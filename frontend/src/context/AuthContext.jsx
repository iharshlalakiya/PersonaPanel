/**
 * AuthContext — provides auth state across the entire app.
 *
 * Persistence: stores { access_token, refresh_token, user } in localStorage
 * so the session survives a page refresh.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

const STORAGE_KEY = 'pp_auth'

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadStored)   // { access_token, refresh_token, user_id, email }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Keep localStorage in sync whenever auth changes
  useEffect(() => {
    if (auth) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [auth])

  const signup = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post('/api/auth/signup', { email, password })
      setAuth(data)
      return { ok: true }
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Signup failed'
      setError(msg)
      return { ok: false, message: msg }
    } finally {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post('/api/auth/login', { email, password })
      setAuth(data)
      return { ok: true }
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Login failed'
      setError(msg)
      return { ok: false, message: msg }
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    setAuth(null)
    setError(null)
  }, [])

  return (
    <AuthContext.Provider value={{ auth, loading, error, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
