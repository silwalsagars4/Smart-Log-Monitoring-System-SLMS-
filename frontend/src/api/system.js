import api from './client'

/** Fetch the latest system hardware & OS telemetry from the backend. */
export const getSystemStats = () => api.get('/v1/system/stats')
