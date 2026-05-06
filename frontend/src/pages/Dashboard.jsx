import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout/Layout'
import { getSummary, getTrend, getTopIPs, getSeverityTrend, getAlerts } from '../api/stats'
import LogsPerSecondChart from '../components/Charts/LogsPerSecondChart'
import SeverityDistributionChart from '../components/Charts/SeverityDistributionChart'
import TopIPsChart from '../components/Charts/TopIPsChart'
import ErrorTrendChart from '../components/Charts/ErrorTrendChart'
import LiveLogStream from '../components/LiveLogStream'
import SystemHealthCard from '../components/SystemHealthCard'
import AlertPanel from '../components/AlertPanel'
import { Activity, AlertTriangle, BarChart2, Shield, TrendingUp, Zap, Cpu } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Safely extracts an array from an API response regardless of shape */
function toArray(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  if (data && Array.isArray(data.results)) return data.results
  return []
}

/** Safely extracts a plain object from an API response */
function toObject(data) {
  if (data && typeof data === 'object' && !Array.isArray(data)) return data
  return null
}

/** Safely formats a number to fixed decimal places */
function safeFixed(val, decimals = 1) {
  return typeof val === 'number' ? val.toFixed(decimals) : '—'
}

/** Safely counts keys of an object */
function safeKeyCount(obj) {
  if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
    return Object.keys(obj).length || '—'
  }
  return '—'
}

// ─── StatCard ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, color = 'brand' }) {
  const colors = {
    brand: 'from-brand-500/20 to-brand-600/5 border-brand-500/30 text-brand-400',
    red: 'from-red-500/20 to-red-600/5 border-red-500/30 text-red-400',
    yellow: 'from-yellow-500/20 to-yellow-600/5 border-yellow-500/30 text-yellow-400',
    emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30 text-emerald-400',
    purple: 'from-purple-500/20 to-purple-600/5 border-purple-500/30 text-purple-400',
  }
  return (
    <div className={`stat-card backdrop-blur-md bg-gradient-to-br ${colors[color]} border shadow-xl relative overflow-hidden group`}>
      <div className={`absolute top-0 right-0 w-24 h-24 rounded-full mix-blend-screen filter blur-2xl opacity-20 bg-${color}-500 group-hover:opacity-40 transition-opacity duration-500`}></div>
      <div className="flex items-center justify-between relative z-10">
        <span className="text-xs text-slate-400 uppercase tracking-wide font-semibold">{label}</span>
        <Icon size={16} className={colors[color].split(' ').pop()} />
      </div>
      <p className="text-3xl font-bold text-white tabular-nums mt-1 relative z-10">
        {value ?? <span className="text-slate-600">—</span>}
      </p>
      {sub && <p className="text-xs text-slate-500 relative z-10">{sub}</p>}
    </div>
  )
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [topIPs, setTopIPs] = useState([])
  const [severityTrend, setSeverityTrend] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAll = useCallback(async () => {
    try {
      const [sumRes, trendRes, ipsRes, sevRes, alertsRes] = await Promise.all([
        getSummary(),
        getTrend(6),
        getTopIPs(8),
        getSeverityTrend(24),
        getAlerts({ acknowledged: false, page_size: 5 }),
      ])

      // FIX: validate each response before setting state
      // prevents raw MongoDB log objects {t, s, c, id, ctx, msg, attr}
      // from leaking into React render and causing error #31
      setSummary(toObject(sumRes.data))
      setTrend(toArray(trendRes.data))
      setTopIPs(toArray(ipsRes.data))
      setSeverityTrend(toArray(sevRes.data))
      setAlerts(toArray(alertsRes.data))

    } catch (err) {
      console.error('Dashboard fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <Layout onRefresh={fetchAll}>
      <div className="space-y-6 max-w-screen-2xl">

        {/* Phase 1.1 Upgrade Banner */}
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-brand-600/20 via-purple-600/20 to-brand-600/20 border border-brand-500/20 p-6 backdrop-blur-sm shadow-xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
          <div className="absolute bottom-0 left-1/4 w-64 h-64 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>

          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-brand-500/20 text-brand-300 border border-brand-500/30 uppercase">SLMS Update</span>
                <h1 className="text-xl font-bold text-white tracking-tight">Phase 1.1 Deployed</h1>
              </div>
              <p className="text-sm text-slate-300 max-w-2xl">
                The ML Ensemble is now analyzing your logs with Isolation Forest, LOF, and OC-SVM.
                {isAdmin
                  ? ' As an admin, you can manage user access and dynamic log sources in Settings.'
                  : ' Explore the real-time anomaly scores and stream insights.'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/80 border border-surface-600/50 shadow-inner">
                <Cpu size={16} className="text-brand-400" />
                <span className="text-xs font-medium text-slate-200">Ensemble Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-4">
          <StatCard
            icon={BarChart2}
            label="Total Logs"
            value={summary?.total_logs?.toLocaleString()}
            sub="all time"
            color="brand"
          />
          <StatCard
            icon={AlertTriangle}
            label="Anomalies"
            value={summary?.total_anomalies?.toLocaleString()}
            sub="detected by ML"
            color="red"
          />
          <StatCard
            icon={Zap}
            label="Active Alerts"
            value={summary?.total_alerts?.toLocaleString()}
            sub="high + disaster"
            color="yellow"
          />
          <StatCard
            icon={TrendingUp}
            label="Logs / min"
            // FIX: guard against non-number value before calling .toFixed()
            value={safeFixed(summary?.logs_per_minute)}
            sub="5-min average"
            color="emerald"
          />
          <StatCard
            icon={Shield}
            label="Sources"
            // FIX: guard against non-object before calling Object.keys()
            value={safeKeyCount(summary?.source_counts)}
            sub="monitored"
            color="purple"
          />
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <LogsPerSecondChart data={trend} />
          </div>
          <SeverityDistributionChart data={summary?.severity_counts || {}} />
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ErrorTrendChart data={severityTrend} />
          <TopIPsChart data={topIPs} />
        </div>

        {/* Live Stream + Health + Alerts */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <LiveLogStream />
          </div>
          <div className="space-y-4">
            <SystemHealthCard summary={summary} />
          </div>
        </div>

        {/* Recent Alerts — only shown when alerts exist */}
        {alerts.length > 0 && (
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-red-400" />
                <h3 className="text-sm font-semibold text-white">Recent Alerts</h3>
              </div>
              <a href="/alerts" className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                View all →
              </a>
            </div>
            <AlertPanel alerts={alerts} onRefresh={fetchAll} userRole={user?.role || 'user'} />
          </div>
        )}

      </div>
    </Layout>
  )
}