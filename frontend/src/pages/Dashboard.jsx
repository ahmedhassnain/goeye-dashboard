import { useState, useEffect, useRef } from 'react'
import { getComparison, getDaily, getDailyRange, getHourly, getAvailableDates, getLoadedDates, loadDate, loadDates, getLoadStatus, getLoadStatuses } from '../api/client'
import KPICard from '../components/KPICard'
import ComparisonTable from '../components/ComparisonTable'
import HeatmapPanel from '../components/HeatmapPanel'
import ReliabilityChart from '../components/ReliabilityChart'
import InsightsPanel from '../components/InsightsPanel'
import { getGamingBreakdown, getSocialBreakdown, getVideoBreakdown, getDnsDetail, getTrends } from '../api/client'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function Dashboard({ section, user }) {
  const [availableDates, setAvailableDates] = useState([])
  const [loadedDates, setLoadedDates]       = useState(new Set())
  const [selectedDate, setSelectedDate]     = useState(null)
  const [loadingDate, setLoadingDate]       = useState(false)
  const [loadProgress, setLoadProgress]     = useState('')
  const [comparison, setComparison]         = useState(null)
  const [goDaily, setGoDaily]               = useState(null)
  const [rangeMode, setRangeMode]           = useState(false)
  const [rangePopupOpen, setRangePopupOpen] = useState(false)
  const [rangeStart, setRangeStart]         = useState(null)
  const [rangeEnd, setRangeEnd]             = useState(null)
  const [rangeDaily, setRangeDaily]         = useState(null)
  const [rangeError, setRangeError]         = useState(null)
  const [rangeStatuses, setRangeStatuses]   = useState({})
  const [rangeLoading, setRangeLoading]     = useState(false)
  const [selectedPreset, setSelectedPreset] = useState(null)
  const [heatmaps, setHeatmaps]             = useState({})
  const [loading, setLoading]               = useState(false)
  const [error, setError]                   = useState(null)
  const [breakdowns, setBreakdowns] = useState({})
  const [dnsDetail, setDnsDetail]           = useState(null)
  const [trends, setTrends]                 = useState(null)
  const [scrolled, setScrolled] = useState(false)
  const rangeButtonRef = useRef(null)

useEffect(() => {
  const handler = () => {
    // Detect if page is scrolled more than 20px
    setScrolled(window.scrollY > 20)
  }
  window.addEventListener('scroll', handler)
  return () => window.removeEventListener('scroll', handler)
}, [])

  useEffect(() => {
    Promise.allSettled([getAvailableDates(), getLoadedDates()]).then(([availableRes, loadedRes]) => {
      const available = availableRes.status === 'fulfilled' ? availableRes.value : []
      const loaded    = loadedRes.status   === 'fulfilled' ? loadedRes.value   : []
      setAvailableDates(available)
      setLoadedDates(new Set(loaded))
      const def = loaded[0] || available[0]
      if (def) setSelectedDate(def)
    })
  }, [])

  useEffect(() => {
    if (rangeMode) return
    if (!selectedDate) return
    const dateKey = selectedDate.replace(/-/g, '')
    if (loadedDates.has(selectedDate)) {
      fetchData(selectedDate)
    } else {
      triggerLoad(dateKey, selectedDate)
    }
  }, [selectedDate, rangeMode])

  function normalizeLoadedDate(date) {
    if (!date) return date
    if (date.includes('-')) return date
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
  }

  async function triggerLoad(dateKey, dateDisplay) {
    setLoadingDate(true)
    setLoadProgress('Connecting to measurement server...')
    setComparison(null); setGoDaily(null)
    try {
      await loadDate(dateKey)
      const msgs = ['Downloading archive...','Extracting data...','Parsing measurements...','Running aggregations...','Almost ready...']
      let i = 0
      const poll = setInterval(async () => {
        setLoadProgress(msgs[Math.min(i++, msgs.length - 1)])
        try {
          const { status } = await getLoadStatus(dateKey)
          if (status === 'done') {
            clearInterval(poll)
            setLoadedDates(prev => new Set([...prev, dateDisplay]))
            setLoadingDate(false); setLoadProgress('')
            fetchData(dateDisplay)
          } else if (status.startsWith('error')) {
            clearInterval(poll)
            setLoadingDate(false)
            setError(`Failed to load ${dateDisplay}`)
          }
        } catch { clearInterval(poll); setLoadingDate(false) }
      }, 4000)
    } catch (e) { setError(e.message); setLoadingDate(false) }
  }

  function getDateRange(start, end) {
    if (!start || !end) return []
    const dates = []
    const cursor = new Date(start)
    const last = new Date(end)
    while (cursor <= last) {
      dates.push(cursor.toISOString().slice(0, 10))
      cursor.setDate(cursor.getDate() + 1)
    }
    return dates
  }

  // Union of dates already in the DB and remotely available dates,
  // sorted newest-first. When the measurement server is not configured only loaded dates appear.
  const displayDates = [...new Set([...loadedDates, ...availableDates])].sort().reverse()

  function getPresetDates(preset) {
    if (displayDates.length === 0) {
      return { start: '', end: '' }
    }

    const sortedDates = [...displayDates].sort()
    const end = sortedDates[sortedDates.length - 1]
    let offset

    if (preset === '3days') {
      offset = 2
    } else if (preset === 'week') {
      offset = 6
    } else if (preset === 'month') {
      offset = 29
    } else {
      return { start: '', end }
    }

    const startIndex = Math.max(0, sortedDates.length - 1 - offset)
    return { start: sortedDates[startIndex], end }
  }

  const rangeDates = getDateRange(rangeStart, rangeEnd)
  const rangeDoneCount = Object.values(rangeStatuses).filter(s => s === 'done').length
  const rangePendingCount = Object.values(rangeStatuses).filter(s => s === 'processing').length

  const rangeProgressMessage = () => {
    if (!rangeMode || rangeDates.length === 0) return ''
    if (loadingDate) return loadProgress || 'Loading selected range...'
    if (rangeDaily) return `Selected range loaded: ${rangeDaily.start_date} to ${rangeDaily.end_date}`
    if (rangePendingCount > 0 || rangeDoneCount > 0) return 'Preparing selected date range...'
    return 'Select a date range and click Apply.'
  }

  async function startRangeLoad(dates) {
    if (dates.length === 0) return
    setRangeLoading(true)
    setLoadingDate(true)
    setLoadProgress('Starting range downloads...')
    setRangeError(null)
    console.log('startRangeLoad dates', dates)
    try {
      await loadDates(dates)
    } catch (e) {
      console.error('Range bulk load failed', e)
      if (e?.response) {
        throw new Error(`Range load failed: ${e.response.status} ${e.response.statusText}`)
      }
      throw new Error(e.message || 'Network error while loading date range')
    }
  }

  async function pollRangeStatuses(dates) {
    const pending = new Set(dates)
    const statuses = {}
    let maxAttempts = 300 // ~12.5 mins at 2.5s interval (with backoff)
    let attempts = 0
    const maxNoProgressAttempts = 15
    let noProgressCount = 0

    while (pending.size > 0 && attempts < maxAttempts) {
      attempts++
      
      // Adaptive backoff: start at 2.5s, gradually increase to 5s
      const delayMs = Math.min(2500 + attempts * 100, 5000)
      await new Promise(resolve => setTimeout(resolve, delayMs))
      
      try {
        const response = await getLoadStatuses(Array.from(pending))
        const items = response.statuses || []

        if (!items || items.length === 0) {
          noProgressCount++
          console.warn(`Poll attempt ${attempts}: Empty response, no progress count: ${noProgressCount}`)
          if (noProgressCount > maxNoProgressAttempts) {
            throw new Error('No response from server after multiple attempts. The server may be busy.')
          }
          continue
        }

        noProgressCount = 0
        let anyProgress = false

        items.forEach(item => {
          const normalized = normalizeLoadedDate(item.date)
          statuses[normalized] = item.status

          if (item.status === 'done') {
            anyProgress = true
            pending.delete(normalized)
            setLoadedDates(prev => new Set([...prev, normalized]))
          } else if (item.status?.startsWith('error')) {
            anyProgress = true
            pending.delete(normalized)
          }
        })

        setRangeStatuses({ ...statuses })
        
        if (!anyProgress) {
          noProgressCount++
        } else {
          noProgressCount = Math.max(0, noProgressCount - 2) // Decay progress counter
        }
      } catch (pollErr) {
        console.warn(`Poll attempt ${attempts} failed:`, pollErr.message)
        noProgressCount++
        if (noProgressCount > maxNoProgressAttempts) {
          throw new Error(`Unable to poll status: ${pollErr.message}`)
        }
      }
    }

    // Check for any errors in final statuses
    const errorDates = Object.entries(statuses)
      .filter(([_, status]) => status?.startsWith('error'))
      .map(([date]) => date)
    
    if (errorDates.length > 0) {
      console.warn('Some dates had errors:', errorDates, statuses)
    }

    if (attempts >= maxAttempts && pending.size > 0) {
      throw new Error(`Timeout loading dates. Still waiting for: ${Array.from(pending).join(', ')}`)
    }
  }

  async function fetchRangeData(start, end) {
    setLoading(true)
    setRangeError(null)
    try {
      console.log('fetchRangeData start/end', start, end)
      const [compResult, rangeResult] = await Promise.allSettled([
        getComparison(end),
        getDailyRange('GO/FTTH', start, end)
      ])

      if (rangeResult.status === 'rejected') {
        const err = rangeResult.reason
        console.error('Range fetch failed', err)
        if (err?.response?.status === 404) {
          throw new Error(`No daily range data available for ${start} to ${end}. Please try a smaller range or ensure those dates are loaded.`)
        }
        throw err
      }

      if (compResult.status === 'fulfilled') {
        setComparison(compResult.value)
      }

      const rangeData = rangeResult.value
      setRangeDaily(rangeData)

      // Aggregate range metrics into a single metrics object
      const aggregatedMetrics = aggregateRangeMetrics(rangeData.metrics_by_date)
      setGoDaily({ metrics: aggregatedMetrics })

      // Fetch heatmaps and other data for the end date to keep UI consistent
      const [
        gamesHeatmap,
        socialHeatmap,
        videoHeatmap,
        discHeatmap,
        gamingBreakdown,
        socialBreakdown,
        videoBreakdown,
        dnsDetail,
        trendsData
      ] = await Promise.all([
        getHourly('GO/FTTH', end, 'Games'),
        getHourly('GO/FTTH', end, 'Social Media'),
        getHourly('GO/FTTH', end, 'Video Conferencing'),
        getHourly('GO/FTTH', end, 'Disconnection'),
        getGamingBreakdown('GO/FTTH', end),
        getSocialBreakdown('GO/FTTH', end),
        getVideoBreakdown('GO/FTTH', end),
        getDnsDetail('GO/FTTH', end),
        getTrends('GO/FTTH'),
      ])

      setHeatmaps({ 
        games: gamesHeatmap, 
        social: socialHeatmap, 
        video: videoHeatmap, 
        disc: discHeatmap 
      })
      setBreakdowns({ 
        gaming: gamingBreakdown,
        social: socialBreakdown, 
        video: videoBreakdown 
      })
      setDnsDetail(dnsDetail)
      setTrends(trendsData)
    } catch (e) {
      console.error('Error fetching range data:', e)
      setError(e.message || 'Failed to fetch range metrics')
    } finally {
      setLoading(false)
    }
  }

  function aggregateRangeMetrics(metricsByDate) {
    if (!metricsByDate) return {}

    const categories = ['Games', 'Social Media', 'Video Conferencing', 'Combined']
    const aggregated = {}

    categories.forEach(category => {
      const values = Object.values(metricsByDate).map(dateMetrics => dateMetrics[category]).filter(Boolean)
      if (values.length === 0) return

      const avg = (field) => {
        const nums = values.map(v => v[field]).filter(n => n != null)
        return nums.length > 0 ? nums.reduce((a, b) => a + b, 0) / nums.length : null
      }

      aggregated[category] = {
        reliability_pct: avg('reliability_pct'),
        weighted_reliability_pct: avg('weighted_reliability_pct'),
        uptime_pct: avg('uptime_pct'),
        total_tests: avg('total_tests'),
        total_disconnections: avg('total_disconnections'),
        median_disconnection_sec: avg('median_disconnection_sec'),
        dns_v4_reliability: avg('dns_v4_reliability'),
        dns_v6_reliability: avg('dns_v6_reliability'),
        dns_v4_rtt_p50: avg('dns_v4_rtt_p50'),
        dns_v6_rtt_p50: avg('dns_v6_rtt_p50'),
      }
    })

    return aggregated
  }

  async function handleRangeApply() {
    setRangeError(null)
    if (!rangeStart || !rangeEnd) {
      setRangeError('Select both range start and end dates.')
      return
    }
    if (new Date(rangeStart) > new Date(rangeEnd)) {
      setRangeError('Start date must be before or equal to end date.')
      return
    }

    setRangeDaily(null)
    setRangeStatuses({})
    setRangeLoading(true)
    setLoadingDate(true)
    setLoadProgress('Starting range downloads...')

    const missing = rangeDates.filter(d => !loadedDates.has(d))
    try {
      if (missing.length > 0) {
        setLoadProgress(`Requesting downloads for ${missing.length} missing date(s)...`)
        await startRangeLoad(missing)
        setLoadProgress(`Monitoring download progress for ${missing.length} date(s)...`)
        await pollRangeStatuses(missing)
      } else {
        setLoadProgress('All dates already loaded, preparing data...')
      }
      setLoadProgress('Fetching aggregated range data...')
      await fetchRangeData(rangeStart, rangeEnd)
      setLoadProgress('')
      setRangePopupOpen(false)
    } catch (e) {
      console.error('Range load error:', e)
      setRangeError(e.message || 'Unable to load selected date range. Please try a smaller range or check your connection.')
    } finally {
      setRangeLoading(false)
      setLoadingDate(false)
      setLoadProgress('')
    }
  }

async function fetchData(date) {
  setLoading(true); setError(null)
  try {
    const [comp, daily] = await Promise.all([getComparison(date), getDaily('GO/FTTH', date)])
    setComparison(comp); setGoDaily(daily)
    
    const [
      gamesHeatmap,
      socialHeatmap,
      videoHeatmap,
      discHeatmap,
      gamingBreakdown,
      socialBreakdown,
      videoBreakdown,
      dnsDetail,
      trendsData
    ] = await Promise.all([
      getHourly('GO/FTTH', date, 'Games'),
      getHourly('GO/FTTH', date, 'Social Media'),
      getHourly('GO/FTTH', date, 'Video Conferencing'),
      getHourly('GO/FTTH', date, 'Disconnection'),
      getGamingBreakdown('GO/FTTH', date),
      getSocialBreakdown('GO/FTTH', date),
      getVideoBreakdown('GO/FTTH', date),
      getDnsDetail('GO/FTTH', date),
      getTrends('GO/FTTH'),
    ])

    // Add console logs to debug DNS data
    console.log('DNS Detail Response:', dnsDetail)
    console.log('DNS v4 data:', dnsDetail?.v4)
    console.log('DNS v6 data:', dnsDetail?.v6)
    console.log('DNS nameservers v4:', dnsDetail?.v4?.nameservers)
    console.log('DNS nameservers v6:', dnsDetail?.v6?.nameservers)
    
    setHeatmaps({ 
      games: gamesHeatmap, 
      social: socialHeatmap, 
      video: videoHeatmap, 
      disc: discHeatmap 
    })
    setBreakdowns({ 
      gaming: gamingBreakdown, 
      social: socialBreakdown, 
      video: videoBreakdown 
    })
    setDnsDetail(dnsDetail)
    setTrends(trendsData)
  } catch (e) { 
    console.error('Error fetching data:', e)
    setError(e.message) 
  } finally { 
    setLoading(false) 
  }
}

  const go  = comparison?.scopes?.['GO/FTTH'] || {}
  const ksa = comparison?.scopes?.['KSA Average'] || {}
  const m   = goDaily?.metrics || {}
  const selectedDateLabel = rangeMode ? `${rangeStart || 'Start'} – ${rangeEnd || 'End'}` : selectedDate

  const showLoadScreen =
    (loadingDate || loading) ||
    (!rangeMode && (!comparison || !goDaily || Object.keys(heatmaps).length === 0)) ||
    (rangeMode && rangeLoading && !rangeDaily)

  const sectionTitle = {
    overview: 'Network Overview', benchmark: 'Benchmark Comparison',
    heatmaps: 'Reliability Heatmaps', gaming: 'Gaming Performance',
    social: 'Social Media', video: 'Video Conferencing',
    reliability: 'Network Reliability', strategic: 'Strategic Recommendations',
  }

  if (showLoadScreen) return (
    <div style={s.loadScreen}>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div style={s.loadSpinner} />
      
      <div style={s.loadText}>
        {loadingDate
          ? loadProgress || 'Preparing data...'
          : 'Loading analytics...'}
      </div>

      <div style={s.loadSub}>
        Please wait while we prepare your dashboard
      </div>
    </div>
  )

  if (error) return (
    <div style={s.loadScreen}>
      <div style={{ fontSize: 13, color: '#7A1E1E' }}>{error}</div>
    </div>
  )

  const renderSection = () => {
    switch (section) {
      case 'benchmark':   return <BenchmarkSection comparison={comparison} />
      case 'heatmaps':    return <HeatmapSection heatmaps={heatmaps} selectedDate={selectedDateLabel} />
      case 'strategic':   return <StrategicSection comparison={comparison} goDaily={goDaily} />
      case 'gaming':  return <GamingSection metrics={m['Games']} breakdown={breakdowns.gaming} selectedDate={selectedDateLabel} />
      case 'social':  return <SocialSection metrics={m['Social Media']} breakdown={breakdowns.social} selectedDate={selectedDateLabel} />
      case 'video':   return <VideoSection  metrics={m['Video Conferencing']} breakdown={breakdowns.video} selectedDate={selectedDateLabel} />
      case 'reliability': return <ReliabilitySection go={go} ksa={ksa} heatmaps={heatmaps} dns={dnsDetail} trends={trends} />
      default:            return <OverviewSection go={go} ksa={ksa} m={m} heatmaps={heatmaps} comparison={comparison} goDaily={goDaily} user={user} selectedDate={selectedDateLabel} rangeDaily={rangeDaily} />
      
    }
  }

return (
  <div style={s.page}>
    {/* The Sticky Wrapper: Keep it transparent so it doesn't look like a block */}
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '16px 0', // Provides space for the pill to "float"
    }}>
      <div style={{
        ...s.topbar,
        pointerEvents: 'auto', // Re-enable clicks for the actual bar
        // Dynamic animation properties
        padding: scrolled ? '8px 40px' : '14px 30px',
        margin: scrolled ? '0 40px' : '0 16px', // Shrinks slightly on scroll
        boxShadow: scrolled ? '0 12px 30px rgba(0,0,0,0.12)' : 'none',
        background: scrolled ? '#F5F0E8' : '#EEE8DF', // Subtle color shift
        borderRadius: '50px', // Keeps the pill shape consistent
        transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)', // Smooth "out-out" easing
        opacity: scrolled ? 0.8 : 1,
        // Optional: subtle glass effect (high-end feel)
        backdropFilter: scrolled ? 'blur(10px)' : 'blur(0px)',
        WebkitBackdropFilter: scrolled ? 'blur(10px)' : 'blur(0px)',

        // Optional: slightly more transparent background on scroll
        backgroundColor: scrolled 
          ? 'rgba(245, 240, 232, 0.85)' 
          : 'rgba(238, 232, 223, 1)',
      }}>
        <div style={s.topbarTitle}>{sectionTitle[section] || 'Network Overview'}</div>
        <div style={s.topbarRight}>
          <div style={s.rangePanelTop}>
            <button
              style={rangeMode ? s.rangeToggleInactive : s.rangeToggleActive}
              onClick={() => {
                setRangeMode(false)
                setRangePopupOpen(false)
                setRangeError(null)
                setRangeDaily(null)
                setSelectedPreset(null)
              }}
            >Single</button>
            <button
              ref={rangeButtonRef}
              style={rangeMode ? s.rangeToggleActive : s.rangeToggleInactive}
              onClick={() => {
                setRangeMode(true)
                setRangePopupOpen(true)
                setRangeError(null)
                setSelectedPreset(null)
                setRangeStart(null)
                setRangeEnd(null)
              }}
            >Range</button>
          </div>

          {!rangeMode && (
            <select
              style={s.dateSelect}
              value={selectedDate || ''}
              onChange={e => setSelectedDate(e.target.value)}
            >
              {displayDates.map(d => (
                <option key={d} value={d}>
                  {d} {loadedDates.has(d) ? '✓' : '↓'}
                </option>
              ))}
            </select>
          )}
          {rangeMode && selectedPreset && (
            <div style={s.rangeBadge}>{selectedPreset === 'custom' ? 'Custom Range' : selectedPreset === '3days' ? 'Last 3 Days' : selectedPreset === 'week' ? 'Last Week' : 'Last Month'}</div>
          )}

          <div style={s.scopeBadge}>GO FTTH</div>
          <div style={s.uptimeBadge}>
            Uptime: <strong style={{ color: '#1A4E28' }}>{go.uptime_pct?.toFixed(3)}%</strong>
          </div>
        </div>
      </div>
      {rangeMode && rangePopupOpen && (
        <div style={s.rangePopup}>
          <div style={s.presetHeader}>Choose range</div>
          <div style={s.presetButtons}>
            <button
              type="button"
              style={selectedPreset === '3days' ? s.presetButtonActive : s.presetButton}
              onClick={() => {
                setSelectedPreset('3days')
                const { start, end } = getPresetDates('3days')
                setRangeStart(start)
                setRangeEnd(end)
              }}
            >Last 3 Days</button>
            <button
              type="button"
              style={selectedPreset === 'week' ? s.presetButtonActive : s.presetButton}
              onClick={() => {
                setSelectedPreset('week')
                const { start, end } = getPresetDates('week')
                setRangeStart(start)
                setRangeEnd(end)
              }}
            >Last Week</button>
            <button
              type="button"
              style={selectedPreset === 'month' ? s.presetButtonActive : s.presetButton}
              onClick={() => {
                setSelectedPreset('month')
                const { start, end } = getPresetDates('month')
                setRangeStart(start)
                setRangeEnd(end)
              }}
            >Last Month</button>
            <button
              type="button"
              style={selectedPreset === 'custom' ? s.presetButtonActive : s.presetButton}
              onClick={() => {
                setSelectedPreset('custom')
                setRangeStart(null)
                setRangeEnd(null)
              }}
            >Custom Range</button>
          </div>
          {selectedPreset === 'custom' && (
            <div style={s.rangeInputRow}>
              <select
                style={s.dateSelect}
                value={rangeStart || ''}
                onChange={e => setRangeStart(e.target.value)}
              >
                <option value="">Start</option>
                {displayDates.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <span style={s.rangeSeparator}>to</span>
              <select
                style={s.dateSelect}
                value={rangeEnd || ''}
                onChange={e => setRangeEnd(e.target.value)}
              >
                <option value="">End</option>
                {displayDates.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          )}
          <div style={s.popupActions}>
            <button type="button" style={s.applyButton} onClick={handleRangeApply}>Apply</button>
            <button
              type="button"
              style={s.changePresetButton}
              onClick={() => {
                setRangePopupOpen(false)
                setSelectedPreset(null)
                setRangeError(null)
                setRangeStart(null)
                setRangeEnd(null)
              }}
            >Close</button>
          </div>
          {rangeError ? <div style={s.rangeError}>{rangeError}</div> : null}
        </div>
      )}
    </div>

    <div style={s.content}>
      {renderSection()}
    </div>
  </div>
)
}

/* ── OVERVIEW ── */
function OverviewSection({ go, ksa, m, heatmaps, comparison, goDaily, user, selectedDate, rangeDaily }) {
  const firstName = user?.fullName?.split(' ')[0] || 'there'
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening'

  return (
    <div style={s.body}>

      {/* Greeting */}
      <div style={{ marginBottom: 28 }}>
        <div style={s.greetH}>
          {greeting}, <em style={{ fontStyle: 'italic', fontWeight: 400 }}>{firstName}.</em>
        </div>
        <div style={s.greetCap}>Here's a complete analysis of what happened while you were away.</div>
      </div>
      {rangeDaily && (
        <div style={s.rangeSummaryBox}>
          <div style={s.rangeSummaryTitle}>Loaded Date Range</div>
          <div style={s.rangeSummaryText}>
            {rangeDaily.start_date} to {rangeDaily.end_date} · {Object.keys(rangeDaily.metrics_by_date || {}).length} Dates Loaded
          </div>
        </div>
      )}

      {/* Row 1 - three metric cards */}
      <div style={s.threeCol}>
        <KPICard
          title="Network Uptime"
          value={go.uptime_pct?.toFixed(4) + '%'}
          delta={go.uptime_pct != null && ksa.uptime_pct != null ? go.uptime_pct - ksa.uptime_pct : null}
          bg="#D4B040"
        />
        <KPICard
          title="Weighted Reliability"
          value={go.weighted_reliability_pct?.toFixed(4) + '%'}
          delta={go.weighted_reliability_pct != null && ksa.weighted_reliability_pct != null ? go.weighted_reliability_pct - ksa.weighted_reliability_pct : null}
          bg="#C2B8DC"
        />
        <KPICard
          title="Video Conf. Reliability"
          value={m['Video Conferencing']?.reliability_pct?.toFixed(4) + '%'}
          delta={m['Video Conferencing']?.reliability_pct != null && ksa.reliability_pct != null ? m['Video Conferencing'].reliability_pct - ksa.reliability_pct : null}
          bg="#E09898"
        />
      </div>

      {/* Row 2 - chart + diagnostics */}
      <div style={s.twoCol}>
        <div style={{ ...s.card, ...s.inkCard, display: 'flex', flexDirection: 'column', padding: '22px 24px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
            <div>
              <div style={s.chartTitle}>Reliability by Category</div>
              <div style={s.chartSub}>GO FTTH ~ {selectedDate}</div>
            </div>
            <div style={s.chartPull}>{go.weighted_reliability_pct?.toFixed(1)}%</div>
          </div>
          <div style={{ flex: 1, minHeight: 150 }}>
            <ReliabilityChart dailyData={goDaily} />
          </div>
        </div>

        <div style={{ ...s.card, background: '#9EBD98', padding: '20px 20px 16px' }}>
          <div style={s.statSectionLabel}>Network Diagnostics</div>
          {[
            ['DNS v4 Reliability', go.dns_v4_reliability?.toFixed(2) + '%', go.dns_v4_reliability < 80],
            ['DNS v6 Reliability', go.dns_v6_reliability?.toFixed(2) + '%', go.dns_v6_reliability < 80],
            ['DNS v4 RTT p50',     (go.dns_v4_rtt_p50?.toFixed(1) || '--') + ' ms', false],
            ['DNS v6 RTT p50',     (go.dns_v6_rtt_p50?.toFixed(1) || '--') + ' ms', false],
            ['Disconnections',     go.total_disconnections, go.total_disconnections > 30],
            ['Median Outage',      (go.median_disconnection_sec || '--') + ' s', false],
            ['KSA Uptime',         ksa.uptime_pct?.toFixed(2) + '%', false, true],
            ['KSA Reliability',    ksa.reliability_pct?.toFixed(2) + '%', false, true],
          ].map(([label, val, isRed, isGreen]) => (
            <div key={label} style={s.statRow}>
              <span style={s.statK}>{label}</span>
              <span style={{ ...s.statV, ...(isRed ? { color: '#7A1E1E' } : isGreen ? { color: '#1A4E28' } : {}) }}>
                {val ?? '--'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Row 3 - heatmaps full width */}
      <div style={{ ...s.card, background: '#dbd0c0', padding: '22px 24px 20px' }}>
        <div style={s.statSectionLabel}>Hourly Failure Patterns</div>
        <div style={{ ...s.chartTitle, color: '#1c1c1c', marginBottom: 1 }}>Fail Rate by Hour of Day</div>
        <div style={{ fontSize: 12, opacity: 0.8, color: '#333232', fontStyle: 'italic', marginBottom: 20 }}>
          Each cell represents the failure rate % for that hour. Darker means more failures.
        </div>
        <HeatmapPanel title="Games"         hourlyData={heatmaps.games}  valueKey="fail_rate_pct" />
        <HeatmapPanel title="Social Media"  hourlyData={heatmaps.social} valueKey="fail_rate_pct" />
        <HeatmapPanel title="Video Conf."   hourlyData={heatmaps.video}  valueKey="fail_rate_pct" />
        <HeatmapPanel title="Disconnection (min)" hourlyData={heatmaps.disc} valueKey="disconnection_minutes" colorScheme="disc" />
        <div style={{ display: 'flex', gap: 2, marginTop: 8 }}>
          {Array.from({ length: 24 }, (_, h) => (
            <div key={h} style={{ flex: 1, textAlign: 'center', fontSize: 9, color: '#1c1c1c' }}>
              {h % 4 === 0 ? h : ''}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
          <span style={{ fontSize: 10, color: '#1c1c1c' }}>Low</span>
          {['#D8EED4','#C8D890','#E8A040','#D84020'].map((c, i) => (
            <div key={i} style={{ width: 14, height: 8, borderRadius: 1, background: c }} />
          ))}
          <span style={{ fontSize: 10, color: '#1c1c1c' }}>High</span>
        </div>
      </div>

      {/* Row 4 - insights + reliability breakdown */}
      <div style={s.twoCol}>
        <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px 20px' }}>
          <div style={s.chartTitle}>Auto-Generated Insights</div>
          <div style={{ fontSize: 12, color: '#baad99', marginBottom: 20 }}>
            Performance Analysis · {selectedDate}
          </div>
          <InsightsPanel comparisonData={comparison} dailyData={goDaily} />
        </div>

        <div style={{ ...s.card, background: '#D4B040', padding: '20px 20px 16px' }}>
          <div style={s.statSectionLabel}>Reliability Breakdown</div>
          {[
            ['Overall',       go.reliability_pct?.toFixed(2) + '%'],
            ['Gaming',        m['Games']?.reliability_pct?.toFixed(2) + '%'],
            ['Social Media',  m['Social Media']?.reliability_pct?.toFixed(2) + '%'],
            ['Video Conf.',   m['Video Conferencing']?.reliability_pct?.toFixed(2) + '%'],
            ['KSA Gaming',    ksa.reliability_pct != null ? '100%' : '--'],
            ['KSA Social',    '99.96%'],
            ['KSA Video',     '98.16%'],
            ['Total Tests',   go.total_tests?.toLocaleString()],
          ].map(([label, val]) => (
            <div key={label} style={s.statRow}>
              <span style={s.statK}>{label}</span>
              <span style={s.statV}>{val ?? '--'}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

/* ── OTHER SECTIONS - same logic, editorial wrapper ── */
function BenchmarkSection({ comparison }) {
  return (
    <div style={s.body}>
      <div style={{ ...s.card, background: '#EEE8DF', padding: '22px 24px' }}>
        <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 4 }}>GO / FTTH vs KSA Average</div>
        <div style={{ fontSize: 15, color: '#9A9088', marginBottom: 20 }}>Full metric comparison</div>
        <ComparisonTable data={comparison} />
      </div>
    </div>
  )
}

function HeatmapSection({ heatmaps, selectedDate }) {
  return (
    <div style={s.body}>
      <div style={{ ...s.card, background: '#E8DFD0', padding: '22px 24px 20px' }}>
        <div style={s.statSectionLabel}>Hourly Failure Patterns</div>
        <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 16 }}>All Categories -- {selectedDate}</div>
        <HeatmapPanel title="Games"         hourlyData={heatmaps.games}  valueKey="fail_rate_pct" />
        <HeatmapPanel title="Social Media"  hourlyData={heatmaps.social} valueKey="fail_rate_pct" />
        <HeatmapPanel title="Video Conf."   hourlyData={heatmaps.video}  valueKey="fail_rate_pct" />
        <HeatmapPanel title="Disconnection (min)" hourlyData={heatmaps.disc} valueKey="disconnection_minutes" colorScheme="disc" />
      </div>
    </div>
  )
}

function ReliabilitySection({ go, ksa, heatmaps, dns, trends }) {

  const trendData = trends ? trends.dates.map(d => ({
    date: d.slice(5), // MM-DD
    uptime: trends.data[d]?.Combined?.uptime,
    reliability: trends.data[d]?.Combined?.reliability,
    dns_v4: trends.data[d]?.Combined?.dns_v4_reliability,
    dns_v6: trends.data[d]?.Combined?.dns_v6_reliability,
  })) : []

  return (
    <div style={s.body}>

      {/* Uptime + disconnections */}
      <div style={s.twoCol}>
        <div style={{ ...s.card, background: '#D4B040', padding: '24px' }}>
          <div style={s.statSectionLabel}>Network Uptime</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 52, fontWeight: 700, letterSpacing: '-2px', color: '#1C1813', lineHeight: 1 }}>
            {go.uptime_pct?.toFixed(4)}<span style={{ fontSize: 18, fontWeight: 400 }}>%</span>
          </div>
          <div style={{ fontSize: 15, color: '#1C1813', opacity: 0.6, marginTop: 8 }}>KSA Average: {ksa.uptime_pct?.toFixed(4)}%</div>
        </div>
        <div style={{ ...s.card, background: '#9EBD98', padding: '20px' }}>
          <div style={s.statSectionLabel}>Disconnection Stats</div>
          {[
            ['Total Events',       go.total_disconnections,                   go.total_disconnections > 30],
            ['Median Duration',    (go.median_disconnection_sec || '-') + ' s', false],
            ['KSA Total Events',   ksa.total_disconnections,                  false],
            ['KSA Median',         (ksa.median_disconnection_sec || '-') + ' s', false],
          ].map(([k, v, isRed]) => (
            <div key={k} style={s.statRow}>
              <span style={s.statK}>{k}</span>
              <span style={{ ...s.statV, ...(isRed ? { color: '#7A1E1E' } : {}) }}>{v ?? '-'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trend chart */}
      {trendData.length > 1 && (
        <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px' }}>
          <div style={s.chartTitle}>Reliability & Uptime Trend</div>
          <div style={s.chartSub}>GO / FTTH · All loaded dates · %</div>
          <div style={{ height: 300, marginTop: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 4, right: 20, left: -10, bottom: 4 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="rgba(238,232,223,0.08)" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#9A8E7E' }} axisLine={false} tickLine={false} />
                <YAxis domain={['auto', 100]} tick={{ fontSize: 12, fill: '#5A5248' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                <Tooltip contentStyle={{ background: '#EEE8DF', border: '2px solid #1C1813', borderRadius: 4, fontSize: 12 }} formatter={v => [`${v?.toFixed(3)}%`]} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#9A8E7E', paddingTop: 8 }} />
                <Line type="monotone" dataKey="uptime"      stroke="#C8A55A" strokeWidth={2} dot={false} name="Uptime" />
                <Line type="monotone" dataKey="reliability" stroke="#9EBD98" strokeWidth={2} dot={false} name="Reliability" />
                <Line type="monotone" dataKey="dns_v4"      stroke="#C2B8DC" strokeWidth={1.5} dot={false} name="DNS v4" strokeDasharray="4 2" />
                <Line type="monotone" dataKey="dns_v6"      stroke="#E09898" strokeWidth={1.5} dot={false} name="DNS v6" strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* DNS detail */}
      {dns && (
        <div style={s.twoCol}>
          {[4, 6].map(ver => {
            const d = dns[`v${ver}`]
            if (!d) return null
            return (
              <div key={ver} style={{ ...s.card, background: ver === 4 ? '#C2B8DC' : '#E09898', padding: '20px 22px' }}>
                <div style={s.statSectionLabel}>DNS v{ver}, Nameserver Breakdown</div>
                <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 14, opacity: 0.6, textTransform: 'uppercase', letterSpacing: '1px' }}>Dead Resolver Share</div>
                    <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 28, fontWeight: 700, color: d.dead_share_pct > 10 ? '#7A1E1E' : '#1C1813' }}>{d.dead_share_pct}%</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 14, opacity: 0.6, textTransform: 'uppercase', letterSpacing: '1px' }}>Total Nameservers</div>
                    <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 28, fontWeight: 700, color: '#1C1813' }}>{d.nameservers.length}</div>
                  </div>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead><tr style={{ borderBottom: '2px solid rgba(28,24,19,0.3)' }}>
                    {['Nameserver','Reliability','Avg RTT','Status'].map(h => (
                      <th key={h} style={{ padding: '4px 6px', textAlign: h==='Nameserver'?'left':'right', fontSize: 12, letterSpacing:'1px', textTransform:'uppercase', opacity:0.5 }}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {d.nameservers.slice(0, 8).map((ns, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(28,24,19,0.1)' }}>
                        <td style={{ padding: '5px 6px', fontSize: 13, fontFamily: 'Athene Voyage' }}>{ns.nameserver}</td>
                        <td style={{ padding: '5px 6px', fontSize: 13, textAlign: 'right', color: ns.reliability < 50 ? '#7A1E1E' : ns.reliability < 90 ? '#6B4A00' : '#1A4E28', fontWeight: 600 }}>{ns.reliability?.toFixed(1)}%</td>
                        <td style={{ padding: '5px 6px', fontSize: 13, textAlign: 'right', color: '#1C1813', opacity: 0.7 }}>{ns.rtt_avg_ms?.toFixed(1) ?? '-'} ms</td>
                        <td style={{ padding: '5px 6px', fontSize: 13, textAlign: 'right' }}>
                          <span style={{ fontSize: 12, fontWeight: 600, padding: '2px 6px', borderRadius: 2, background: ns.is_dead ? 'rgba(122,30,30,0.15)' : 'rgba(26,78,40,0.15)', color: ns.is_dead ? '#7A1E1E' : '#1A4E28' }}>
                            {ns.is_dead ? 'DEAD' : 'OK'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {d.top_failing_hosts.length > 0 && (
                  <>
                    <div style={{ fontSize: 14, textTransform: 'uppercase', letterSpacing: '1px', opacity: 0.5, margin: '14px 0 6px' }}>Top Failing Lookup Hosts</div>
                    {d.top_failing_hosts.slice(0,5).map((h, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(28,24,19,0.1)', fontSize: 11 }}>
                        <span style={{ fontFamily: 'Athene Voyage', fontSize: 14 }}>{h.host}</span>
                        <span style={{ color: '#7A1E1E', fontWeight: 600 }}>{h.fail_rate}% fail</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Disconnection heatmap */}
      <div style={{ ...s.card, background: '#E8DFD0', padding: '22px 24px' }}>
        <div style={s.statSectionLabel}>Disconnection Heatmap</div>
        <HeatmapPanel title="Minutes per Unit" hourlyData={heatmaps.disc} valueKey="disconnection_minutes" colorScheme="disc" />
      </div>

    </div>
  )
}

function CategorySection({ title, metrics }) {
  return (
    <div style={s.body}>
      <div style={{ ...s.card, background: '#C2B8DC', padding: '24px' }}>
        <div style={s.statSectionLabel}>{title}</div>
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 48, fontWeight: 700, letterSpacing: '-2px', color: '#1C1813', lineHeight: 1, marginTop: 8 }}>
          {metrics?.reliability_pct?.toFixed(4) ?? '-'}<span style={{ fontSize: 18, fontWeight: 400 }}>%</span>
        </div>
        <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, marginTop: 8 }}>
          Total tests: {metrics?.total_tests?.toLocaleString() ?? '-'}
        </div>
      </div>
    </div>
  )
}

function StrategicSection({ comparison, goDaily }) {
  const recs = [
    { priority: 'P1', title: 'Expand Gaming Peering', body: 'Establish direct peering with Valve, Blizzard, and Tencent to reduce hop count for high-latency titles.', color: '#E09898' },
    { priority: 'P2', title: 'Optimize Transit Routing', body: 'Review BGP routes for Cisco Webex and Zoom IP ranges. Match Google Meet routing performance.', color: '#D4B040' },
    { priority: 'P3', title: 'Enhance Local Caching', body: 'Deploy cache nodes to replicate Facebook/Instagram CDN success across other high-traffic platforms.', color: '#C2B8DC' },
    { priority: 'P4', title: 'DNS Resolver Remediation', body: 'Investigate dead DNS resolvers - v6 reliability requires urgent attention below 70%.', color: '#E09898' },
    { priority: 'OG', title: 'SLA Monitoring Pipeline', body: 'Implement continuous active monitoring for top latency-sensitive apps to detect routing shifts proactively.', color: '#9EBD98' },
  ]
  return (
    <div style={s.body}>
      <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px', marginBottom: 14 }}>
        <div style={s.chartTitle}>Auto-Generated Insights</div>
        <div style={{ fontSize: 10, color: '#7A7060', fontStyle: 'italic', marginBottom: 20 }}>Based on current dataset</div>
        <InsightsPanel comparisonData={comparison} dailyData={goDaily} />
      </div>
      <div style={{ ...s.card, background: '#EEE8DF', padding: '22px 24px' }}>
        <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 20 }}>Strategic Action Plan</div>
        {recs.map(r => (
          <div key={r.priority} style={{ ...s.recItem, borderLeft: `3px solid ${r.color}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <span style={{ ...s.priorityBadge, background: r.color }}>{r.priority}</span>
              <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 600, color: '#1C1813' }}>{r.title}</span>
            </div>
            <div style={{ fontSize: 12, color: '#7A7060', lineHeight: 1.5 }}>{r.body}</div>
          </div>
        ))}
      </div>
    </div>
  )
}


/* ── GAMING SECTION ── */
function GamingSection({ metrics, breakdown, selectedDate }) {
  const games = breakdown?.games || []
  const providers = breakdown?.providers || []

  // Sort by latency (highest first) for the chart
  const top10highest = [...games]
    .sort((a, b) => (b.rtt_avg_ms || 0) - (a.rtt_avg_ms || 0))
    .slice(0, 10)
    .reverse() // Reverse to show lowest at top for better readability

  // For the table, sort by latency (lowest first)
  const sortedGames = [...games].sort((a, b) => (a.rtt_avg_ms || 0) - (b.rtt_avg_ms || 0))

  return (
    <div style={s.body}>

      {/* Header KPIs */}
      <div style={s.threeCol}>
        <div style={{ ...s.card, background: '#D4B040', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Overall Reliability</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {metrics?.reliability_pct?.toFixed(3) ?? '-'}<span style={{ fontSize: 16 }}>%</span>
          </div>
          <div style={{ fontSize: 15, color: '#1C1813', opacity: 0.6, marginTop: 6 }}>
            {metrics?.total_tests?.toLocaleString() ?? '-'} total tests
          </div>
        </div>
        <div style={{ ...s.card, background: '#C2B8DC', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Avg Latency (All Titles)</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {games.length > 0 ? (games.reduce((a,g) => a + (g.rtt_avg_ms||0), 0) / games.length).toFixed(1) : '-'}
            <span style={{ fontSize: 16 }}> ms</span>
          </div>
          <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, marginTop: 6 }}>across {games.length} titles</div>
        </div>
        <div style={{ ...s.card, background: '#9EBD98', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Best Latency Title</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 28, fontWeight: 700, color: '#1C1813', marginTop: 4 }}>
            {sortedGames[0]?.app_name ?? '-'}
          </div>
          <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, marginTop: 6 }}>
            {sortedGames[0]?.rtt_avg_ms ?? '-'} ms avg
          </div>
        </div>
      </div>

      {/* Latency bar chart - top 10 highest latency titles */}
      {top10highest.length > 0 && (
        <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px' }}>
          <div style={s.chartTitle}>Latency by Title - Top 10 Highest</div>
          <div style={s.chartSub}>GO / FTTH · {selectedDate} · Lower Is Better</div>
          <div style={{ height: 350, marginTop: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={top10highest} 
                layout="vertical" 
                margin={{ left: 100, right: 20, top: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="2 2" stroke="rgba(238,232,223,0.08)" horizontal={false} />
                <XAxis 
                  type="number" 
                  tick={{ fontSize: 13, fill: '#9A8E7E' }} 
                  axisLine={false} 
                  tickLine={false} 
                  tickFormatter={v => `${v}ms`}
                />
                <YAxis 
                  type="category" 
                  dataKey="app_name" 
                  tick={{ fontSize: 15, fill: '#9A8E7E' }} 
                  axisLine={false} 
                  tickLine={false} 
                  width={95}
                />
                <Tooltip
                  contentStyle={{ background: '#EEE8DF', border: '2px solid #1C1813', borderRadius: 4, fontSize: 11 }}
                  formatter={(v) => [`${v} ms`, 'Avg Latency']}
                  labelFormatter={(label) => `Game: ${label}`}
                />
                <Bar 
                  dataKey="rtt_avg_ms" 
                  fill="#C8A55A" 
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Full per-game table */}
      <div style={{ ...s.card, background: '#EEE8DF', padding: '22px 24px' }}>
        <div style={{ ...s.chartTitle, color: '#1C1813' }}>All Titles - Detailed Data</div>
        <div style={{ fontSize: 12, color: '#9A9088', fontStyle: 'italic', marginBottom: 16 }}>
          Sorted by latency (lowest to highest) · Lower latency = better · RTT in ms
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #1C1813' }}>
                {['Title', 'Avg RTT', 'Min', 'Max', 'Reliability', 'Tests', 'Hops'].map(h => (
                  <th key={h} style={{ 
                    padding: '8px 12px', 
                    textAlign: h === 'Title' ? 'left' : 'right', 
                    fontSize: 17, 
                    letterSpacing: '1.5px',  
                    color: '#7A7060', 
                    fontWeight: 600 
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedGames.map((g, i) => (
                <tr key={g.app_key} style={{ 
                  borderBottom: '1px solid rgba(28,24,19,0.1)', 
                  background: i % 2 === 0 ? 'transparent' : 'rgba(28,24,19,0.03)' 
                }}>
                  <td style={{ padding: '8px 12px', fontWeight: 500, color: '#1C1813' }}>{g.app_name}</td>
                  <td style={{ 
                    padding: '8px 12px', 
                    textAlign: 'right', 
                    fontFamily: "'Athene Voyage',serif", 
                    fontWeight: 700, 
                    color: (g.rtt_avg_ms || 0) > 100 ? '#7A1E1E' : (g.rtt_avg_ms || 0) > 60 ? '#be9f41' : '#1A4E28' 
                  }}>
                    {g.rtt_avg_ms?.toFixed(2) ?? '-'}
                  </td>
                  <td style={{ padding: '12px 12px', textAlign: 'right', color: '#1A4E28' }}>{g.rtt_min_ms?.toFixed(1) ?? '-'}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#7A1E1E' }}>{g.rtt_max_ms?.toFixed(1) ?? '-'}</td>
                  <td style={{ 
                    padding: '8px 12px', 
                    textAlign: 'right', 
                    color: (g.reliability ?? 100) < 98 ? '#7A1E1E' : (g.reliability ?? 100) < 99.5 ? '#be9f41' : '#1A4E28', 
                    fontWeight: 600 
                  }}>
                    {g.reliability?.toFixed(2) ?? '-'}%
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#7A7060' }}>{g.total_tests?.toLocaleString()}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#7A7060' }}>{g.avg_hops?.toFixed(1) ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provider/datacenter breakdown */}
      {providers.length > 0 && (
        <div style={{ ...s.card, background: '#9EBD98', padding: '22px 24px' }}>
          <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 4 }}>Server Infrastructure</div>
          <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, marginBottom: 16 }}>
            Provider · Datacenter · Region - sorted by latency (lowest to highest)
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(28,24,19,0.3)' }}>
                  {['Provider', 'Data Center', 'Region', 'Avg RTT', 'Success Rate'].map(h => (
                    <th key={h} style={{ 
                      padding: '8px 12px', 
                      textAlign: h === 'Provider' ? 'left' : 'right', 
                      fontSize: 17, 
                      letterSpacing: '1.5px', 
                      color: '#1C1813', 
                      opacity: 0.6, 
                      fontWeight: 600 
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...providers]
                  .sort((a, b) => (a.rtt_avg_ms || 0) - (b.rtt_avg_ms || 0))
                  .map((p, i) => {
                    const total = p.successes + p.failures
                    const rel = total > 0 ? (p.successes / total * 100).toFixed(3) : '-'
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(28,24,19,0.1)' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 500, fontSize: 15 }}>{p.provider || '-'}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: '#7A7060', fontSize: 15 }}>{p.datacenter || '-'}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: '#7A7060', fontSize: 15 }}>{p.region || '-'}</td>
                        <td style={{ 
                          padding: '8px 12px', 
                          textAlign: 'right', 
                          fontFamily: "'Athene Voyage',serif", 
                          fontWeight: 700,
                          fontSize: 15,
                          color: (p.rtt_avg_ms || 0) > 80 ? '#7A1E1E' : '#1C1813'
                        }}>
                          {p.rtt_avg_ms?.toFixed(2) ?? '-'} ms
                        </td>
                        <td style={{ 
                          padding: '8px 12px', 
                          textAlign: 'right', 
                          color: parseFloat(rel) < 98 ? '#7A1E1E' : '#1A4E28',
                          fontWeight: 600
                        }}>
                          {rel}%
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}


/* ── SOCIAL SECTION ── */
/* ── SOCIAL SECTION ── */
function SocialSection({ metrics, breakdown, selectedDate }) {
  const services = breakdown?.services || []
  
  // Filter out null/empty services and clean up names
  const cleanServices = services.filter(s => s.service && s.service !== 'null' && s.service.trim() !== '')
  
  const cdnServices   = cleanServices.filter(s => s.is_cdn)
  const nonCdnServices = cleanServices.filter(s => !s.is_cdn)

  const byService = {}
  cleanServices.forEach(s => {
    if (!byService[s.service]) byService[s.service] = []
    byService[s.service].push(s)
  })

  const serviceAvgs = Object.entries(byService)
    .map(([name, rows]) => ({
      service: name,
      rtt_avg_ms: rows.reduce((a,r) => a + (r.rtt_avg_ms||0), 0) / rows.length,
      reliability: rows.reduce((a,r) => a + (r.reliability||0), 0) / rows.length,
      total_tests: rows.reduce((a,r) => a + r.total_tests, 0),
    }))
    .sort((a,b) => a.rtt_avg_ms - b.rtt_avg_ms)
    .filter(item => item.service && item.service !== 'null') // Extra filter for safety

  const cdnAvg = cdnServices.length > 0
    ? cdnServices.reduce((a,s) => a + (s.rtt_avg_ms||0), 0) / cdnServices.length
    : null
  const nonCdnAvg = nonCdnServices.length > 0
    ? nonCdnServices.reduce((a,s) => a + (s.rtt_avg_ms||0), 0) / nonCdnServices.length
    : null

  // Helper function to format service names with dashes
  const formatServiceName = (name) => {
    if (!name) return 'Unknown'
    // Handle Snapchat Edge specifically
    if (name.toLowerCase().includes('snapchat') && name.toLowerCase().includes('edge')) {
      return ['Snapchat', 'Edge']
    }
    // Handle any name with a dash
    if (name.includes('-')) {
      const parts = name.split('-')
      if (parts.length === 2) {
        return [parts[0], parts[1]]
      }
      return [name]
    }
    return [name]
  }

  return (
    <div style={s.body}>

      {/* Header KPIs */}
      <div style={s.threeCol}>
        <div style={{ ...s.card, background: '#D4B040', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Overall Reliability</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {metrics?.reliability_pct?.toFixed(3) ?? '-'}<span style={{ fontSize: 16 }}>%</span>
          </div>
          <div style={{ fontSize: 15, opacity: 0.6, marginTop: 6 }}>{metrics?.total_tests?.toLocaleString() ?? '-'} tests</div>
        </div>
        <div style={{ ...s.card, background: '#9EBD98', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>CDN Avg Latency</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {cdnAvg?.toFixed(4) ?? '-'}<span style={{ fontSize: 16 }}> ms</span>
          </div>
          <div style={{ fontSize: 15, opacity: 0.6, marginTop: 6 }}>{cdnServices.length} CDN endpoints</div>
        </div>
        <div style={{ ...s.card, background: '#E09898', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Non-CDN Avg Latency</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {nonCdnAvg?.toFixed(4) ?? '-'}<span style={{ fontSize: 16 }}> ms</span>
          </div>
          <div style={{ fontSize: 15, opacity: 0.6, marginTop: 6 }}>{nonCdnServices.length} standard endpoints</div>
        </div>
      </div>

      {/* Per-service latency chart */}
      {serviceAvgs.length > 0 && (
        <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px' }}>
          <div style={s.chartTitle}>Latency by Platform</div>
          <div style={s.chartSub}>GO / FTTH · {selectedDate} · Avg across all endpoints per service</div>
          <div style={{ height: Math.max(320, serviceAvgs.length * 35), marginTop: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={serviceAvgs} 
                layout="vertical" 
                margin={{ 
                  left: 10, 
                  right: 30, 
                  top: 10, 
                  bottom: 10 
                }}
              >
                <CartesianGrid strokeDasharray="2 2" stroke="rgba(238,232,223,0.08)" vertical={false} />
                <XAxis 
                  type="number" 
                  tick={{ fontSize: 13, fill: '#9A8E7E' }} 
                  axisLine={false} 
                  tickLine={false} 
                  tickFormatter={v => `${v}ms`}
                />
                <YAxis 
                  type="category" 
                  dataKey="service" 
                  tick={(props) => {
                    const { x, y, payload } = props;
                    const serviceName = payload.value;
                    const formattedName = formatServiceName(serviceName);
                    
                    if (formattedName.length === 2) {
                      // Two-line label
                      return (
                        <g transform={`translate(${x - 8}, ${y})`}>
                          <text 
                            textAnchor="end" 
                            fill="#9A8E7E" 
                            fontSize={15}
                            fontWeight={500}
                            dy={-6}
                            style={{ fontFamily: "'Athene Voyage', sans-serif" }}
                          >
                            {formattedName[0]}
                          </text>
                          <text 
                            textAnchor="end" 
                            fill="#9A8E7E" 
                            fontSize={15}
                            fontWeight={100}
                            dy={6}
                            style={{ fontFamily: "'Athene Voyage', sans-serif" }}
                          >
                            ({formattedName[1]})
                          </text>
                        </g>
                      );
                    }
                    
                    return (
                      <text 
                        x={x - 8} 
                        y={y} 
                        dy={4} 
                        textAnchor="end" 
                        fill="#9A8E7E" 
                        fontSize={15}
                        fontWeight={500}
                        style={{ fontFamily: "'Athene Voyage', sans-serif" }}
                      >
                        {formattedName[0]}
                      </text>
                    );
                  }}
                  axisLine={false} 
                  tickLine={false} 
                  width={105}
                />
                <Tooltip
                  contentStyle={{ background: '#EEE8DF', border: '2px solid #1C1813', borderRadius: 4, fontSize: 12 }}
                  formatter={(v) => [`${v?.toFixed(3)} ms`, 'Avg Latency']}
                  labelFormatter={(label) => `Platform: ${label}`}
                />
                <Bar 
                  dataKey="rtt_avg_ms" 
                  fill="#C8A55A" 
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

{/* CDN vs Non-CDN endpoint table */}
<div style={s.twoCol}>
  <div style={{ ...s.card, background: '#9EBD98', padding: '20px 22px' }}>
    <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 4 }}>CDN Optimised Endpoints</div>
    <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, fontStyle: 'italic', marginBottom: 14 }}>
      Local / edge-cached - fast
    </div>
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid rgba(28,24,19,0.3)' }}>
            {['Target', 'RTT', 'Reliability'].map(h => (
              <th key={h} style={{ 
                padding: '6px 10px', 
                textAlign: h === 'Target' ? 'left' : 'right', 
                fontSize: 17, 
                letterSpacing: '1.5px', 
                color: '#1C1813', 
                opacity: 0.5 
              }}>
                {h}
              </th>
            ))}
           </tr>
        </thead>
        <tbody>
          {cdnServices.map((sv,i) => {
            const displayName = sv.target || sv.service
            
            // Check if it's a hyphenated name (like "Snapchat-Edge") vs a domain name (has dots)
            const isHyphenated = displayName.includes('-') && !displayName.includes('.')
            
            let formattedDisplay
            if (isHyphenated) {
              // For hyphenated names like "Snapchat-Edge" - split at dash and display on two lines
              const parts = displayName.split('-')
              formattedDisplay = (
                <div>
                  <div>{parts[0]}</div>
                  <div style={{ fontSize: 12, opacity: 0.8 }}>({parts[1]})</div>
                </div>
              )
            } else {
              // For everything else (domains, single words) - display as is
              formattedDisplay = displayName
            }
            
            return (
              <tr key={i} style={{ borderBottom: '1px solid rgba(28,24,19,0.1)' }}>
                <td style={{ 
                  padding: '6px 10px', 
                  fontSize: 15,
                  whiteSpace: 'normal',
                  wordBreak: 'keep-all',
                  maxWidth: '200px',
                  lineHeight: '1.3'
                }}>
                  {formattedDisplay}
                </td>
                <td style={{ 
                  padding: '6px 10px', 
                  fontSize: 15,
                  textAlign: 'right', 
                  fontFamily: "'Athene Voyage',serif", 
                  fontWeight: 700, 
                  color: '#1A4E28' 
                }}>
                  {sv.rtt_avg_ms?.toFixed(2) ?? '-'} ms
                </td>
                <td style={{ 
                  padding: '6px 10px', 
                  fontSize: 15,
                  textAlign: 'right', 
                  color: (sv.reliability??100) < 99 ? '#7A1E1E' : '#1A4E28' 
                }}>
                  {sv.reliability?.toFixed(2) ?? '-'}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  </div>

  <div style={{ ...s.card, background: '#E09898', padding: '20px 22px' }}>
    <div style={{ ...s.chartTitle, color: '#1C1813'}}>Standard Routing Endpoints</div>
    <div style={{ fontSize: 12, color: '#1C1813', opacity: 0.6, fontStyle: 'italic', marginBottom: 14 }}>
      Global / Non-CDN - higher latency expected
    </div>
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid rgba(28,24,19,0.3)' }}>
            {['Target', 'RTT', 'Reliability'].map(h => (
              <th key={h} style={{ 
                padding: '6px 10px', 
                textAlign: h === 'Target' ? 'left' : 'right', 
                fontSize: 17, 
                letterSpacing: '1.5px', 
                color: '#1C1813', 
                opacity: 0.5 
              }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {nonCdnServices.map((sv,i) => {
            const displayName = sv.target || sv.service
            
            // Check if it's a hyphenated name (like "Snapchat-Edge") vs a domain name (has dots)
            const isHyphenated = displayName.includes('-') && !displayName.includes('.')
            
            let formattedDisplay
            if (isHyphenated) {
              // For hyphenated names like "Snapchat-Edge" - split at dash and display on two lines
              const parts = displayName.split('-')
              formattedDisplay = (
                <div>
                  <div>{parts[0]}</div>
                  <div style={{ fontSize: 12, opacity: 0.8 }}>({parts[1]})</div>
                </div>
              )
            } else {
              // For everything else (domains, single words) - display as is
              formattedDisplay = displayName
            }
            
            return (
              <tr key={i} style={{ borderBottom: '1px solid rgba(28,24,19,0.1)' }}>
                <td style={{ 
                  padding: '6px 10px', 
                  fontSize: 15,
                  whiteSpace: 'normal',
                  wordBreak: 'keep-all',
                  maxWidth: '200px',
                  lineHeight: '1.3'
                }}>
                  {formattedDisplay}
                </td>
                <td style={{ 
                  padding: '6px 10px', 
                  textAlign: 'right', 
                  fontFamily: "'Athene Voyage',serif", 
                  fontSize: 15,
                  fontWeight: 700 
                }}>
                  {sv.rtt_avg_ms?.toFixed(2) ?? '-'} ms
                </td>
                <td style={{ 
                  padding: '6px 10px', 
                  fontSize: 15,
                  textAlign: 'right', 
                  color: (sv.reliability??100) < 99 ? '#7A1E1E' : '#1A4E28' 
                }}>
                  {sv.reliability?.toFixed(2) ?? '-'}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  </div>
</div>

    </div>
  )
}


/* ── VIDEO SECTION ── */
function VideoSection({ metrics, breakdown, selectedDate }) {
  const platforms = breakdown?.platforms || []

  const byService = {}
  platforms.forEach(p => {
    if (!byService[p.service]) byService[p.service] = { service: p.service, rtts: [], successes: 0, failures: 0 }
    if (p.rtt_avg_ms) byService[p.service].rtts.push(p.rtt_avg_ms)
    byService[p.service].successes += p.successes
    byService[p.service].failures  += p.failures
  })

  const serviceAvgs = Object.values(byService).map(sv => ({
    service: sv.service,
    rtt_avg_ms: sv.rtts.length > 0 ? sv.rtts.reduce((a,b) => a+b, 0) / sv.rtts.length : null,
    reliability: (sv.successes + sv.failures) > 0 ? sv.successes / (sv.successes + sv.failures) * 100 : null,
  })).sort((a,b) => (a.rtt_avg_ms||9999) - (b.rtt_avg_ms||9999))

  const best = serviceAvgs[0]
  const worst = serviceAvgs[serviceAvgs.length - 1]

  return (
    <div style={s.body}>

      {/* Header KPIs */}
      <div style={s.threeCol}>
        <div style={{ ...s.card, background: '#C2B8DC', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Overall Reliability</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, letterSpacing: '-1px', color: '#1C1813' }}>
            {metrics?.reliability_pct?.toFixed(3) ?? '-'}<span style={{ fontSize: 16 }}>%</span>
          </div>
          <div style={{ fontSize: 15, opacity: 0.6, marginTop: 6 }}>{metrics?.total_tests?.toLocaleString() ?? '-'} tests</div>
        </div>
        <div style={{ ...s.card, background: '#9EBD98', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Best Platform</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, color: '#1C1813', marginTop: 4 }}>{best?.service ?? '-'}</div>
          <div style={{ fontSize: 15, color: '#1A4E28', marginTop: 6, fontWeight: 600 }}>{best?.rtt_avg_ms?.toFixed(3) ?? '-'} ms avg</div>
        </div>
        <div style={{ ...s.card, background: '#E09898', padding: '20px 22px' }}>
          <div style={s.statSectionLabel}>Needs Optimisation</div>
          <div style={{ fontFamily: "'Athene Voyage',serif", fontSize: 42, fontWeight: 700, color: '#1C1813', marginTop: 4 }}>{worst?.service ?? '-'}</div>
          <div style={{ fontSize: 15, color: '#7A1E1E', marginTop: 6, fontWeight: 600 }}>{worst?.rtt_avg_ms?.toFixed(3) ?? '-'} ms avg</div>
        </div>
      </div>

      {/* Platform comparison bar chart */}
      <div style={{ ...s.card, ...s.inkCard, padding: '22px 24px' }}>
        <div style={s.chartTitle}>Latency by Platform</div>
        <div style={s.chartSub}>GO / FTTH · {selectedDate} · Lower Is Better</div>
        <div style={{ height: 220, marginTop: 16 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={serviceAvgs} margin={{ top: 4, right: 20, left: 5, bottom: 4 }} barSize={36}>
              <CartesianGrid strokeDasharray="2 2" stroke="rgba(238,232,223,0.08)" vertical={false} />
              <XAxis dataKey="service" tick={{ fontSize: 15, fill: '#9A8E7E' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 13, fill: '#5A5248' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}ms`} />
              <Tooltip contentStyle={{ background: '#EEE8DF', border: '2px solid #1C1813', borderRadius: 4, fontSize: 11 }} formatter={v => [`${v?.toFixed(3)} ms`, 'Avg Latency']} />
              <Bar dataKey="rtt_avg_ms" radius={[2,2,0,0]}
                fill="#C8A55A"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Full endpoint table */}
      <div style={{ ...s.card, background: '#EEE8DF', padding: '22px 24px' }}>
        <div style={{ ...s.chartTitle, color: '#1C1813', marginBottom: 4 }}>All Endpoints - Detailed Data</div>
        <div style={{ fontSize: 11, color: '#9A9088', fontStyle: 'italic', marginBottom: 16 }}>Sorted by latency · RTT in ms</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #1C1813' }}>
              {['Platform','Region','Avg RTT','Median RTT','Best','Worst','Reliability','Tests'].map(h => (
                <th key={h} style={{ padding: '6px 10px', textAlign: h==='Platform'||h==='Region'?'left':'right', fontSize: 17, letterSpacing:'1.5px', color:'#7A7060', fontWeight:500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {platforms.map((p, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(28,24,19,0.1)', background: i%2===0?'transparent':'rgba(28,24,19,0.03)' }}>
                <td style={{ padding: '7px 10px', fontWeight: 500, fontSize: 15 }}>{p.service}</td>
                <td style={{ padding: '7px 10px', color: '#7A7060', fontSize: 15 }}>{p.region || '-'}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, fontFamily: "'Athene Voyage',serif", fontWeight: 700, color: (p.rtt_avg_ms||0) > 120 ? '#7A1E1E' : '#1C1813' }}>{p.rtt_avg_ms ?? '-'}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, color: '#7A7060' }}>{p.rtt_median_ms ?? '-'}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, color: '#1A4E28' }}>{p.rtt_best_ms ?? '-'}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, color: '#7A1E1E' }}>{p.rtt_worst_ms ?? '-'}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, color: (p.reliability??100) < 99 ? '#7A1E1E' : '#1A4E28', fontWeight: 600 }}>{p.reliability?.toFixed(2) ?? '-'}%</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontSize: 15, color: '#7A7060' }}>{p.total_tests?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  )
}

/* ── STYLES ── */
const s = {
  page: { display: 'flex', flexDirection: 'column', minHeight: '100vh', background: '#EEE8DF' },

  topbar: {
  background: '#EEE8DF',
  border: '3.5px solid black',
  padding: '5px 30px',
  margin: '0 16px',
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  transition: 'padding 0.3s ease, box-shadow 0.3s ease',
},
  topbarTitle: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 26,
    padding: '0px 5px', borderRadius: 2,
  },
  topbarRight: { display: 'flex', alignItems: 'center', gap: 10 },
  dateSelect: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 15, fontWeight: 500,
    background: '#1C1813', color: '#EEE8DF',
    border: '2px solid #1C1813',
    padding: '7px 11px', borderRadius: 15, cursor: 'pointer',
  },
  rangePanelTop: { display: 'flex', gap: 6, marginRight: 10 },
  rangeToggleActive: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 14, fontWeight: 700,
    color: '#EEE8DF', background: '#1C1813', border: '2px solid #1C1813', borderRadius: 14,
    padding: '6px 14px', cursor: 'pointer'
  },
  rangeToggleInactive: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 14, fontWeight: 600,
    color: '#1C1813', background: 'transparent', border: '2px solid #1C1813', borderRadius: 14,
    padding: '6px 14px', cursor: 'pointer'
  },
  rangeInputRow: { display: 'flex', alignItems: 'center', gap: 10, marginTop: 20 },
  rangePresetPanel: { display: 'flex', flexDirection: 'column', gap: 10 },
  presetButtons: { display: 'flex', gap: 6 },
  presetButton: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 13, fontWeight: 600,
    color: '#1C1813', background: 'transparent', border: '2px solid #1C1813', borderRadius: 14,
    padding: '5px 12px', cursor: 'pointer'
  },
  presetButtonActive: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 13, fontWeight: 700,
    color: '#EEE8DF', background: '#1C1813', border: '2px solid #1C1813', borderRadius: 14,
    padding: '5px 12px', cursor: 'pointer'
  },
  selectedPresetDisplay: { display: 'flex', alignItems: 'center', gap: 10 },
  changePresetButton: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 13, fontWeight: 600,
    color: '#1C1813', background: 'transparent', border: '1px solid #1C1813', borderRadius: 10,
    padding: '4px 8px', cursor: 'pointer'
  },
  rangeBadge: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 13, fontWeight: 700,
    color: '#1C1813', background: '#F4F1E8', border: '1px solid #1C1813', borderRadius: 14,
    padding: '6px 12px', marginRight: 10,
  },
  rangePopup: {
    position: 'fixed',
    top: 80,
    right: 24,
    width: 420,
    maxWidth: 'calc(100vw - 40px)',
    background: '#FFF',
    border: '2px solid #1C1813',
    borderRadius: 24,
    boxShadow: '0 22px 40px rgba(0,0,0,0.14)',
    padding: 20,
    zIndex: 210,
    pointerEvents: 'auto',
  },
  presetHeader: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 18,
    color: '#1C1813',
    marginBottom: 12,
  },
  popupActions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 18,
  },

  rangeSeparator: { color: '#1C1813', fontSize: 15, fontWeight: 700 },
  applyButton: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 14, fontWeight: 700,
    color: '#EEE8DF', background: '#1C1813', border: '2px solid #1C1813', borderRadius: 14,
    padding: '7px 14px', cursor: 'pointer'
  },
  rangeSummaryBox: {
    background: '#FFF7D6', border: '1px solid #DDC77A', borderRadius: 18,
    padding: '16px 20px', marginBottom: 18,
  },
  rangeSummaryTitle: { color: '#4C3C1A', fontSize: 14, letterSpacing: '0.1em', marginBottom: 6 },
  rangeSummaryText: { fontSize: 16, color: '#1C1813' },
  rangeError: { color: '#7A1E1E', fontSize: 13, marginTop: 6 },
  rangeProgress: { fontSize: 13, color: '#1C1813', marginTop: 8, padding: '4px 10px', background: '#F4F1E8', borderRadius: 12 },
  scopeBadge: {
    fontSize: 15, fontWeight: 500,
    border: '2px solid #1C1813',
    padding: '4px 11px', borderRadius: 15,
  },
  uptimeBadge: { fontSize: 18 },

  content: { flex: 1 },

  body: { padding: '28px 30px 36px', display: 'flex', flexDirection: 'column', gap: 14 },

  greetH: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 80,
    lineHeight: 1.0, letterSpacing: '-2px', color: '#1C1813',
  },
  greetCap: {
    fontSize: 18, color: '#1C1813',
    fontWeight: 300
  },

  threeCol: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 13 },
  twoCol:   { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 13 },

  card: { border: '2px solid #1C1813', borderRadius: 20 },
  inkCard: { background: '#1C1813' },

  chartTitle: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 25, fontWeight: 700,
    color: '#EEE8DF', lineHeight: 1.2,
  },
  chartSub: { fontSize: 10, color: '#deae61', marginTop: 3, letterSpacing: '0.4px' },
  chartPull: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 30, fontWeight: 700, fontStyle: 'italic', color: '#C8A55A', lineHeight: 1,
  },

  statSectionLabel: {
    fontSize: 25, fontWeight: 500,
    color: 'rgb(28, 24, 19)', marginBottom: 12,
  },
  statRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
    padding: '7px 0', borderBottom: '1px solid rgba(26,23,18,0.15)',
  },
  statK: { fontSize: 17, color: '#1C1813', opacity: 0.65 },
  statV: { fontFamily: "'Athene Voyage', serif", fontSize: 18, fontWeight: 700, color: '#1C1813' },

  recItem: {
    background: '#f7f8f0', padding: '12px 14px',
    borderRadius: '0 4px 4px 0', marginBottom: 10,
  },
  priorityBadge: {
    fontSize: 9, fontWeight: 700, color: '#1C1813',
    padding: '2px 7px', borderRadius: 3, letterSpacing: '0.5px',
  },

  loadScreen: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    height: '100vh', gap: 12, background: '#EEE8DF',
  },
  loadSpinner: {
    width: 24, height: 24, borderRadius: '50%',
    border: '2px solid #C8C0B4', borderTopColor: '#1C1813',
    animation: 'spin 0.7s linear infinite',
  },
  loadText: { fontSize: 13, color: '#7A7060', fontFamily: "'Playfair Display', serif", fontStyle: 'italic' },
  loadSub: { fontSize: 11, color: '#9A9088' },
}