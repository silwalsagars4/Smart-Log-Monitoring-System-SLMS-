import api from './client'

export const getLogs = (params = {}) => api.get('/logs', { params })
export const getLog = (id) => api.get(`/logs/${id}`)
export const ingestLog = (body) => api.post('/logs/ingest', body)
