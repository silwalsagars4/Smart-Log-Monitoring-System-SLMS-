import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const SEVERITY_COLORS = {
  information: '#38bdf8',
  warning: '#facc15',
  medium: '#fb923c',
  high: '#f87171',
  disaster: '#c084fc',
}

export default function ErrorTrendChart({ data = [] }) {
  // data: [{_id: {hour, severity}, count}]
  // pivot to: [{hour, information, warning, medium, high, disaster}]
  const hourMap = {}
  data.forEach(({ _id, count }) => {
    const { hour, severity } = _id || {}
    if (!hour || !severity) return
    const h = hour.substring(11) || hour
    hourMap[h] = hourMap[h] || {}
    hourMap[h][severity] = (hourMap[h][severity] || 0) + count
  })

  const chartData = Object.entries(hourMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([hour, counts]) => ({ hour, ...counts }))

  const allSeverities = ['information', 'warning', 'medium', 'high', 'disaster']

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-sm font-semibold text-white">Severity Trend</h3>
        <span className="text-xs text-slate-500">Last 24 hours</span>
      </div>
      {!chartData.length ? (
        <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
          No trend data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" />
            <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e2535',
                border: '1px solid #252d3d',
                borderRadius: '8px',
                fontSize: '11px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
            {allSeverities.map((sev) => (
              <Bar key={sev} dataKey={sev} stackId="a" fill={SEVERITY_COLORS[sev]} radius={sev === 'disaster' ? [3, 3, 0, 0] : [0, 0, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
