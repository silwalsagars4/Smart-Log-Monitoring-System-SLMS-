import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { WebSocketProvider } from './contexts/WebSocketContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'

function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/logs" element={<PrivateRoute><Logs /></PrivateRoute>} />
      <Route path="/alerts" element={<PrivateRoute><Alerts /></PrivateRoute>} />
      <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <AppRoutes />
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
