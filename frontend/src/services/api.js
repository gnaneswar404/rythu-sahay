import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api/v1' })
const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'
let marketToken = window.sessionStorage.getItem('rythu-market-token')

export const resolveProfilePhotoUrl = (photoUrl) => {
  if (!photoUrl) return null
  const apiOrigin = new URL(apiBaseUrl, window.location.origin)
  return new URL(photoUrl, apiOrigin).toString()
}

api.interceptors.request.use((config) => {
  if (marketToken) config.headers.Authorization = `Bearer ${marketToken}`
  else delete config.headers.Authorization
  return config
})

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
}

export const marketAuthApi = {
  register: (payload) => api.post('/auth/market/register', payload, { timeout: 15000 }),
  login: (payload) => api.post('/auth/market/login', payload, { timeout: 15000 }),
}

export const marketApi = {
  publicJobs: (search) => api.get('/market/public/jobs', { params: search ? { search } : {} }),
  publicWorkers: (search) => api.get('/market/public/workers', { params: search ? { search } : {} }),
  publicProfile: (accountType, accountId) => api.get(`/market/public/profiles/${accountType}/${accountId}`),
  farmerCases: () => api.get('/market/farmer/cases'),
  farmerProfile: () => api.get('/market/farmer/profile'),
  updateFarmerProfile: (payload) => api.patch('/market/farmer/profile', payload),
  uploadFarmerProfilePhoto: (photo) => {
    const formData = new FormData()
    formData.append('photo', photo)
    return api.post('/market/farmer/profile/photo', formData)
  },
  deleteFarmerProfilePhoto: () => api.delete('/market/farmer/profile/photo'),
  workerProfile: () => api.get('/market/worker/profile'),
  updateWorkerProfile: (payload) => api.patch('/market/worker/profile', payload),
  uploadWorkerProfilePhoto: (photo) => {
    const formData = new FormData()
    formData.append('photo', photo)
    return api.post('/market/worker/profile/photo', formData)
  },
  deleteWorkerProfilePhoto: () => api.delete('/market/worker/profile/photo'),
  createJob: (payload) => api.post('/market/jobs', payload),
  myJobs: () => api.get('/market/jobs/mine'),
  nearbyJobs: (radiusKm) => api.get('/market/jobs/nearby', { params: { radius_km: radiusKm } }),
  nearbyWorkers: (radiusKm) => api.get('/market/workers/nearby', { params: { radius_km: radiusKm } }),
  bookWorker: (jobId, workerId) => api.post(`/market/jobs/${jobId}/workers/${workerId}/book`),
  reportWorkerAbsence: (bookingId) => api.post(`/market/farmer/bookings/${bookingId}/report-absence`),
  replacementWorkers: (bookingId, radiusKm = 20) => api.get(`/market/farmer/bookings/${bookingId}/replacements`, {
    params: { radius_km: radiusKm },
  }),
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
  bookingMessages: (accountType, bookingId) => api.get(`/market/${accountType}/bookings/${bookingId}/messages`),
  sendBookingMessage: (accountType, bookingId, payload) => api.post(`/market/${accountType}/bookings/${bookingId}/messages`, payload),
}
