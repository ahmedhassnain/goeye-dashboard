import { useState } from 'react'
import { login } from '../api/client'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async () => {
    if (!username || !password) {
      setError('Please enter both fields.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await login(username, password)
      window.__authToken = data.access_token
      onLogin({ fullName: data.full_name, role: data.role, username })
    } catch {
      setError('Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div style={s.page}>

      {/* ── Left Panel ── */}
      <div style={s.leftPanel}>
        <svg style={s.decorSvg} viewBox="0 0 700 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
          <defs>
            <linearGradient id="arcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor="#F6D709" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#EDCA0F" stopOpacity="0.6" />
            </linearGradient>
          </defs>
          {/* Upper large arc */}
          <circle
            cx="620" cy="-60" r="460"
            fill="none"
            stroke="url(#arcGrad)"
            strokeWidth="150"
            opacity="0.78"
          />
          {/* Lower smaller arc */}
          <circle
            cx="640" cy="860" r="300"
            fill="none"
            stroke="url(#arcGrad)"
            strokeWidth="130"
            opacity="0.78"
          />
        </svg>

        <div style={s.leftTop}>
          <div style={s.brandName}>GoEye</div>
        </div>

        <div style={s.leftBottom}>
          <div style={s.brandSub}>
            One-Stop Dashboard<br />
            for all Go Telecom Data.
          </div>
        </div>
      </div>

      {/* ── Right Panel ── */}
      <div style={s.rightPanel}>
        <div style={s.cardWrapper}>
          {/* Shadow card – sits behind, offset down-left */}
          <div style={s.cardBack} />

          {/* Front card */}
          <div style={s.cardFront}>
            <div style={s.welcomeText}>Welcome Back</div>
            <div style={s.subText}>
              Please proceed to login with your credentials.
            </div>
            <div style={s.divider} />

            <div style={s.field}>
              <label style={s.label}>Your Email</label>
              <input
                style={s.input}
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                onKeyDown={handleKeyDown}
                autoFocus
              />
            </div>

            <div style={s.field}>
              <label style={s.label}>Password</label>
              <input
                style={s.input}
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>

            {error && <div style={s.error}>{error}</div>}

            <button
              style={{ ...s.button, opacity: loading ? 0.75 : 1 }}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Login'}
            </button>
          </div>
        </div>
      </div>

    </div>
  )
}

const s = {
  page: {
    display: 'flex',
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
    fontFamily: 'Athene Voyage, sans-serif',
  },

  /* ── Left ── */
  leftPanel: {
    flex: 1,
    background: '#DDCA66',
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    overflow: 'hidden',
    padding: '52px 40px 60px 56px',
  },
  decorSvg: {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
  },
  leftTop: {
    position: 'relative',
    zIndex: 1,
  },
  leftBottom: {
    position: 'relative',
    zIndex: 1,
  },
  brandName: {
    fontSize: 70,
    fontWeight: 400,
    color: '#EFEFEF',
    WebkitTextStroke: '1px #EFEFEF',
    lineHeight: 1,
    letterSpacing: '-1px',
  },
  brandSub: {
    fontSize: 35,
    color: '#FFFFFF',
    lineHeight: 1,
    fontWeight: 400,
    letterSpacing: '-2px'
  },

  /* ── Right ── */
  rightPanel: {
    flex: 1,
    background: '#F2ECE7',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 48px',
  },
  cardWrapper: {
    position: 'relative',
    width: '100%',
    maxWidth: 500,
  },
  cardBack: {
    position: 'absolute',
    inset: 0,
    borderRadius: 26,
    background: '#FFFFFF',
    border: '5px solid #000000',
    transform: 'translate(-9px, 10px)',
  },
  cardFront: {
    position: 'relative',
    zIndex: 1,
    background: '#FFFFFF',
    border: '5px solid #000000',
    borderRadius: 26,
    padding: '44px 48px 48px',
  },

  welcomeText: {
    fontSize: 40,
    color: '#2D2D2D',
    lineHeight: 1.05,
    marginBottom: 10,
  },
  subText: {
    fontSize: 30,
    color: '#2D2D2D',
    lineHeight: "25px",
    fontWeight: 400,
    marginBottom: 18,
  },
  divider: {
    height: 2,
    background: '#2D2D2D',
    marginBottom: 26,
  },

  field: {
    marginBottom: 18,
  },
  label: {
    display: 'block',
    fontSize: 30,
    color: '#2D2D2D',
    fontWeight: 400,
    marginBottom: 8,
    lineHeight: 1.2,
  },
  input: {
    width: '100%',
    padding: '10px 16px',
    border: '3px solid #000000',
    borderRadius: 12,
    fontSize: 25,
    color: '#2D2D2D',
    background: '#FFFFFF',
    outline: 'none',
    boxSizing: 'border-box',
    fontFamily: 'Athene Voyage, sans-serif',
  },

  error: {
    fontSize: 22,
    color: '#c0392b',
    background: '#fdf0ef',
    borderRadius: 8,
    padding: '8px 14px',
    marginBottom: 14,
  },

  button: {
    width: '100%',
    padding: '12px',
    background: '#EDCA0F',
    color: '#2D2D2D',
    border: '3px solid black',
    borderRadius: 12,
    fontSize: 35,
    cursor: 'pointer',
    marginTop: 10,
    fontFamily: 'Athene Voyage, sans-serif',
    letterSpacing: '0.3px',
    transition: 'opacity 0.15s',
  },
}
