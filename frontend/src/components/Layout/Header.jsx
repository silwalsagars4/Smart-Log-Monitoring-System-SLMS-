import { useLocation } from 'react-router-dom'
import { LogOut, RefreshCw, Activity, ShieldAlert } from 'lucide-react'
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
      <div className="flex items-center gap-4">
        {/* Mobile Sidebar Toggle could go here if needed, but we have a sidebar always visible or collapsed */}
        <div>
          <h1 className="text-lg font-semibold text-white">{title}</h1>
          <p className="text-xs text-slate-500">Smart Log Monitoring System</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Live indicator */}
        <div className="hidden md:flex items-center gap-2 bg-surface-700/50 rounded-full px-3 py-1.5 border border-surface-500/30">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
          <span className="text-[11px] font-medium text-slate-400">{connected ? 'Live stream' : 'Disconnected'}</span>
        </div>

        <div className="w-px h-6 bg-surface-600 mx-1 hidden sm:block" />

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-2 rounded-lg text-slate-400 hover:bg-surface-700 hover:text-brand-400 transition-colors"
            aria-label="Refresh"
            title="Refresh data"
          >
            <RefreshCw size={16} />
          </button>
        )}

        <button
          onClick={signOut}
          className="p-2 rounded-lg text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
          aria-label="Logout"
          title="Sign out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
