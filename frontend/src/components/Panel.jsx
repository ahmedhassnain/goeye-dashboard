export default function Panel({ title, subtitle, action, children, style }) {
  return (
    <div style={{ ...styles.panel, ...style }}>
      {(title || action) && (
        <div style={styles.header}>
          <div>
            <div style={styles.title}>{title}</div>
            {subtitle && <div style={styles.subtitle}>{subtitle}</div>}
          </div>
          {action && <div style={styles.action}>{action}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  )
}

const styles = {
  panel: {
    background: '#ffffff',
    border: '1px solid #e2e6f0',
    borderRadius: 10,
    padding: '18px 20px',
    boxShadow: '0 1px 3px rgba(15,22,36,0.04)',
  },
  header: {
    display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: '1px solid #f0f2f7',
  },
  title: {
    fontSize: 13.5, fontWeight: 600, color: '#0f1624', letterSpacing: '-0.1px',
  },
  subtitle: {
    fontSize: 11.5, color: '#8892a8', marginTop: 2,
  },
  action: {
    fontSize: 11.5, color: '#2563eb', fontWeight: 500, cursor: 'pointer',
  },
}