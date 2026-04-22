import { Activity, AlertTriangle, Database, Cpu } from 'lucide-react'

function HealthItem({ label, value, status = 'ok' }) {
  const colors = { ok: 'text-emerald-400', warn: 'text-yellow-400', error: 'text-red-400' }
  return (
    <div className="flex items-center justify-between py-2 border-b border-surface-600 last:border-0">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-xs font-mono font-medium ${colors[status]}`}>{value}</span>
    </div>
  )
}

export default function SystemHealthCard({ summary }) {
  if (!summary) return null

  const lpm = summary.logs_per_minute ?? 0
  const anomalyRate = summary.total_logs
    ? ((summary.total_anomalies / summary.total_logs) * 100).toFixed(1)
    : '0.0'

  const lpmStatus = lpm > 500 ? 'warn' : 'ok'
  const anomalyStatus = parseFloat(anomalyRate) > 10 ? 'error' : parseFloat(anomalyRate) > 5 ? 'warn' : 'ok'

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Cpu size={16} className="text-brand-400" />
          <h3 className="text-sm font-semibold text-white">System Health</h3>
        </div>
        <span className="badge bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">Operational</span>
      </div>
      <div>
        <HealthItem label="Total Logs" value={summary.total_logs?.toLocaleString()} />
        <HealthItem label="Logs / min" value={lpm.toFixed(1)} status={lpmStatus} />
        <HealthItem label="Anomalies" value={summary.total_anomalies?.toLocaleString()} />
        <HealthItem label="Anomaly Rate" value={`${anomalyRate}%`} status={anomalyStatus} />
        <HealthItem label="Active Alerts" value={summary.total_alerts?.toLocaleString()} status={summary.total_alerts > 0 ? 'warn' : 'ok'} />
      </div>
    </div>
  )
}
