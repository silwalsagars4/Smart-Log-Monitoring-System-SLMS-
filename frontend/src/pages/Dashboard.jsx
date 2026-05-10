import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout/Layout'
import { getSummary, getTrend, getTopIPs, getSeverityTrend, getAlerts } from '../api/stats'
import { getSystemStats } from '../api/system'
import LogsPerSecondChart from '../components/Charts/LogsPerSecondChart'
import SeverityDistributionChart from '../components/Charts/SeverityDistributionChart'
import TopIPsChart from '../components/Charts/TopIPsChart'
import ErrorTrendChart from '../components/Charts/ErrorTrendChart'
import LiveLogStream from '../components/LiveLogStream'
import SystemHealthTray from '../components/SystemHealthTray'
import AlertPanel from '../components/AlertPanel'
import { Activity, AlertTriangle, BarChart2, Shield, TrendingUp, Zap } from 'lucide-react'
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
  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [topIPs, setTopIPs] = useState([])
  const [severityTrend, setSeverityTrend] = useState([])
  const [alerts, setAlerts] = useState([])
  const [systemStats, setSystemStats] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [sumRes, trendRes, ipsRes, sevRes, alertsRes] = await Promise.all([
        getSummary(),
        getTrend(6),
        getTopIPs(8),
        getSeverityTrend(24),
        getAlerts({ acknowledged: false, page_size: 5 }),
      ])

      setSummary(toObject(sumRes.data))
      setTrend(toArray(trendRes.data))
      setTopIPs(toArray(ipsRes.data))
      setSeverityTrend(toArray(sevRes.data))
      setAlerts(toArray(alertsRes.data))

      const sysRes = await getSystemStats()
      setSystemStats(sysRes.data)

    } catch (err) {
      console.error('Dashboard fetch error:', err)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <Layout onRefresh={fetchAll} rightSidebar={<SystemHealthTray />}>
      <div className="p-6 space-y-6">
        
        {/* Main Dashboard Content */}
        <div className="space-y-6">
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
              value={safeFixed(summary?.logs_per_minute)}
              sub="5-min average"
              color="emerald"
            />
            <StatCard
              icon={Shield}
              label="Sources"
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

          {/* Live Stream */}
          <div className="card">
            <LiveLogStream />
          </div>

          {/* Recent Alerts */}
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
        </div>
      </div>
    </Layout>
  )
}