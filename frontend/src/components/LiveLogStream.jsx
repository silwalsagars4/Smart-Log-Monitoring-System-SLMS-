import { useState, useEffect, useCallback, useRef } from 'react'
import { useWebSocket } from '../contexts/WebSocketContext'
import SeverityBadge from './SeverityBadge'
import { Terminal, Trash2, PauseCircle, PlayCircle } from 'lucide-react'

const MAX_LOG_LINES = 200

export default function LiveLogStream() {
  const { subscribe } = useWebSocket()
  const [logs, setLogs] = useState([])
  const [paused, setPaused] = useState(false)
  const [filter, setFilter] = useState('')
  const bottomRef = useRef(null)
  const pausedRef = useRef(false)

  useEffect(() => { pausedRef.current = paused }, [paused])

  useEffect(() => {
    const unsub = subscribe((log) => {
      if (pausedRef.current) return
      setLogs((prev) => {
        const next = [log, ...prev]
        return next.slice(0, MAX_LOG_LINES)
      })
    })
    return unsub
  }, [subscribe])

  const filtered = filter
    ? logs.filter((l) =>
        l.message?.toLowerCase().includes(filter.toLowerCase()) ||
        l.source?.toLowerCase().includes(filter.toLowerCase()) ||
        l.ip?.toLowerCase().includes(filter.toLowerCase())
      )
    : logs

  return (
    <div className="card flex flex-col h-80">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-brand-400" />
          <span className="text-sm font-semibold text-white">Live Stream</span>
          <span className="badge bg-brand-500/20 text-brand-400 border border-brand-500/30 text-xs">
            {logs.length} events
          </span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Filter…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input w-36 text-xs py-1"
          />
          <button
            onClick={() => setPaused((p) => !p)}
            className="btn-ghost p-1.5 rounded-lg"
            title={paused ? 'Resume' : 'Pause'}
          >
            {paused
              ? <PlayCircle size={16} className="text-emerald-400" />
              : <PauseCircle size={16} className="text-slate-400" />
            }
          </button>
          <button
            onClick={() => setLogs([])}
            className="btn-ghost p-1.5 rounded-lg"
            title="Clear"
          >
            <Trash2 size={14} className="text-slate-400" />
          </button>
        </div>
      </div>

      {/* Stream */}
      <div className="flex-1 overflow-y-auto font-mono text-xs space-y-1 pr-1">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-600">
            {paused ? 'Stream paused…' : 'Waiting for events…'}
          </div>
        ) : (
          filtered.map((log, i) => (
            <div
              key={i}
              className="flex items-start gap-2 px-2 py-1 rounded hover:bg-surface-700/40 transition-colors animate-slide-in"
            >
              <span className="text-slate-600 select-none flex-shrink-0 w-20 truncate">
                {log.timestamp?.substring(11, 19) || '--:--:--'}
              </span>
              <SeverityBadge severity={log.severity} showDot={false} className="flex-shrink-0 py-0 text-[10px]" />
              <span className="text-slate-400 flex-shrink-0 w-16 truncate">[{log.source}]</span>
              <span className="text-slate-300 truncate">{log.message || log.raw || '—'}</span>
              {log.ip && <span className="text-slate-600 flex-shrink-0 ml-auto">{log.ip}</span>}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
