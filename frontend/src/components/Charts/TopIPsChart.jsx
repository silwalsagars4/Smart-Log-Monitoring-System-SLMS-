import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-700 border border-surface-500 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 font-mono">{payload[0].payload.ip}</p>
      <p className="text-brand-400 font-semibold">{payload[0].value} requests</p>
    </div>
  )
}

export default function TopIPsChart({ data = [] }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-sm font-semibold text-white">Top Source IPs</h3>
        <span className="text-xs text-slate-500">By request volume</span>
      </div>
      {!data.length ? (
        <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
          No IP data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis
              type="category"
              dataKey="ip"
              tick={{ fontSize: 9, fill: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}
              width={100}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={i === 0 ? '#f87171' : i === 1 ? '#fb923c' : '#6366f1'}
                  fillOpacity={1 - i * 0.08}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
