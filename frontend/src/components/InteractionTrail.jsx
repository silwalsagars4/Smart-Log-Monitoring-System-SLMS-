import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { MessageSquare, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { getInteractions } from '../api/stats' // We will add getInteractions to stats.js

export default function InteractionTrail({ alertId }) {
  const [expanded, setExpanded] = useState(false)
  const [interactions, setInteractions] = useState([])
  const [loading, setLoading] = useState(false)

  const handleToggle = async () => {
    if (!expanded && interactions.length === 0) {
      setLoading(true)
      try {
        const { data } = await getInteractions(alertId)
        setInteractions(data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    setExpanded(!expanded)
  }

  return (
    <div className="mt-2 text-xs">
      <button 
        onClick={handleToggle}
        className="flex items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors"
      >
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        View Audit Trail
      </button>

      {expanded && (
        <div className="mt-2 pl-4 border-l-2 border-slate-700/50 space-y-3">
          {loading ? (
            <div className="text-slate-600 animate-pulse">Loading trail...</div>
          ) : interactions.length === 0 ? (
            <div className="text-slate-600">No interactions recorded.</div>
          ) : (
            interactions.map(int => (
              <div key={int.id} className="flex gap-2 text-slate-400">
                <div className="mt-0.5 text-slate-500">
                  {int.action === 'comment' ? <MessageSquare size={12} /> : <CheckCircle size={12} />}
                </div>
                <div>
                  <span className="text-slate-300 font-medium">{int.username}</span>
                  <span className="text-[10px] uppercase tracking-wide ml-1 px-1 rounded bg-slate-800 text-slate-500">
                    {int.user_role}
                  </span>
                  <span className="text-slate-500 ml-2">
                    {formatDistanceToNow(new Date(int.timestamp), { addSuffix: true })}
                  </span>
                  {int.action === 'comment' ? (
                    <div className="mt-1 text-slate-300 italic">"{int.message}"</div>
                  ) : (
                    <div className="mt-1 text-emerald-400/80">Acknowledged alert</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
