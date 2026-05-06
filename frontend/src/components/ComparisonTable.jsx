export default function ComparisonTable({ data }) {
  if (!data?.scopes) return null

  const go  = data.scopes['GO/FTTH'] || {}
  const ksa = data.scopes['KSA Average'] || {}

  const rows = [
    { label: 'Overall Reliability',    go: go.reliability_pct,           ksa: ksa.reliability_pct,           unit: '%',  higher: true },
    { label: 'Weighted Reliability',   go: go.weighted_reliability_pct,   ksa: ksa.weighted_reliability_pct,  unit: '%',  higher: true },
    { label: 'Network Uptime',         go: go.uptime_pct,                 ksa: ksa.uptime_pct,                unit: '%',  higher: true },
    { label: 'Total Disconnections',   go: go.total_disconnections,       ksa: ksa.total_disconnections,      unit: '',   higher: false },
    { label: 'Median Outage Duration', go: go.median_disconnection_sec,   ksa: ksa.median_disconnection_sec,  unit: 's',  higher: false },
    { label: 'DNS v4 Reliability',     go: go.dns_v4_reliability,         ksa: ksa.dns_v4_reliability,        unit: '%',  higher: true },
    { label: 'DNS v6 Reliability',     go: go.dns_v6_reliability,         ksa: ksa.dns_v6_reliability,        unit: '%',  higher: true },
    { label: 'DNS v4 RTT p50',         go: go.dns_v4_rtt_p50,             ksa: ksa.dns_v4_rtt_p50,            unit: 'ms', higher: false },
    { label: 'DNS v6 RTT p50',         go: go.dns_v6_rtt_p50,             ksa: ksa.dns_v6_rtt_p50,            unit: 'ms', higher: false },
  ]

  const fmt = (v, unit) => {
    if (v === null || v === undefined) return <span style={{ color: '#9A9088' }}>--</span>
    if (typeof v === 'number') {
      return `${v.toFixed(v % 1 === 0 ? 0 : 2)}${unit}`
    }
    return `${v}${unit}`
  }

  const getStatus = (go, ksa, higher) => {
    if (go === null || ksa === null || go === undefined || ksa === undefined) return null
    if (higher) return go >= ksa ? 'better' : 'worse'
    return go <= ksa ? 'better' : 'worse'
  }

  const getDiff = (go, ksa, unit, higher) => {
    if (go == null || ksa == null) return null
    const diff = go - ksa
    const sign = diff >= 0 ? '+' : ''
    const color = higher
      ? (diff >= 0 ? '#1A4E28' : '#7A1E1E')
      : (diff <= 0 ? '#1A4E28' : '#7A1E1E')
    return (
      <span style={{ 
        color, 
        fontWeight: 600, 
        fontFamily: "'Athene Voyage', serif", 
        fontSize: 15,
        letterSpacing: '-0.3px'
      }}>
        {sign}{diff.toFixed(diff % 1 === 0 ? 0 : 2)}{unit}
      </span>
    )
  }

  return (
    <div style={styles.wrapper}>
      <table style={styles.table}>
        <thead>
          <tr style={styles.headerRow}>
            <th style={styles.th}>Metric</th>
            <th style={styles.th}>GO / FTTH</th>
            <th style={styles.th}>KSA Average</th>
            <th style={{ ...styles.th, textAlign: 'center' }}>Difference</th>
            <th style={{ ...styles.th, textAlign: 'center' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const status = getStatus(row.go, row.ksa, row.higher)
            return (
              <tr key={row.label} style={{ 
                borderBottom: '1px solid rgba(26, 23, 18, 0.15)',
                background: 'transparent'
              }}>
                <td style={styles.td}>
                  <span style={styles.metricLabel}>{row.label}</span>
                </td>
                <td style={styles.td}>
                  <span style={styles.valueHighlight}>
                    {fmt(row.go, row.unit)}
                  </span>
                </td>
                <td style={styles.td}>
                  <span style={styles.valueStandard}>
                    {fmt(row.ksa, row.unit)}
                  </span>
                </td>
                <td style={{ ...styles.td, textAlign: 'center' }}>
                  {getDiff(row.go, row.ksa, row.unit, row.higher)}
                </td>
                <td style={{ ...styles.td, textAlign: 'center' }}>
                  {status && (
                    <span style={{
                      ...styles.statusPill,
                      background: status === 'better' ? 'rgba(31, 116, 54, 0.4)' : 'rgba(177, 28, 28, 0.4)',
                      color: status === 'better' ? '#1C1813' : '#5f1414',
                    }}>
                      {status === 'better' ? '▲ Above Average' : '▼ Below Average'}
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const styles = {
  wrapper: { 
    overflowX: 'auto', 
    borderRadius: 20, 
    border: '2px solid #1C1813',
    background: 'rgb(158, 189, 152)',
  },
  table: { 
    width: '100%', 
    borderCollapse: 'collapse', 
    fontSize: 15,
  },
  headerRow: {
    borderBottom: '2px solid #1C1813',
  },
  th: {
    padding: '18px 30px',
    textAlign: 'left',
    fontWeight: 600,
    fontSize: 17,
    color: '#1C1813',
    letterSpacing: '0.5px',
    background: 'rgb(158, 189, 152)',
    fontFamily: "'Athene Voyage', sans-serif",
  },
  td: {
    padding: '12px 30px',
    color: '#1C1813',
  },
  metricLabel: { 
    fontSize: 17, 
    color: '#1C1813', 
    fontWeight: 500,
    fontFamily: "'Athene Voyage', sans-serif",
    opacity: "0.75"
  },
  valueHighlight: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 15,
    fontWeight: 700,
    color: '#1C1813',
    letterSpacing: '-0.2px',
  },
  valueStandard: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 15,
    fontWeight: 500,
    color: '#3a3631',
    letterSpacing: '-0.2px',
  },
  statusPill: {
    display: 'inline-block',
    fontSize: 13,
    fontWeight: 400,
    padding: '4px 12px',
    borderRadius: 20,
    border: '1px solid #211405',
    letterSpacing: '0.3px',
    fontFamily: "'Athene Voyage', sans-serif",
  },
}