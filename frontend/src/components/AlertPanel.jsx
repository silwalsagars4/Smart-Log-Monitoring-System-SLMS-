import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { CheckCircle, Trash2, AlertTriangle, Zap, ShieldX, MessageSquare } from 'lucide-react'
import SeverityBadge from './SeverityBadge'
import { acknowledgeAlert, deleteAlert, postComment } from '../api/stats'
import InteractionTrail from './InteractionTrail'

const SEVERITY_ICONS = {
  high: <AlertTriangle size={16} className="text-red-400" />,
  disaster: <Zap size={16} className="text-purple-400 animate-pulse" />,
}

export default function AlertPanel({ alerts = [], onRefresh, userRole = "user" }) {
  const [loading, setLoading] = useState({})
  const [commentingId, setCommentingId] = useState(null)
  const [commentText, setCommentText] = useState('')

  const isAdmin = userRole === 'admin'
  const isAnalyst = userRole === 'analyst' || isAdmin

  const handleAck = async (id) => {
    setLoading((l) => ({ ...l, [id]: 'ack' }))
    try {
      await acknowledgeAlert(id)
      onRefresh?.()
    } finally {
      setLoading((l) => ({ ...l, [id]: undefined }))
    }
  }

  const handleDelete = async (id) => {
    setLoading((l) => ({ ...l, [id]: 'del' }))
    try {
      await deleteAlert(id)
      onRefresh?.()
    } finally {
      setLoading((l) => ({ ...l, [id]: undefined }))
    }
  }

  const handleCommentSubmit = async (id) => {
    if (!commentText.trim()) return
    setLoading((l) => ({ ...l, [id]: 'comment' }))
    try {
      await postComment(id, commentText)
      setCommentingId(null)
      setCommentText('')
      // Optionally refresh to let InteractionTrail fetch if already expanded 
      // but simpler is to just refresh the alerts list or rely on user expanding it.
    } finally {
      setLoading((l) => ({ ...l, [id]: undefined }))
    }
  }

  if (!alerts.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-600">
        <ShieldX size={32} className="mb-2" />
        <p className="text-sm">No active alerts</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div key={alert.id} className="space-y-1">
          <div
            className={`flex items-start gap-3 px-4 py-3 rounded-lg border transition-all duration-200 ${
              alert.acknowledged
                ? 'bg-surface-700/30 border-surface-600 opacity-60'
                : alert.severity === 'disaster'
                ? 'bg-purple-500/10 border-purple-500/30'
                : 'bg-red-500/10 border-red-500/30'
            }`}
          >
            <div className="flex-shrink-0 mt-0.5">
              {SEVERITY_ICONS[alert.severity] || <AlertTriangle size={16} className="text-orange-400" />}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={alert.severity} />
                <span className="text-xs text-slate-500 uppercase tracking-wide">{alert.source}</span>
                {alert.ip && <span className="text-xs text-slate-600 font-mono">{alert.ip}</span>}
                {alert.acknowledged && (
                  <span className="badge bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px]">
                    Acknowledged
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-300 truncate">{alert.message}</p>
              <p className="text-xs text-slate-600 mt-1">
                {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })} ·{' '}
                Score: <span className="text-slate-500">{alert.anomaly_score?.toFixed(3)}</span>
              </p>
            </div>

            <div className="flex items-center gap-1 flex-shrink-0">
              {isAnalyst && !alert.acknowledged && (
                <button
                  onClick={() => handleAck(alert.id)}
                  disabled={loading[alert.id] === 'ack'}
                  className="btn-ghost p-1.5 rounded text-slate-500 hover:text-emerald-400"
                  title="Acknowledge"
                >
                  <CheckCircle size={15} />
                </button>
              )}
              {isAnalyst && ['high', 'disaster'].includes(alert.severity) && (
                <button
                  onClick={() => setCommentingId(alert.id === commentingId ? null : alert.id)}
                  className="btn-ghost p-1.5 rounded text-slate-500 hover:text-blue-400"
                  title="Comment"
                >
                  <MessageSquare size={15} />
                </button>
              )}
              {isAdmin && (
                <button
                  onClick={() => handleDelete(alert.id)}
                  disabled={loading[alert.id] === 'del'}
                  className="btn-ghost p-1.5 rounded text-slate-500 hover:text-red-400"
                  title="Delete"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          </div>
          {commentingId === alert.id && (
            <div className="mt-2 ml-10 flex gap-2">
              <input
                type="text"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Add an investigation comment..."
                className="flex-1 input-field bg-slate-800 text-sm py-1.5"
              />
              <button
                onClick={() => handleCommentSubmit(alert.id)}
                disabled={loading[alert.id] === 'comment' || !commentText.trim()}
                className="btn-primary py-1.5 px-3 text-sm"
              >
                Post
              </button>
            </div>
          )}
          <div className="ml-10">
            <InteractionTrail alertId={alert.id} />
          </div>
        </div>
      ))}
    </div>
  )
}
