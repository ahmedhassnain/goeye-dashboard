export default function KPICard({ title, value, delta, deltaLabel, bg }) {
  const isNeg = delta < 0
  const isPos = delta > 0

  return (
    <div style={{ ...s.card, background: bg || '#D4B040' }}>
      <div style={s.label}>{title}</div>
      <div style={s.value}>{value ?? '-'}</div>
      {delta != null && (
        <div style={{ ...s.delta, color: isNeg ? '#7A1E1E' : isPos ? '#1A4E28' : '#1C1813' }}>
          {isNeg ? '−' : isPos ? '+' : ''}{Math.abs(delta).toFixed(4)}% vs {deltaLabel || 'National Average'}
        </div>
      )}
    </div>
  )
}

const s = {
  card: {
    border: '2px solid #1C1813',
    borderRadius: 20,
    padding: '20px 20px 18px',
  },
  label: {
    fontSize: 20, fontWeight: 200,
    letterSpacing: '1.4px',
    color: '#1C1813', 
    marginBottom: 5,
  },
  value: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 32, fontWeight: 700,
    letterSpacing: '-0.8px', color: '#1C1813',
    lineHeight: 1, marginBottom: 10,
  },
  delta: {
    fontSize: 15, fontWeight: 500,
  },
}