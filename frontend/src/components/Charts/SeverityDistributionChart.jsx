import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const COLORS = {
  information: '#38bdf8',
  warning: '#facc15',
  medium: '#fb923c',
  high: '#f87171',
  disaster: '#c084fc',
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="bg-surface-700 border border-surface-500 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="capitalize font-semibold" style={{ color: COLORS[name] }}>{name}</p>
      <p className="text-slate-300">{value} logs</p>
    </div>
  )
}

export default function SeverityDistributionChart({ data = {} }) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({ name: key, value }))

  if (!chartData.length) return (
    <div className="card h-48 flex items-center justify-center text-slate-600 text-sm">
      No severity data yet
    </div>
  )

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-sm font-semibold text-white">Severity Distribution</h3>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={COLORS[entry.name] || '#64748b'}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="capitalize text-xs text-slate-400">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
