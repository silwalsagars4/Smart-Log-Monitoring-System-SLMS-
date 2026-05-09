import client from './client'

export const getLogConfigs = () => client.get('/config/log-paths')
export const createLogConfig = (data) => client.post('/config/log-paths', data)
export const updateLogConfig = (id, data) => client.patch(`/config/log-paths/${id}`, data)
export const deleteLogConfig = (id) => client.delete(`/config/log-paths/${id}`)
