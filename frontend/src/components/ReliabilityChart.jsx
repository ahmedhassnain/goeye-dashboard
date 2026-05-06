import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function ReliabilityChart({ dailyData }) {
  if (!dailyData?.metrics) return null

  const m = dailyData.metrics
  const data = [
    { category: 'Games',    value: m['Games']?.reliability_pct },
    { category: 'Social',   value: m['Social Media']?.reliability_pct },
    { category: 'Video Conf.',    value: m['Video Conferencing']?.reliability_pct },
    { category: 'Combined', value: m['Combined']?.weighted_reliability_pct },
  ].filter(d => d.value != null)

  const minVal = Math.max(0, Math.min(...data.map(d => d.value)) - 3)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 4, left: 2, bottom: 0 }} barSize={28}>
        <CartesianGrid strokeDasharray="2 2" stroke="rgba(238,232,223,0.1)" vertical={false} />
        <XAxis
          dataKey="category"
          tick={{ fontSize: 14, fill: '#9A8E7E', fontFamily: 'Athene Voyage' }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          domain={[minVal, 100]}
          tick={{ fontSize: 12, fill: '#5A5248', fontFamily: 'Athene Voyage' }}
          axisLine={false} tickLine={false}
          tickFormatter={v => `${v}%`}
        />
        <Tooltip
          cursor={{ fill: 'rgba(238,232,223,0.06)' }}
          contentStyle={{
            background: '#EEE8DF', border: '2px solid #1C1813',
            borderRadius: 4, fontSize: 11,
            fontFamily: 'Athene Voyage',
          }}
          formatter={v => [`${v.toFixed(2)}%`, 'Reliability']}
        />
        <Bar dataKey="value" fill="#C8A55A" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}