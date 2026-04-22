import { useLocation } from 'react-router-dom'
import { LogOut, RefreshCw, Bell } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useWebSocket } from '../../contexts/WebSocketContext'

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/logs': 'Log Explorer',
  '/alerts': 'Alert Center',
  '/settings': 'Settings',
}

export default function Header({ onRefresh }) {
  const { signOut, user } = useAuth()
  const { connected } = useWebSocket()
  const location = useLocation()
  const title = PAGE_TITLES[location.pathname] || 'SLMS'

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-surface-800/60 backdrop-blur-sm border-b border-surface-600 sticky top-0 z-20">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        <p className="text-xs text-slate-500">Smart Log Monitoring System</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Live indicator */}
        <div className="hidden sm:flex items-center gap-2 bg-surface-700 rounded-full px-3 py-1.5 border border-surface-500">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
          <span className="text-xs text-slate-400">{connected ? 'Live stream' : 'Disconnected'}</span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="btn-ghost p-2 rounded-lg"
            aria-label="Refresh"
            title="Refresh data"
          >
            <RefreshCw size={16} />
          </button>
        )}

        <button
          onClick={signOut}
          className="btn-ghost p-2 rounded-lg text-slate-400 hover:text-red-400"
          aria-label="Logout"
          title="Sign out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
