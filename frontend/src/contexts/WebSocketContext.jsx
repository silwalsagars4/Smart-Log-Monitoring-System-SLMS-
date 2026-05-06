import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'

const WebSocketContext = createContext(null)

// ─── Normalizer ──────────────────────────────────────────────────────────────
// Called ONCE here at the source so every consumer gets a safe flat object.
// Handles two shapes:
//   1. Already-processed: { message, source, ip, severity, timestamp }
//   2. Raw MongoDB:       { t, s, c, id, ctx, msg, attr }
function normalizeLog(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null

  // Already normalized — validate each field is a primitive before passing on
  if (typeof raw.message === 'string' || typeof raw.source === 'string') {
    return {
      timestamp: typeof raw.timestamp === 'string' ? raw.timestamp : '',
      severity: typeof raw.severity === 'string' ? raw.severity : 'info',
      source: typeof raw.source === 'string' ? raw.source : '',
      message: typeof raw.message === 'string' ? raw.message : '',
      ip: typeof raw.ip === 'string' ? raw.ip : '',
      raw: typeof raw.raw === 'string' ? raw.raw : '',
    }
  }

  // Raw MongoDB log shape: { t, s, c, id, ctx, msg, attr }
  const severityMap = { E: 'error', W: 'warning', I: 'info', D: 'debug', F: 'fatal' }
  return {
    timestamp: raw.t?.['$date'] ?? (typeof raw.t === 'string' ? raw.t : ''),
    severity: severityMap[raw.s] ?? 'info',
    source: [raw.c, raw.ctx].filter(Boolean).join('/') || '',
    message: typeof raw.msg === 'string' ? raw.msg : '',
    ip: raw.attr?.remote ?? raw.attr?.client ?? '',
    raw: '',
  }
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function WebSocketProvider({ children }) {
  const [liveLog, setLiveLog] = useState(null)   // always null or a normalized log
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const listenersRef = useRef(new Set())
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    const token = localStorage.getItem('slms_token')
    if (!token) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${protocol}://${host}/ws/logs?token=${token}`

    if (wsRef.current) {
      wsRef.current.close()
    }

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'log') {
          // FIX: normalize ONCE here at the source before touching any state
          // or notifying any subscriber — kills error #31 for ALL consumers
          const normalized = normalizeLog(msg.data)
          if (!normalized) return

          setLiveLog(normalized)
          listenersRef.current.forEach((fn) => fn(normalized))
        }
      } catch {
        // ignore unparseable frames (e.g. pong responses)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 25000)

    return () => {
      clearInterval(ping)
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const subscribe = useCallback((fn) => {
    listenersRef.current.add(fn)
    return () => listenersRef.current.delete(fn)
  }, [])

  return (
    <WebSocketContext.Provider value={{ liveLog, connected, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  return useContext(WebSocketContext)
}