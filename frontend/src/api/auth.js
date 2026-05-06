import api from './client'

export const login = (username, password) =>
  api.post('/auth/login', { username, password })

export const register = (username, email, password) =>
  api.post('/auth/register', { username, email, password })

export const getMe = () => api.get('/auth/me')

export const getUsers = () => api.get('/auth/users')

export const createUser = (data) => api.post('/auth/users', data)

export const updateUserRole = (userId, role) => api.patch(`/auth/users/${userId}/role`, { role })
