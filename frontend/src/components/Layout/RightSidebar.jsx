/**
 * RightSidebar — A vertical "navbar-like" column on the right side.
 * Contains quick actions, filters, and auxiliary system status.
 */

import { 
  Zap, Play, Pause, Filter, ShieldCheck, 
  UserCheck, History, Terminal, Info
} from 'lucide-react'
import { useState } from 'react'

function ActionButton({ icon: Icon, label, onClick, active = false, colorClass = 'text-slate-400' }) {
  return (
    <button
      onClick={onClick}
      className={`
        flex flex-col items-center justify-center gap-1 w-full py-4 px-2 
        border-b border-surface-700/50 transition-all duration-200
        ${active ? 'bg-brand-500/10 text-brand-400' : 'text-slate-500 hover:bg-surface-700/30 hover:text-slate-300'}
      `}
    >
      <Icon size={20} className={active ? 'text-brand-400' : colorClass} />
      <span className="text-[9px] font-bold uppercase tracking-tighter">{label}</span>
    </button>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest text-center py-3 border-b border-surface-700/50">
      {children}
    </p>
  )
}

export default function RightSidebar() {
  const [streamPaused, setStreamPaused] = useState(false)
  const [activeFilter, setActiveFilter] = useState('all')

  return (
    <aside className="hidden lg:flex flex-col w-20 bg-surface-900 border-l border-surface-700/50 overflow-y-auto no-scrollbar">
      
      {/* ── Section: Controls ── */}
      <SectionLabel>Live</SectionLabel>
      <ActionButton 
        icon={streamPaused ? Play : Pause} 
        label={streamPaused ? "Resume" : "Pause"} 
        onClick={() => setStreamPaused(!streamPaused)}
        colorClass={streamPaused ? 'text-emerald-400' : 'text-yellow-400'}
        active={streamPaused}
      />
      <ActionButton 
        icon={Zap} 
        label="Clear" 
        onClick={() => {}} 
        colorClass="text-purple-400"
      />

      {/* ── Section: Filters ── */}
      <SectionLabel>Filters</SectionLabel>
      <ActionButton 
        icon={ShieldCheck} 
        label="Critical" 
        active={activeFilter === 'critical'}
        onClick={() => setActiveFilter('critical')}
        colorClass="text-red-400"
      />
      <ActionButton 
        icon={Filter} 
        label="Anomalies" 
        active={activeFilter === 'anomalies'}
        onClick={() => setActiveFilter('anomalies')}
        colorClass="text-brand-400"
      />

      {/* ── Section: System ── */}
      <SectionLabel>System</SectionLabel>
      <ActionButton 
        icon={UserCheck} 
        label="Sessions" 
        onClick={() => {}} 
      />
      <ActionButton 
        icon={Terminal} 
        label="Console" 
        onClick={() => {}} 
      />
      <ActionButton 
        icon={History} 
        label="Audit" 
        onClick={() => {}} 
      />

      {/* ── Footer / Info ── */}
      <div className="mt-auto border-t border-surface-700/50">
        <ActionButton 
          icon={Info} 
          label="Help" 
          onClick={() => {}} 
        />
      </div>

    </aside>
  )
}
