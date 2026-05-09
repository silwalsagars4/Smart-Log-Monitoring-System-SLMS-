/**
 * SystemHealthTray — Vertical Sidebar Version
 * ─────────────────────────────────────────────────────────────
 * Designed as a fixed-width, high-density telemetry console for the dashboard.
 * Width: ~3 inches (w-80 / 320px).
 * Sticky behavior.
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { getSystemStats } from '../api/system'
import {
  Cpu, HardDrive, MemoryStick, Server, RefreshCw,
  CircleDot, Wifi, WifiOff, Clock, Activity, ArrowUpRight, ArrowDownLeft,
  Zap, Database, ShieldAlert, Layers
} from 'lucide-react'

// ── ProgressBar ───────────────────────────────────────────────────────────────
function ProgressBar({ percent = 0, label, icon: Icon, colorClass = 'text-brand-400', subLabel = '' }) {
  const clamped = Math.min(Math.max(percent, 0), 100)
  const barColor = clamped >= 90 ? 'bg-red-500'
                 : clamped >= 70 ? 'bg-yellow-500'
                 : 'bg-brand-500'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={12} className={colorClass} />
          <span className="text-[10px] font-semibold text-slate-300">{label}</span>
        </div>
        <span className={`text-[10px] font-mono font-bold ${colorClass}`}>{Math.round(clamped)}%</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-surface-800 border border-surface-700/50 overflow-hidden shadow-inner">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-1000 ease-in-out`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {subLabel && <p className="text-[9px] text-slate-500 text-right font-medium">{subLabel}</p>}
    </div>
  )
}

// ── Stat Group ────────────────────────────────────────────────────────────────
function StatGroup({ label, children }) {
  return (
    <div className="py-2 border-b border-surface-700/50 last:border-0">
      <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-2">{label}</p>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  )
}

export default function SystemHealthTray() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)
  const [spinning, setSpinning] = useState(false)
  const intervalRef = useRef(null)

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await getSystemStats()
      setStats(data)
      setError(null)
    } catch (err) {
      if (err?.response?.status === 503) setError('Initializing Telemetry...')
      else setError('System Offline')
    }
  }, [])

  useEffect(() => {
    fetchStats()
    intervalRef.current = setInterval(fetchStats, 5000)
    return () => clearInterval(intervalRef.current)
  }, [fetchStats])

  const formatUptime = (seconds) => {
    if (!seconds) return '—'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return `${h}h ${m}m`
  }

  if (!stats && !error) {
    return (
      <div className="w-80 h-full bg-surface-900/50 border-l border-surface-700/30 flex flex-col items-center justify-center gap-4">
        <RefreshCw size={24} className="text-brand-500 animate-spin" />
        <span className="text-xs text-slate-500 font-mono">Syncing Core...</span>
      </div>
    )
  }

  if (error && !stats) {
    return (
      <div className="w-80 h-full bg-surface-900/80 border-l border-red-500/20 p-6 flex flex-col items-center justify-center text-center gap-4">
        <div className="p-4 rounded-full bg-red-500/10 border border-red-500/20">
          <WifiOff size={32} className="text-red-400" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white mb-1">Telemetry Interrupted</h3>
          <p className="text-xs text-slate-500">{error}</p>
        </div>
        <button 
          onClick={fetchStats}
          className="btn-primary w-full py-2 text-xs"
        >
          Re-establish Link
        </button>
      </div>
    )
  }

  const services = Object.entries(stats.services || {})

  return (
    <div className="w-80 h-full bg-surface-900/60 border-l border-surface-700/50 flex flex-col backdrop-blur-xl shadow-2xl">
      
      {/* ── Header ── */}
      <div className="p-4 bg-gradient-to-br from-brand-600/10 to-transparent border-b border-surface-700/50">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Server size={16} className="text-brand-400" />
            <h3 className="text-xs font-black text-white uppercase tracking-tighter">System Console</h3>
          </div>
          <button 
            onClick={() => { setSpinning(true); fetchStats(); setTimeout(() => setSpinning(false), 600); }}
            className="p-1 rounded-lg bg-surface-800/50 text-slate-500 hover:text-brand-400 transition-colors"
          >
            <RefreshCw size={12} className={spinning ? 'animate-spin' : ''} />
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2">
           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
           <span className="text-[9px] font-bold text-slate-300 truncate max-w-[200px]">{stats.hostname}</span>
        </div>
        <p className="text-[9px] text-slate-500 mt-0.5 font-mono">{stats.os_name}</p>
      </div>

      {/* ── Body ── */}
      <div className="flex-1 p-4 space-y-1">
        
        {/* Core Utilization */}
        <StatGroup label="Utilization">
          <ProgressBar 
            icon={Cpu} 
            label="CPU Usage" 
            percent={stats.cpu_percent} 
            colorClass="text-brand-400"
            subLabel={`Load: ${stats.load_avg?.[0]?.toFixed(2)} / ${stats.load_avg?.[1]?.toFixed(2)}`}
          />
          <ProgressBar 
            icon={MemoryStick} 
            label="RAM Usage" 
            percent={stats.mem_percent} 
            colorClass="text-purple-400"
            subLabel={`${stats.mem_used_gb} / ${stats.mem_total_gb} GB`}
          />
          <ProgressBar 
            icon={Layers} 
            label="Swap Memory" 
            percent={stats.swap_percent} 
            colorClass="text-pink-400"
            subLabel={`${stats.swap_used_gb} / ${stats.swap_total_gb} GB`}
          />
          <ProgressBar 
            icon={HardDrive} 
            label="Storage (Root)" 
            percent={stats.disk_percent} 
            colorClass="text-emerald-400"
            subLabel={`${stats.disk_used_gb} / ${stats.disk_total_gb} GB`}
          />
        </StatGroup>

        {/* Network & Processes */}
        <StatGroup label="Network & Ops">
          <div className="grid grid-cols-2 gap-2">
             <div className="p-2 rounded-lg bg-surface-800/50 border border-surface-700/50">
                <p className="text-[8px] font-bold text-slate-500 uppercase tracking-tighter">Uptime</p>
                <div className="flex items-center gap-1">
                   <Clock size={10} className="text-brand-400" />
                   <span className="text-[10px] font-bold text-slate-200">{formatUptime(stats.uptime)}</span>
                </div>
             </div>
             <div className="p-2 rounded-lg bg-surface-800/50 border border-surface-700/50">
                <p className="text-[8px] font-bold text-slate-500 uppercase tracking-tighter">Procs</p>
                <div className="flex items-center gap-1">
                   <Activity size={10} className="text-purple-400" />
                   <span className="text-[10px] font-bold text-slate-200">{stats.process_count}</span>
                </div>
             </div>
          </div>
          
          <div className="space-y-1.5 p-2 rounded-lg bg-surface-800/30 border border-surface-700/30">
            <div className="flex items-center justify-between">
              <span className="text-[9px] text-slate-400">Inbound</span>
              <div className="flex items-center gap-1 text-emerald-400 font-mono text-[10px] font-bold">
                <ArrowDownLeft size={8} /> {stats.net_recv_mb} MB
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[9px] text-slate-400">Outbound</span>
              <div className="flex items-center gap-1 text-blue-400 font-mono text-[10px] font-bold">
                <ArrowUpRight size={8} /> {stats.net_sent_mb} MB
              </div>
            </div>
          </div>
        </StatGroup>

        {/* Service Sentinel */}
        <StatGroup label="Service Sentinel">
          <div className="space-y-0.5">
            {services.map(([name, status]) => (
              <div key={name} className="flex items-center justify-between py-1 px-2 rounded hover:bg-surface-800/40 transition-colors group">
                <div className="flex items-center gap-1.5">
                   <div className={`w-1 h-1 rounded-full ${status === 'Running' ? 'bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]' : 'bg-red-500'}`} />
                   <span className="text-[10px] font-mono text-slate-300 group-hover:text-white transition-colors">{name}</span>
                </div>
                <span className={`text-[8px] font-black px-1 py-0.5 rounded ${status === 'Running' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                  {status === 'Running' ? 'RUN' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        </StatGroup>

      </div>


    </div>
  )
}
