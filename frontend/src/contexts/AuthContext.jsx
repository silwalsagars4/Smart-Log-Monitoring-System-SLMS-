import { createContext, useContext, useState, useCallback } from 'react'
import { login as apiLogin } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('slms_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const signIn = useCallback(async (username, password) => {
    const { data } = await apiLogin(username, password)
    localStorage.setItem('slms_token', data.access_token)
    const userObj = { username, role: data.role }
    localStorage.setItem('slms_user', JSON.stringify(userObj))
    setUser(userObj)
    return data
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('slms_token')
    localStorage.removeItem('slms_user')
    setUser(null)
  }, [])

  const isAdmin = user?.role === 'admin'
  const isAnalyst = user?.role === 'analyst'
  const isAuthenticated = Boolean(user)

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isAdmin, isAnalyst, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
