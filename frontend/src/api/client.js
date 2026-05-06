import axios from 'axios'

// Get the URL from the environment
const rawUrl = import.meta.env.VITE_API_URL;

// If it exists and doesn't start with http, add it. Otherwise, use localhost.
const getBaseUrl = () => {
  if (rawUrl) {
    return rawUrl.startsWith('http') ? rawUrl : `https://${rawUrl}`;
  }
  return 'http://localhost:8001';
};

const api = axios.create({
  baseURL: getBaseUrl(),
  timeout: 30000,
})

// Inject token into every request automatically
api.interceptors.request.use(config => {
  const token = window.__authToken  // stored in memory, not localStorage
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If any request returns 401, clear token and reload
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      window.__authToken = null
      console.warn('Unauthorized request rejected; token cleared. Please sign in again.')
    }
    return Promise.reject(error)
  }
)

export const login = (username, password) => {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }).then(r => r.data)
}

export const getMe = () =>
  api.get('/auth/me').then(r => r.data)

export const getAvailableDates  = () => api.get('/api/available-dates').then(r => r.data)
export const getLoadedDates     = () => api.get('/api/loaded-dates').then(r => r.data)
export const loadDate           = (d) => api.post(`/api/load-date/${d}`).then(r => r.data)
export const loadDates          = (dates) => api.post('/api/load-dates', { dates: dates.map(d => d.replace(/-/g, '')) }, { headers: { 'Content-Type': 'application/json' }, timeout: 60000 }).then(r => r.data)
export const getLoadStatus      = (d) => api.get(`/api/load-status/${d.replace(/-/g, '')}`, { timeout: 30000 }).then(r => r.data)
export const getLoadStatuses    = (dates) => api.get('/api/load-statuses', { params: { dates: dates.map(d => d.replace(/-/g, '')).join(',') }, timeout: 30000 }).then(r => r.data)
export const getScopes          = () => api.get('/api/scopes').then(r => r.data)
export const getComparison      = (date) => api.get(`/api/comparison/${date}`).then(r => r.data)
export const getDaily           = (scope, date) => api.get('/api/daily', { params: { scope_name: scope, agg_date: date }, timeout: 30000 }).then(r => r.data)
export const getDailyRange      = (scope, startDate, endDate) => api.get('/api/daily', { params: { scope_name: scope, start_date: startDate, end_date: endDate }, timeout: 60000 }).then(r => r.data)
export const getHourly          = (scope, date, category) => api.get('/api/hourly', { params: { scope_name: scope, agg_date: date, category } }).then(r => r.data)
export const getGamingBreakdown  = (scope, date) =>
  api.get('/api/gaming/breakdown',  { params: { scope_name: scope, agg_date: date } }).then(r => r.data)

export const getSocialBreakdown  = (scope, date) =>
  api.get('/api/social/breakdown',  { params: { scope_name: scope, agg_date: date } }).then(r => r.data)

export const getVideoBreakdown   = (scope, date) =>
  api.get('/api/video/breakdown',   { params: { scope_name: scope, agg_date: date } }).then(r => r.data)

export const getDnsDetail        = (scope, date) =>
  api.get('/api/dns/detail',        { params: { scope_name: scope, agg_date: date } }).then(r => r.data)

export const getTrends           = (scope) =>
  api.get('/api/trends',            { params: { scope_name: scope } }).then(r => r.data)