import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NewTestPage from './pages/NewTestPage.jsx'
import ResultsPage from './pages/ResultsPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
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

      <Route path="/history" element={
        <ProtectedRoute><HistoryPage /></ProtectedRoute>
      } />

      <Route path="/results/:id" element={
        <ProtectedRoute><ResultsPage /></ProtectedRoute>
      } />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
