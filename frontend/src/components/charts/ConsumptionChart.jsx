import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

export function ConsumptionChart({ data, meterType }) {
  const color = {
    ELECTRICITY: '#3b82f6',
    HEAT: '#f97316',
    WATER_COLD: '#06b6d4',
    WATER_HOT: '#ef4444',
    GAS: '#a855f7',
    OIL: '#78716c',
  }[meterType] ?? '#6366f1'

  const label = {
    ELECTRICITY: 'Strom (kWh)',
    HEAT: 'Wärme (kWh)',
    WATER_COLD: 'Kaltwasser (m³)',
    WATER_HOT: 'Warmwasser (m³)',
    GAS: 'Gas (m³)',
    OIL: 'Heizöl (L)',
  }[meterType] ?? 'Verbrauch'

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id={`grad-${meterType}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="period_start" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => [`${v}`, label]} />
        <Legend />
        <Area
          type="monotone"
          dataKey="consumption"
          name={label}
          stroke={color}
          fill={`url(#grad-${meterType})`}
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
