const SEVERITY_CONFIG = {
  information: { bg: 'bg-sky-500/15', text: 'text-sky-400', border: 'border-sky-500/30', dot: 'bg-sky-400' },
  warning:     { bg: 'bg-yellow-500/15', text: 'text-yellow-400', border: 'border-yellow-500/30', dot: 'bg-yellow-400' },
  medium:      { bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30', dot: 'bg-orange-400' },
  high:        { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },
  disaster:    { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30', dot: 'bg-purple-500', pulse: true },
}

export default function SeverityBadge({ severity, showDot = true, className = '' }) {
  const cfg = SEVERITY_CONFIG[severity?.toLowerCase()] || SEVERITY_CONFIG.information
  return (
    <span className={`badge ${cfg.bg} ${cfg.text} border ${cfg.border} ${className}`}>
      {showDot && (
        <span className={`severity-dot ${cfg.dot} ${cfg.pulse ? 'animate-pulse' : ''}`} />
      )}
      {severity || 'unknown'}
    </span>
  )
}

export { SEVERITY_CONFIG }
