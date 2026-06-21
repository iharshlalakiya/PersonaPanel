import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client.js'
import Nav from '../components/Nav.jsx'

/* ── tiny icon components ──────────────────────────────────────────── */
const UserGroupIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
  </svg>
)

const BeakerIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15M14.25 3.104c.251.023.501.05.75.082M19.8 15a2.25 2.25 0 01.45 2.912C19.48 19.064 18.366 20 17.1 20H6.9c-1.266 0-2.38-.936-3.15-2.088A2.25 2.25 0 014.2 15h15.6z" />
  </svg>
)

const ChartBarIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
  </svg>
)

/* ── API status badge ──────────────────────────────────────────────── */
function ApiStatusBadge({ status }) {
  const variants = {
    idle:    { cls: 'badge-idle',  dot: 'bg-slate-400',   label: 'Not checked' },
    loading: { cls: 'badge-idle',  dot: 'bg-yellow-400 animate-pulse', label: 'Checking…' },
    ok:      { cls: 'badge-ok',    dot: 'bg-emerald-400', label: 'API online' },
    error:   { cls: 'badge-error', dot: 'bg-red-400',     label: 'API offline' },
  }
  const v = variants[status] ?? variants.idle
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${v.cls}`}>
      <span className={`w-2 h-2 rounded-full ${v.dot}`} />
      {v.label}
    </span>
  )
}

/* ── Feature card ──────────────────────────────────────────────────── */
function FeatureCard({ icon, title, description }) {
  return (
    <div className="glass-card p-6 flex flex-col gap-3 hover:scale-[1.02] transition-transform duration-200 cursor-default">
      <div className="w-10 h-10 rounded-lg bg-brand-600/30 flex items-center justify-center text-brand-300">
        {icon}
      </div>
      <h3 className="font-semibold text-white">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  )
}

/* ── Main page ─────────────────────────────────────────────────────── */
export default function HomePage() {
  const [apiStatus, setApiStatus] = useState('idle')
  const [apiData, setApiData]     = useState(null)

  async function checkHealth() {
    setApiStatus('loading')
    setApiData(null)
    try {
      const { data } = await api.get('/api/health')
      setApiData(data)
      setApiStatus('ok')
    } catch {
      setApiStatus('error')
    }
  }

  useEffect(() => { checkHealth() }, [])

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      <Nav actions={
        <div className="flex items-center gap-3">
          <ApiStatusBadge status={apiStatus} />
          <button
            id="btn-check-health"
            onClick={checkHealth}
            className="text-sm font-medium px-3 py-2 rounded-lg border border-white/15
                       hover:border-white/30 transition-colors text-slate-300 hover:text-white"
          >
            Ping API
          </button>
        </div>
      } />

      {/* ── Hero ── */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-8 py-20">
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-600/20 border border-brand-500/30 text-brand-300 text-sm font-medium">
          ✦ AI-Powered Synthetic User Testing
        </span>

        <h1 className="text-5xl sm:text-6xl font-extrabold text-white max-w-3xl leading-tight">
          Test your product with{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-300 to-purple-400">
            AI personas
          </span>
          , not guesswork.
        </h1>

        <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
          PersonaPanel generates diverse synthetic users, runs them through your landing page,
          and surfaces rich qualitative insights — all before you talk to a single real customer.
        </p>

        <div className="flex flex-wrap gap-4 justify-center">
          <Link
            id="btn-run-new-test"
            to="/new-test"
            className="px-8 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 transition-all
                       text-white font-semibold shadow-lg shadow-brand-900/40
                       hover:shadow-xl hover:shadow-brand-700/30"
          >
            Run New Test →
          </Link>
          <a
            id="btn-view-docs"
            href="http://localhost:8001/docs"
            target="_blank"
            rel="noreferrer"
            className="px-8 py-3 rounded-xl border border-white/20 hover:border-white/40 transition-colors text-white font-semibold"
          >
            API Docs
          </a>
        </div>

        {apiData && (
          <div id="health-result" className="glass-card px-6 py-4 text-sm font-mono text-emerald-300 mt-2">
            GET /api/health → {JSON.stringify(apiData)}
          </div>
        )}
        {apiStatus === 'error' && (
          <div id="health-error" className="glass-card px-6 py-4 text-sm font-mono text-red-300 mt-2">
            Could not reach the backend. Is it running on port 8001?
          </div>
        )}
      </main>

      {/* ── Feature grid ── */}
      <section className="px-8 pb-20 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-5xl mx-auto w-full">
        <FeatureCard
          icon={<UserGroupIcon />}
          title="5 Diverse Personas"
          description="Skeptical Buyer, Confused First-Timer, Price-Sensitive Shopper, Mobile Scroller, and Detail Researcher — all in one run."
        />
        <FeatureCard
          icon={<BeakerIcon />}
          title="Parallel Analysis"
          description="All 5 personas run concurrently via asyncio.gather — total time ≈ one persona call, not 5×."
        />
        <FeatureCard
          icon={<ChartBarIcon />}
          title="Synthesised Insights"
          description="Cross-persona friction aggregation, conversion risk score (0-100), and an executive summary — all in one API call."
        />
      </section>
    </div>
  )
}
