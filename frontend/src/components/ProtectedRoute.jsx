/**
 * ProtectedRoute — redirects unauthenticated users to /login.
 * Wrap any <Route> element with this component.
 *
 * Usage:
 *   <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { auth } = useAuth()
  const location = useLocation()

  if (!auth) {
    // Pass the attempted URL so LoginPage can redirect back after auth
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
