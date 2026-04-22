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
import { Activity, AlertTriangle, BarChart2, Shield, TrendingUp, Zap } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

function StatCard({ icon: Icon, label, value, sub, color = 'brand' }) {
  const colors = {
    brand: 'from-brand-500/20 to-brand-600/10 border-brand-500/20 text-brand-400',
    red: 'from-red-500/20 to-red-600/10 border-red-500/20 text-red-400',
    yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/20 text-yellow-400',
    emerald: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/20 text-emerald-400',
    purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/20 text-purple-400',
  }
  return (
    <div className={`stat-card bg-gradient-to-br ${colors[color]} border`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">{label}</span>
        <Icon size={16} className={colors[color].split(' ').pop()} />
      </div>
      <p className="text-3xl font-bold text-white tabular-nums">
        {value ?? <span className="text-slate-600">—</span>}
      </p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { isAdmin } = useAuth()
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
      setSummary(sumRes.data)
      setTrend(trendRes.data)
      setTopIPs(ipsRes.data)
      setSeverityTrend(sevRes.data)
      setAlerts(alertsRes.data)
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
        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-4">
          <StatCard icon={BarChart2} label="Total Logs" value={summary?.total_logs?.toLocaleString()} sub="all time" color="brand" />
          <StatCard icon={AlertTriangle} label="Anomalies" value={summary?.total_anomalies?.toLocaleString()} sub="detected by ML" color="red" />
          <StatCard icon={Zap} label="Active Alerts" value={summary?.total_alerts?.toLocaleString()} sub="high + disaster" color="yellow" />
          <StatCard icon={TrendingUp} label="Logs / min" value={summary?.logs_per_minute?.toFixed(1)} sub="5-min average" color="emerald" />
          <StatCard icon={Shield} label="Sources" value={Object.keys(summary?.source_counts || {}).length || '—'} sub="monitored" color="purple" />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <LogsPerSecondChart data={trend} />
          </div>
          <SeverityDistributionChart data={summary?.severity_counts || {}} />
        </div>

        {/* Second charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ErrorTrendChart data={severityTrend} />
          <TopIPsChart data={topIPs} />
        </div>

        {/* Live stream + health + alerts */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <LiveLogStream />
          </div>
          <div className="space-y-4">
            <SystemHealthCard summary={summary} />
          </div>
        </div>

        {/* Recent alerts */}
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
            <AlertPanel alerts={alerts} onRefresh={fetchAll} isAdmin={isAdmin} />
          </div>
        )}
      </div>
    </Layout>
  )
}
