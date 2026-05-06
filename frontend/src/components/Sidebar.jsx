const NAV = [
  {
    group: 'Analytics',
    items: [
      { id: 'overview',   label: 'Overview' },
      { id: 'benchmark',  label: 'Benchmark' },
    ]
  },
  {
    group: 'Performance',
    items: [
      { id: 'gaming',     label: 'Gaming' },
      { id: 'social',     label: 'Social Media' },
      { id: 'video',      label: 'Video Conf.' },
    ]
  },
  {
    group: 'Network',
    items: [
      { id: 'reliability', label: 'Reliability' },
      { id: 'heatmaps',    label: 'Heatmaps' },
    ]
  },
  {
    group: 'Insights',
    items: [
      { id: 'strategic',  label: 'Recommendations' },
    ]
  },
]

export default function Sidebar({ active, onNavigate, user, onLogout }) {
  return (
    <aside style={s.sidebar}>
      <div style={s.logo}>GoEye</div>

      <nav style={s.nav}>
        {NAV.map(section => (
          <div key={section.group} style={s.group}>
            <div style={s.groupLabel}>{section.group}</div>
            {section.items.map(item => (
              <button
                key={item.id}
                style={{
                  ...s.item,
                  ...(active === item.id ? s.itemActive : {}),
                }}
                onClick={() => onNavigate(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div style={s.foot}>
        {user && (
          <>
            <div style={s.userName}>{user.fullName}</div>
            <div style={s.userRole}>{user.role}</div>
          </>
        )}
        {onLogout && (
          <button style={s.signOut} onClick={onLogout}>Sign Out</button>
        )}
      </div>
    </aside>
  )
}

const s = {
  sidebar: {
    width: 188, minWidth: 188,
    background: '#1C1813',
    display: 'flex', flexDirection: 'column',
    padding: '26px 18px 20px',
    position: 'fixed', top: 0, left: 0, bottom: 0,
    zIndex: 100,
    overflowY: 'auto',
  },
  logo: {
    fontFamily: "'Athene Voyage', serif",
    fontSize: 30, fontWeight: 700,
    color: '#EEE8DF', letterSpacing: '0.3px',
    marginBottom: 38,
  },
  nav: { flex: 1 },
  group: { marginBottom: 22 },
  groupLabel: {
    fontSize: 13, fontWeight: 500,
    color: '#5A5248', letterSpacing: '0.5px',
    marginBottom: 9,
  },
  item: {
    display: 'block', width: '100%',
    fontSize: 15, color: '#8A8078',
    padding: '4px 0 4px 10px', textAlign: 'left',
    borderLeft: '1px solid transparent',
    background: 'none', cursor: 'pointer',
    fontFamily: "'Athene Voyage', sans-serif",
  },
  itemActive: {
    color: '#EEE8DF',
    borderLeft: '2px solid #C8A55A',
    paddingLeft: 9,
    fontWeight: 500,
  },
  foot: {
    paddingTop: 14,
    borderTop: '1px solid #2E2820',
    lineHeight: 1.25,
  },
  userName: { fontSize: 15, color: '#EEE8DF', fontWeight: 500 },
  userRole: { fontSize: 12, color: '#5A5248', textTransform: 'capitalize' },
  signOut: {
    marginTop: 8, fontSize: 12, color: '#b79854',
    cursor: 'pointer', background: 'none', border: 'none',
    fontFamily: "'Athene Voyage', sans-serif", padding: 0,
  },
}