export default function HeatmapPanel({ title, hourlyData, valueKey, colorScheme = 'fail' }) {
  if (!hourlyData?.hours) return null

  const hours = Array.from({ length: 24 }, (_, i) => i)
  const values = hours.map(h => {
    const row = hourlyData.hours.find(r => r.hour === h)
    return row ? (row[valueKey] ?? 0) : 0
  })

  const max = Math.max(...values.filter(v => v > 0)) || 1

  const getColor = (val) => {
    if (val === 0) return '#D8EED4'
    const r = Math.min(val / max, 1)
    if (colorScheme === 'disc') {
      return `rgb(${Math.round(158 + r * 80)},${Math.round(189 - r * 100)},${Math.round(152 - r * 100)})`
    }
    if (r < 0.4) {
      const t = r / 0.4
      return `rgb(${Math.round(180 + t * 60)},${Math.round(200 - t * 80)},${Math.round(120 - t * 60)})`
    }
    const t = (r - 0.4) / 0.6
    return `rgb(${Math.round(240 - t * 20)},${Math.round(120 - t * 100)},${Math.round(60 - t * 50)})`
  }

  return (
    <div style={s.row}>
      <div style={s.rowLabel}>{title}</div>
      <div style={s.cells}>
        {hours.map(h => (
          <div
            key={h}
            title={`${h}:00 - ${values[h].toFixed(2)}`}
            style={{ ...s.cell, background: getColor(values[h]) }}
          />
        ))}
      </div>
    </div>
  )
}

const s = {
  row: { marginBottom: 12 },
  rowLabel: {
    fontSize: 13, fontWeight: 500,
    letterSpacing: '1px', 
    color: '#1c1c1c', opacity: 0.85,
    marginBottom: 4,
  },
  cells: { display: 'flex', gap: 2 },
  cell: {
    flex: 1, height: 26,
    borderRadius: 2,
    border: '1px solid rgba(28,24,19,0.08)',
    cursor: 'default',
  },
}