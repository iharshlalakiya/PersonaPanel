import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client.js'
import Nav from '../components/Nav.jsx'
import { useAuth } from '../context/AuthContext.jsx'

function HistoryScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return (
      <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30">
        Incomplete
      </span>
    )
  }

  let color = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  let label = 'Low Risk'
  
  if (score > 66) {
    color = 'bg-red-500/20 text-red-300 border-red-500/30'
    label = 'High Risk'
  } else if (score > 33) {
    color = 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
    label = 'Medium Risk'
  }

  return (
    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${color}`}>
      {label} ({score})
    </span>
  )
}

function HistoryCard({ testSession }) {
  const date = new Date(testSession.created_at).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })

  return (
    <Link to={`/results/${testSession.id}`} className="block glass-card p-5 hover:bg-white/[0.04] transition-colors border-l-4 border-l-brand-500/50 hover:border-l-brand-400 group">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-bold text-lg truncate group-hover:text-brand-300 transition-colors">
            {testSession.url}
          </h3>
          <p className="text-slate-400 text-sm mt-1 flex items-center gap-2">
            <svg className="w-4 h-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {date}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <HistoryScoreBadge score={testSession.overall_conversion_risk_score} />
          <svg className="w-5 h-5 text-slate-500 group-hover:text-brand-300 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Link>
  )
}

export default function HistoryPage() {
  const { auth } = useAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!auth?.user_id) {
      setLoading(false)
      setError("You must be logged in to view history.")
      return
    }

    api.get(`/api/test/history?user_id=${auth.user_id}`)
      .then(res => {
        if (res.data.ok) {
          setHistory(res.data.history || [])
        } else {
          setError(res.data.error || 'Failed to fetch history')
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [auth])

  return (
    <div className="min-h-screen bg-[#0d0d1a] flex flex-col pb-20">
      <Nav />
      
      <main className="max-w-4xl mx-auto w-full px-6 pt-10">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Test History</h1>
          <p className="text-slate-400 mt-2 text-sm">Review your past synthetic user tests.</p>
        </div>

        {loading ? (
          <div className="flex flex-col gap-3 animate-pulse">
            {[1, 2, 3].map(i => (
              <div key={i} className="glass-card p-5 border-l-4 border-l-white/10">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="h-5 w-64 bg-white/5 rounded mb-2"></div>
                    <div className="h-3 w-32 bg-white/5 rounded"></div>
                  </div>
                  <div className="h-6 w-24 bg-white/5 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="glass-card p-6 border-red-500/30 text-center">
            <p className="text-red-400 text-sm mb-2">Error loading history</p>
            <p className="text-slate-400 text-xs">{error}</p>
          </div>
        ) : history.length === 0 ? (
          <div className="glass-card p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4 text-slate-500">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h2 className="text-lg font-bold text-white mb-2">No tests yet</h2>
            <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto">
              You haven't run any tests yet. Click the button below to start your first synthetic user test.
            </p>
            <Link to="/new-test" className="px-6 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 transition-colors text-white font-medium text-sm">
              Run New Test
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {history.map(session => (
              <HistoryCard key={session.id} testSession={session} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
