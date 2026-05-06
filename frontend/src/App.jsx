import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import LoginPage from './pages/Login'

export default function App() {
  const [section, setSection] = useState('overview')
  const [user, setUser]       = useState(null)

  if (!user) {
    return <LoginPage onLogin={setUser} />
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#EEE8DF' }}>  {/* Set to dashboard background color */}
      <Sidebar
        active={section}
        onNavigate={setSection}
        user={user}
        onLogout={() => {
          window.__authToken = null
          setUser(null)
        }}
      />
      <div style={{ marginLeft: 188, flex: 1, minWidth: 0 }}>
        <Dashboard section={section} user = {user} />
      </div>
    </div>
  )
}