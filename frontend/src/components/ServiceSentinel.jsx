import { RefreshCw } from 'lucide-react'

export default function ServiceSentinel({ services = [], title = "Service Sentinel", compact = false }) {
  if (!services || services.length === 0) return null;

  return (
    <div className={`${compact ? '' : 'card'}`}>
      {!compact && (
        <div className="card-header">
          <div className="flex items-center gap-2">
            <RefreshCw size={16} className="text-brand-400" />
            <h3 className="text-sm font-semibold text-white">{title}</h3>
          </div>
        </div>
      )}
      {compact && (
         <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-2">{title}</p>
      )}
      
      <div className="space-y-1">
        {services.map(([name, status]) => (
          <div key={name} className={`flex items-center justify-between py-1 px-2 rounded hover:bg-surface-800/40 transition-colors group ${compact ? '' : 'bg-surface-800/20 mb-1 border border-surface-700/30'}`}>
            <div className="flex items-center gap-1.5">
               <div className={`w-1.5 h-1.5 rounded-full ${status === 'Running' ? 'bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]' : 'bg-red-500'}`} />
               <span className={`${compact ? 'text-[10px]' : 'text-xs'} font-mono text-slate-300 group-hover:text-white transition-colors`}>{name}</span>
            </div>
            <span className={`${compact ? 'text-[8px]' : 'text-[10px]'} font-black px-1.5 py-0.5 rounded ${status === 'Running' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
              {status === 'Running' ? 'RUNNING' : 'OFFLINE'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
