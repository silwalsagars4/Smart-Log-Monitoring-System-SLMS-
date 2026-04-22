import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'

const WebSocketContext = createContext(null)

export function WebSocketProvider({ children }) {
  const [liveLog, setLiveLog] = useState(null)
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
          setLiveLog(msg.data)
          listenersRef.current.forEach((fn) => fn(msg.data))
        }
      } catch { /* ignore */ }
    }

    ws.onclose = () => {
      setConnected(false)
      // Reconnect after 3s
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
