import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NewTestPage from './pages/NewTestPage.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/" element={
        <ProtectedRoute><HomePage /></ProtectedRoute>
      } />

      <Route path="/new-test" element={
        <ProtectedRoute><NewTestPage /></ProtectedRoute>
      } />

      {/* /results/:id — page to be built next; for now navigating here shows a stub */}
      <Route path="/results/:id" element={
        <ProtectedRoute>
          <div className="min-h-screen bg-[#0d0d1a] flex items-center justify-center text-slate-400 text-sm">
            Results page coming soon — session saved to Supabase ✓
          </div>
        </ProtectedRoute>
      } />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
