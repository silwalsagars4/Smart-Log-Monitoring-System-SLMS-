import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-700 border border-surface-500 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: <span className="font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export default function LogsPerSecondChart({ data = [] }) {
  // data: [{_id: "2024-01-15T10", count: 42, anomalies: 3}]
  const formatted = data.map((d) => ({
    hour: d._id?.substring(11) || d._id || '',
    logs: d.count || 0,
    anomalies: d.anomalies || 0,
  }))

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-sm font-semibold text-white">Log Volume</h3>
        <span className="text-xs text-slate-500">Last 6 hours</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={formatted} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="logGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" />
          <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
          <Area type="monotone" dataKey="logs" name="Logs" stroke="#6366f1" fill="url(#logGrad)" strokeWidth={2} dot={false} />
          <Area type="monotone" dataKey="anomalies" name="Anomalies" stroke="#f87171" fill="url(#anomalyGrad)" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
