import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import SeverityBadge from './SeverityBadge'

const SOURCE_COLORS = {
  ssh: 'text-cyan-400',
  nginx: 'text-green-400',
  apache: 'text-orange-400',
  docker: 'text-blue-400',
  mysql: 'text-yellow-400',
}

function Row({ log, expanded, onToggle }) {
  return (
    <>
      <tr
        className="table-row-hover cursor-pointer border-b border-surface-700"
        onClick={onToggle}
      >
        <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
          {typeof log.timestamp === 'string' ? log.timestamp.substring(0, 19).replace('T', ' ') : '—'}
        </td>
        <td className="px-4 py-3">
          <span className={`text-xs font-semibold uppercase ${SOURCE_COLORS[log.source] || 'text-slate-400'}`}>
            {String(log.source || '')}
          </span>
        </td>
        <td className="px-4 py-3">
          <SeverityBadge severity={log.severity} />
        </td>
        <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
          {String(log.ip || '—')}
        </td>
        <td className="px-4 py-3 text-sm text-slate-300 break-words min-w-[20rem]">
          {typeof log.message === 'string' ? log.message : (log.raw ? String(log.raw) : '—')}
        </td>
        <td className="px-4 py-3 text-xs text-slate-600 whitespace-nowrap">
          {typeof log.anomaly_score === 'number' ? log.anomaly_score.toFixed(3) : '—'}
        </td>
        <td className="px-4 py-3 text-right">
          {expanded ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-surface-700/30 border-b border-surface-700">
          <td colSpan={7} className="px-6 py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              {[
                ['ID', log._id],
                ['Event Type', log.event_type],
                ['User', log.user],
                ['Method', log.method],
                ['Path', log.path],
                ['Status', log.status],
                ['Bytes', log.bytes],
                ['Container', log.container],
                ['Anomaly', log.is_anomaly ? '⚠️ Yes' : 'No'],
                ['Reason', log.severity_reason],
              ].filter(([, v]) => v != null && v !== '').map(([label, value]) => (
                <div key={label}>
                  <p className="text-slate-500 mb-0.5">{label}</p>
                  <p className="text-slate-300 font-mono break-all">{String(value)}</p>
                </div>
              ))}
            </div>
            {log.raw && (
              <div className="mt-3">
                <p className="text-slate-500 text-xs mb-1">Raw</p>
                <pre className="text-xs text-slate-400 bg-surface-800 rounded px-3 py-2 overflow-x-auto font-mono whitespace-pre-wrap break-all">
                  {log.raw}
                </pre>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export default function LogTable({ logs = [], loading = false }) {
  const [expanded, setExpanded] = useState(null)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-600">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-surface-700/50 text-left">
            {['Timestamp', 'Source', 'Severity', 'IP', 'Message', 'Score', ''].map((h) => (
              <th key={h} className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {!logs.length ? (
            <tr>
              <td colSpan={7} className="text-center py-16 text-slate-600">
                No logs found
              </td>
            </tr>
          ) : (
            logs.map((log) => (
              <Row
                key={log._id}
                log={log}
                expanded={expanded === log._id}
                onToggle={() => setExpanded(expanded === log._id ? null : log._id)}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
