import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout/Layout'
import AlertPanel from '../components/AlertPanel'
import { getAlerts } from '../api/stats'
import { Bell, Filter } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const SEVERITY_FILTER = ['', 'high', 'disaster']

export default function Alerts() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [severity, setSeverity] = useState('')
  const [showAcknowledged, setShowAcknowledged] = useState(false)
  const [page, setPage] = useState(1)

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 50 }
      if (severity) params.severity = severity
      if (!showAcknowledged) params.acknowledged = false
      const { data } = await getAlerts(params)
      setAlerts(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, severity, showAcknowledged])

  useEffect(() => {
    fetchAlerts()
    const iv = setInterval(fetchAlerts, 15000)
    return () => clearInterval(iv)
  }, [fetchAlerts])

  return (
    <Layout onRefresh={fetchAlerts}>
      <div className="max-w-4xl space-y-4">
        {/* Header + filters */}
        <div className="card py-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-white font-medium">
              <Bell size={16} className="text-red-400" />
              Alert Center
            </div>

            <select
              value={severity}
              onChange={(e) => { setSeverity(e.target.value); setPage(1) }}
              className="input w-36 ml-auto"
            >
              <option value="">All severities</option>
              <option value="high">High</option>
              <option value="disaster">Disaster</option>
            </select>

            <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={showAcknowledged}
                onChange={(e) => setShowAcknowledged(e.target.checked)}
                className="rounded border-surface-500 bg-surface-700 text-brand-600 focus:ring-brand-500"
              />
              Show acknowledged
            </label>
          </div>
        </div>

        {/* Alert count */}
        <div className="flex items-center gap-2">
          <span className="badge bg-red-500/15 text-red-400 border border-red-500/30">
            {alerts.length} alerts
          </span>
          {loading && <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />}
        </div>

        {/* Alerts */}
        <div className="card">
          <AlertPanel alerts={alerts} onRefresh={fetchAlerts} userRole={user?.role || "user"} />
        </div>
      </div>
    </Layout>
  )
}
