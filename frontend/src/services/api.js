import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api/v1' })
let expertToken = null
let marketToken = window.sessionStorage.getItem('rythu-market-token')

api.interceptors.request.use((config) => {
  const url = config.url || ''
  const method = (config.method || 'get').toLowerCase()
  const expertOnly = url.startsWith('/dashboard/')
    || url === '/auth/me'
    || (url.startsWith('/cases/') && !url.endsWith('/feedback') && !(method === 'post' && url.endsWith('/photos')))
    || (url === '/cases' && method === 'get')
  const token = expertOnly ? expertToken : marketToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  else delete config.headers.Authorization
  return config
})

export const setExpertToken = (token) => {
  expertToken = token || null
}

export const setMarketToken = (token, account) => {
  if (token) {
    window.sessionStorage.setItem('rythu-market-token', token)
    if (account) window.sessionStorage.setItem('rythu-market-account', JSON.stringify(account))
    marketToken = token
  } else {
    window.sessionStorage.removeItem('rythu-market-token')
    window.sessionStorage.removeItem('rythu-market-account')
    marketToken = null
  }
}

export const farmerApi = {
  start: (payload) => api.post('/calls/start', payload),
  message: (payload) => api.post('/calls/message', payload),
  end: (sessionId) => api.post('/calls/end', null, { params: { session_id: sessionId } }),
  feedback: (caseId, payload, accessToken) => api.post(`/cases/${caseId}/feedback`, payload, {
    headers: accessToken ? { 'X-Case-Access-Token': accessToken } : {},
  }),
  uploadPhoto: (caseId, accessToken, photo) => {
    const body = new FormData()
    body.append('photo', photo)
    return api.post(`/cases/${caseId}/photos`, body, { headers: { 'X-Case-Access-Token': accessToken } })
  },
}

export const marketAuthApi = {
  register: (payload) => api.post('/auth/market/register', payload, { timeout: 15000 }),
  login: (payload) => api.post('/auth/market/login', payload, { timeout: 15000 }),
}

export const marketApi = {
  farmerCases: () => api.get('/market/farmer/cases'),
  farmerProfile: () => api.get('/market/farmer/profile'),
  updateFarmerProfile: (payload) => api.patch('/market/farmer/profile', payload),
  workerProfile: () => api.get('/market/worker/profile'),
  updateWorkerProfile: (payload) => api.patch('/market/worker/profile', payload),
  createJob: (payload) => api.post('/market/jobs', payload),
  myJobs: () => api.get('/market/jobs/mine'),
  nearbyJobs: (radiusKm) => api.get('/market/jobs/nearby', { params: { radius_km: radiusKm } }),
  nearbyWorkers: (radiusKm) => api.get('/market/workers/nearby', { params: { radius_km: radiusKm } }),
  bookWorker: (jobId, workerId) => api.post(`/market/jobs/${jobId}/workers/${workerId}/book`),
  createTeam: (payload) => api.post('/market/teams', payload),
  myTeams: () => api.get('/market/teams'),
  addTeamMember: (teamId, payload) => api.post(`/market/teams/${teamId}/members`, payload),
  removeTeamMember: (teamId, workerId) => api.delete(`/market/teams/${teamId}/members/${workerId}`),
  apply: (jobId, payload) => api.post(`/market/jobs/${jobId}/applications`, payload),
  jobApplications: (jobId) => api.get(`/market/jobs/${jobId}/applications`),
  myApplications: () => api.get('/market/worker/applications'),
  workerOffer: (applicationId, payload) => api.patch(`/market/worker/applications/${applicationId}/offer`, payload),
  farmerOffer: (applicationId, payload) => api.patch(`/market/farmer/applications/${applicationId}/offer`, payload),
  acceptApplication: (applicationId) => api.post(`/market/farmer/applications/${applicationId}/accept`),
  workerBookings: () => api.get('/market/worker/bookings'),
  farmerBookings: () => api.get('/market/farmer/bookings'),
  confirmBooking: (bookingId) => api.post(`/market/worker/bookings/${bookingId}/confirm`),
  cancelWorkerBooking: (bookingId) => api.post(`/market/worker/bookings/${bookingId}/cancel`),
  cancelFarmerBooking: (bookingId) => api.post(`/market/farmer/bookings/${bookingId}/cancel`),
}

export const expertApi = {
  login: (payload) => api.post('/auth/login', payload),
  googleConfig: () => api.get('/auth/google/config'),
  googleLogin: (credential) => api.post('/auth/google', { credential }),
  me: () => api.get('/auth/me'),
  updateMe: (payload) => api.patch('/auth/me', payload),
  summary: () => api.get('/dashboard/summary'),
  cases: (params) => api.get('/cases', { params }),
  caseDetail: (caseId) => api.get(`/cases/${caseId}`),
  casePhoto: (caseId, filename) => api.get(`/cases/${caseId}/photos/${encodeURIComponent(filename)}`, { responseType: 'blob' }),
  status: (caseId, payload) => api.patch(`/cases/${caseId}/status`, payload),
  assign: (caseId, payload) => api.post(`/cases/${caseId}/assign`, payload),
  note: (caseId, payload) => api.post(`/cases/${caseId}/notes`, payload),
  followup: (caseId, payload) => api.post(`/cases/${caseId}/followups`, payload),
}
