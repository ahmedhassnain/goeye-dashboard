import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import LoginPage from './pages/Login'

export default function App() {
  const [section, setSection] = useState('overview')
  const [user, setUser]       = useState(null)
  const [navOpen, setNavOpen] = useState(false)  // drawer state on small screens

  useEffect(() => {
    if (!navOpen) return
    const onKey = e => { if (e.key === 'Escape') setNavOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navOpen])

  if (!user) {
    return <LoginPage onLogin={setUser} />
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#EEE8DF' }}>  {/* Set to dashboard background color */}
      <Sidebar
        active={section}
        open={navOpen}
        onClose={() => setNavOpen(false)}
        onNavigate={id => {
          setSection(id)
          setNavOpen(false)
        }}
        user={user}
        onLogout={() => {
          window.__authToken = null
          setUser(null)
        }}
      />
      <div className={`ge-backdrop${navOpen ? ' is-open' : ''}`} onClick={() => setNavOpen(false)} />
      <div className="ge-main" style={{ marginLeft: 188, flex: 1, minWidth: 0 }}>
        <Dashboard section={section} user = {user} onMenu={() => setNavOpen(true)} />
      </div>
    </div>
  )
}
