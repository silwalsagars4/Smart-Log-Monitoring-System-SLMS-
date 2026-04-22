import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, ScrollText, Bell, Settings, Activity,
  ShieldAlert, ChevronLeft, ChevronRight, Zap
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useWebSocket } from '../../contexts/WebSocketContext'
import { useState } from 'react'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/logs', icon: ScrollText, label: 'Logs' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { user, isAdmin } = useAuth()
  const { connected } = useWebSocket()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`
      flex flex-col bg-surface-800 border-r border-surface-600
      transition-all duration-300 ease-in-out
      ${collapsed ? 'w-16' : 'w-60'}
    `}>
      {/* Logo */}
      <div className={`flex items-center gap-3 px-4 py-5 border-b border-surface-600 ${collapsed ? 'justify-center' : ''}`}>
        <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-brand-500 to-purple-500 rounded-lg flex items-center justify-center glow-brand">
          <ShieldAlert size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-sm font-bold text-white tracking-wide">SLMS</p>
            <p className="text-xs text-slate-500">Log Monitor</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              isActive ? 'nav-item-active' : 'nav-item-inactive'
            }
            title={collapsed ? label : undefined}
          >
            <Icon size={18} className="flex-shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Status + User */}
      <div className="px-3 py-4 border-t border-surface-600 space-y-3">
        {/* WS status */}
        <div className={`flex items-center gap-2 px-2 ${collapsed ? 'justify-center' : ''}`}>
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${connected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-slate-600'}`} />
          {!collapsed && (
            <span className={`text-xs ${connected ? 'text-emerald-400' : 'text-slate-500'}`}>
              {connected ? 'Live' : 'Offline'}
            </span>
          )}
          {!collapsed && connected && (
            <Activity size={12} className="text-emerald-400 animate-pulse ml-auto" />
          )}
        </div>

        {/* User info */}
        {!collapsed && (
          <div className="flex items-center gap-2 px-2">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.username}</p>
              <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
            </div>
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-end px-2'} text-slate-500 hover:text-white transition-colors`}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}
