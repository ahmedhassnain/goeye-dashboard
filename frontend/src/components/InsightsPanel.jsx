export default function InsightsPanel({ comparisonData, dailyData }) {
  const go  = comparisonData?.scopes?.['GO/FTTH'] || {}
  const ksa = comparisonData?.scopes?.['KSA Average'] || {}
  const m   = dailyData?.metrics || {}

  const insights = []

  if (go.uptime_pct != null) {
    if (go.uptime_pct >= 99.9) {
      insights.push({ type: 'strength', text: `Excellent network uptime at ${go.uptime_pct}%. This exceeds 99.9% of SLA threshold.` })
    } else if (go.uptime_pct < 99) {
      insights.push({ type: 'critical', text: `Network uptime at ${go.uptime_pct}% is below the 99% threshold. ${go.total_disconnections} disconnection events have been recorded.` })
    } else {
      insights.push({ type: 'warning', text: `Network uptime at ${go.uptime_pct}% with ${go.total_disconnections} disconnection events. Median outage: ${go.median_disconnection_sec}s.` })
    }
  }

  if (go.reliability_pct != null && ksa.reliability_pct != null) {
    const diff = (go.reliability_pct - ksa.reliability_pct).toFixed(2)
    if (diff >= 0) {
      insights.push({ type: 'strength', text: `Overall reliability ${go.reliability_pct}% matches or exceeds KSA Average (${ksa.reliability_pct}%).` })
    } else {
      insights.push({ type: 'warning', text: `Reliability gap of ${Math.abs(diff)}% below KSA Average. You need to investigate session failure patterns.` })
    }
  }

  const videoRel = m['Video Conferencing']?.reliability_pct
  if (videoRel != null && videoRel < 98) {
    insights.push({ type: 'bottleneck', text: `Video Conferencing at ${videoRel}% is the weakest category. Review the routing for Zoom and Webex endpoints.` })
  }

  if (go.dns_v4_reliability != null && go.dns_v4_reliability < 80) {
    insights.push({ type: 'bottleneck', text: `DNS v4 reliability at ${go.dns_v4_reliability}%.  ${(100 - go.dns_v4_reliability).toFixed(1)}% of queries are failing.` })
  }

  if (go.dns_v6_reliability != null && go.dns_v6_reliability < 60) {
    insights.push({ type: 'critical', text: `DNS v6 reliability critically low at ${go.dns_v6_reliability}% which means that IPv6 connectivity severely impaired.` })
  }

  if (go.weighted_reliability_pct != null && go.weighted_reliability_pct >= 99.5) {
    insights.push({ type: 'strength', text: `Weighted reliability score of ${go.weighted_reliability_pct}% reflects strong performance by test volume.` })
  }

  const tagStyle = {
    strength:   { color: '#9EBD98', border: '1.5px solid #9EBD98' },
    warning:    { color: '#D4B040', border: '1.5px solid #D4B040' },
    bottleneck: { color: '#C2B8DC', border: '1.5px solid #C2B8DC' },
    critical:   { color: '#E09898', border: '1.5px solid #E09898' },
  }

  const tagLabel = {
    strength: 'Strength', warning: 'Advisory',
    bottleneck: 'Bottleneck', critical: 'Critical',
  }

  if (!insights.length) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {insights.map((ins, i) => (
        <div key={i} style={s.item}>
          <span style={{ ...s.tag, ...tagStyle[ins.type] }}>
            {tagLabel[ins.type]}
          </span>
          <div style={s.text}>{ins.text}</div>
        </div>
      ))}
    </div>
  )
}

const s = {
  item: {
    paddingBottom: 14,
    borderBottom: '1px solid rgba(238,232,223,0.12)',
  },
  tag: {
    display: 'inline-block',
    fontSize: 10, fontWeight: 500,
    letterSpacing: '1.2px', textTransform: 'uppercase',
    padding: '3px 8px', borderRadius: 15,
    marginBottom: 6,
  },
  text: {
    fontSize: 15, color: '#9A8E7E', lineHeight: 1.6,
  },
}