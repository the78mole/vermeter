/**
 * Axios API client.
 *
 * The Bearer token comes from oidc-client-ts (Keycloak).
 * We obtain it through the UserManager so this module stays framework-agnostic
 * and can be used outside of React components (e.g. Zustand actions).
 */
import axios from 'axios'
import { UserManager } from 'oidc-client-ts'
import { oidcConfig } from '../oidc'

// Singleton UserManager – shared with AuthProvider in main.jsx
export const userManager = new UserManager(oidcConfig)

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
})

api.interceptors.request.use(async (config) => {
  const user = await userManager.getUser()
  if (user?.access_token) {
    config.headers.Authorization = `Bearer ${user.access_token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      // Token is invalid / expired – trigger a new login
      await userManager.signinRedirect()
    }
    return Promise.reject(err)
  }
)

export default api

// --- Auth ---
export const getMe = () => api.get('/auth/me')

// --- Admin ---
export const getAdminStats = () => api.get('/admin/stats')
export const getLandlords = () => api.get('/admin/landlords')
export const createLandlord = (data) => api.post('/admin/landlords', data)
export const updateLandlord = (id, data) => api.patch(`/admin/landlords/${id}`, data)
export const deactivateLandlord = (id) => api.delete(`/admin/landlords/${id}`)
export const getLandlordProfile = (id) => api.get(`/admin/landlords/${id}/profile`)
export const upsertLandlordProfile = (id, data) => api.put(`/admin/landlords/${id}/profile`, data)
export const listDocuments = (id) => api.get(`/admin/landlords/${id}/documents`)
export const uploadDocument = (id, file, description, tags = []) => {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  if (description) params.append('description', description)
  tags.forEach((t) => params.append('tags', t))
  return api.post(`/admin/landlords/${id}/documents?${params.toString()}`, form)
}
export const searchTags = (q = '') => api.get('/admin/tags', { params: { q } })
export const downloadDocumentUrl = (landlordId, docId) =>
  `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/admin/landlords/${landlordId}/documents/${docId}/download`
export const updateDocument = (landlordId, docId, data) =>
  api.patch(`/admin/landlords/${landlordId}/documents/${docId}`, data)
export const deleteDocument = (landlordId, docId) =>
  api.delete(`/admin/landlords/${landlordId}/documents/${docId}`)

// --- Landlord ---
export const getProperties = () => api.get('/landlord/properties')
export const createProperty = (data) => api.post('/landlord/properties', data)
export const getPropertyUnits = (propId) => api.get(`/landlord/properties/${propId}/units`)
export const createUnit = (propId, data) => api.post(`/landlord/properties/${propId}/units`, data)
export const getUnitMeters = (unitId) => api.get(`/landlord/units/${unitId}/meters`)
export const createMeter = (unitId, data) => api.post(`/landlord/units/${unitId}/meters`, data)
export const addMeterReading = (meterId, data) => api.post(`/landlord/meters/${meterId}/readings`, data)
export const getMeterReadings = (meterId) => api.get(`/landlord/meters/${meterId}/readings`)
export const getContracts = () => api.get('/landlord/contracts')
export const createContract = (data) => api.post('/landlord/contracts', data)
export const updateContractStatus = (id, status) => api.patch(`/landlord/contracts/${id}/status`, { status })
export const getTenants = () => api.get('/landlord/tenants')
export const getUtilityBills = () => api.get('/landlord/utility-bills')
export const updateBillStatus = (id, status) => api.patch(`/landlord/utility-bills/${id}/status`, { status })
export const generateBillPdf = (id) => api.post(`/billing/utility-bills/${id}/generate-pdf`)
export const calculateGraph = (graph, billId) => {
  const params = billId ? { bill_id: billId } : {}
  return api.post('/billing/calculate-graph', graph, { params })
}

// --- Tenant ---
export const myContracts = () => api.get('/tenant/contracts')
export const myUtilityBills = () => api.get('/tenant/utility-bills')
export const myMeters = () => api.get('/tenant/meters')
export const myMeterReadings = (meterId) => api.get(`/tenant/meters/${meterId}/readings`)
export const myInterpolatedReadings = (meterId) => api.get(`/tenant/meters/${meterId}/interpolated`)
export const submitMeterReading = (meterId, data) => api.post(`/tenant/meters/${meterId}/readings`, data)

// --- Admin Users ---
export const listAdminUsers = () => api.get('/admin-users')
export const createAdminUser = (data) => api.post('/admin-users', data)
export const getAdminUser = (id) => api.get(`/admin-users/${id}`)
export const updateAdminUser = (id, data) => api.patch(`/admin-users/${id}`, data)
export const deleteAdminUser = (id) => api.delete(`/admin-users/${id}`)
