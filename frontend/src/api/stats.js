import api from './client'

export const getSummary = () => api.get('/stats/summary')
export const getTrend = (hours = 6) => api.get('/stats/trend', { params: { hours } })
export const getTopIPs = (limit = 10) => api.get('/stats/top-ips', { params: { limit } })
export const getSeverityTrend = (hours = 24) => api.get('/stats/severity-trend', { params: { hours } })
export const getAlerts = (params = {}) => api.get('/alerts', { params })
export const acknowledgeAlert = (id) => api.patch(`/alerts/${id}/acknowledge`)
export const deleteAlert = (id) => api.delete(`/alerts/${id}`)
export const getInteractions = (id) => api.get(`/alerts/${id}/interactions`)
export const postComment = (id, message) => api.post(`/alerts/${id}/comment`, { message })
