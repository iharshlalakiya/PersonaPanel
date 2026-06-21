import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NewTestPage from './pages/NewTestPage.jsx'
import ResultsPage from './pages/ResultsPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public landing page */}
        <Route path="/" element={<LandingPage />} />

        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Dashboard */}
        <Route path="/dashboard" element={
          <ProtectedRoute><DashboardPage /></ProtectedRoute>
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
    </ErrorBoundary>
  )
}
