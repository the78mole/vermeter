import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// --- Auth ---
export const login = (email, password) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  return api.post('/auth/login', form)
}
export const register = (data) => api.post('/auth/register', data)
export const getMe = () => api.get('/auth/me')

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
