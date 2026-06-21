import { useState, useEffect } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import api from '../api/client.js'
import Nav from '../components/Nav.jsx'

// ── Icons ─────────────────────────────────────────────────────────────
const ChevronDown = ({ className = 'w-5 h-5' }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
)

const AlertCircle = ({ className = 'w-5 h-5' }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
)

const CheckCircle = ({ className = 'w-5 h-5' }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
)

// ── Score Badge Component ─────────────────────────────────────────────
function ScoreBadge({ score }) {
  let color = 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
  let label = 'Low Risk'
  
  if (score > 66) {
    color = 'text-red-400 border-red-500/30 bg-red-500/10'
    label = 'High Risk'
  } else if (score > 33) {
    color = 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
    label = 'Medium Risk'
  }

  return (
    <div className={`inline-flex flex-col items-center justify-center w-32 h-32 rounded-full border-4 ${color} shadow-lg backdrop-blur-sm`}>
      <span className="text-4xl font-black">{score}</span>
      <span className="text-xs font-semibold uppercase tracking-wider mt-1 opacity-80">{label}</span>
    </div>
  )
}

// ── Issue Card ────────────────────────────────────────────────────────
function IssueCard({ issue }) {
  let badgeColor = 'bg-slate-500/20 text-slate-300 border-slate-500/30'
  if (issue.severity === 'high') badgeColor = 'bg-red-500/20 text-red-300 border-red-500/30'
  if (issue.severity === 'medium') badgeColor = 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'

  return (
    <div className="glass-card p-5 border-l-4" style={{ borderLeftColor: issue.severity === 'high' ? '#ef4444' : issue.severity === 'medium' ? '#eab308' : '#64748b' }}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <h4 className="text-white font-semibold text-lg leading-tight">{issue.issue}</h4>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${badgeColor}`}>
          {issue.severity}
        </span>
      </div>
      <p className="text-sm text-slate-300 mb-4">{issue.suggested_fix}</p>
      <div className="flex flex-wrap gap-2">
        {(Array.isArray(issue.flagged_by) ? issue.flagged_by : [issue.flagged_by]).map(p => (
          <span key={p} className="inline-flex items-center px-2.5 py-1 rounded-md bg-white/5 text-xs text-slate-400 border border-white/10">
            {p}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Persona Accordion ─────────────────────────────────────────────────
function PersonaAccordion({ persona }) {
  const [isOpen, setIsOpen] = useState(false)
  const isPositive = persona.would_convert

  return (
    <div className="glass-card overflow-hidden">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className={`w-3 h-3 rounded-full ${isPositive ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' : 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`} />
          <div>
            <h3 className="text-lg font-bold text-white">{persona.persona_name}</h3>
            <p className="text-sm text-slate-400 mt-0.5">
              {isPositive ? 'Would convert' : 'Would NOT convert'}
            </p>
          </div>
        </div>
        <div className={`text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
          <ChevronDown />
        </div>
      </button>

      {isOpen && (
        <div className="p-5 pt-0 border-t border-white/5 mt-2 bg-black/20">
          <div className="mb-6 mt-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Gut Reaction</h4>
            <p className="text-slate-300 italic">"{persona.gut_reaction}"</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5 mb-3">
                <AlertCircle className="w-4 h-4" /> Friction Points
              </h4>
              {persona.friction_points && persona.friction_points.length > 0 ? (
                <ul className="space-y-3">
                  {persona.friction_points.map((fp, i) => (
                    <li key={i} className="text-sm bg-red-500/5 p-3 rounded-lg border border-red-500/10">
                      <div className="font-medium text-slate-200 mb-1">{fp.issue}</div>
                      <div className="text-xs text-slate-400">Fix: {fp.suggested_fix}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">None reported.</p>
              )}
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5 mb-3">
                <CheckCircle className="w-4 h-4" /> Positive Signals
              </h4>
              {persona.positive_signals && persona.positive_signals.length > 0 ? (
                <ul className="space-y-2">
                  {persona.positive_signals.map((sig, i) => (
                    <li key={i} className="text-sm text-emerald-100/70 bg-emerald-500/5 p-2 px-3 rounded border border-emerald-500/10">
                      {sig}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">None reported.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────
export default function ResultsPage() {
  const { id } = useParams()
  const location = useLocation()
  const [data, setData] = useState(location.state?.runData || null)
  const [loading, setLoading] = useState(!data)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!data) {
      api.get(`/api/test/${id}`)
        .then(res => {
          if (res.data.ok) setData(res.data)
          else setError(res.data.error || 'Failed to fetch results')
        })
        .catch(err => setError(err.message))
        .finally(() => setLoading(false))
    }
  }, [id, data])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0d0d1a] flex items-center justify-center text-slate-400">
        <div className="animate-pulse flex items-center gap-2">
          <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" />
          <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s'}} />
          <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s'}} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0d0d1a] flex flex-col">
        <Nav />
        <div className="flex-1 flex items-center justify-center p-6 text-center">
          <div className="glass-card p-8 max-w-md w-full border-red-500/30">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Error loading results</h2>
            <p className="text-slate-400 text-sm mb-6">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  const session = data.session || data
  const synthesis = data.synthesis || {}
  const personas = data.persona_results || []
  
  const topIssues = synthesis.top_priority_issues || []
  const score = synthesis.overall_conversion_risk_score ?? 0

  return (
    <div className="min-h-screen bg-[#0d0d1a] flex flex-col pb-20">
      <Nav />
      
      <main className="max-w-6xl mx-auto w-full px-6 pt-10">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Analysis Results</h1>
          <a href={session.url} target="_blank" rel="noreferrer" className="text-brand-400 hover:text-brand-300 transition-colors text-sm font-medium mt-1 inline-flex items-center gap-1">
            {session.url} ↗
          </a>
        </div>

        {/* Top Section: Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
          {/* Screenshot */}
          <div className="lg:col-span-1 glass-card overflow-hidden p-2 relative group">
            {session.screenshot_url ? (
              <div className="w-full h-[400px] rounded bg-black/40 border border-white/5 overflow-hidden">
                <img 
                  src={session.screenshot_url} 
                  alt="Page screenshot" 
                  className="w-full h-auto object-cover object-top opacity-80 group-hover:opacity-100 transition-opacity duration-500" 
                />
              </div>
            ) : (
              <div className="w-full h-[400px] rounded bg-black/40 border border-white/5 flex items-center justify-center text-slate-500 text-sm">
                No screenshot available
              </div>
            )}
          </div>

          {/* Synthesis Summary */}
          <div className="lg:col-span-2 glass-card p-8 flex flex-col justify-center">
            <div className="flex flex-col sm:flex-row items-center gap-8 mb-8">
              <ScoreBadge score={score} />
              <div>
                <h2 className="text-xl font-bold text-white mb-2">Executive Summary</h2>
                <p className="text-slate-300 leading-relaxed text-base">
                  {synthesis.summary || "No summary available."}
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 pt-6 border-t border-white/10">
              <div>
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Conversion Rate</p>
                <p className="text-2xl font-bold text-white">
                  {personas.filter(p => p.would_convert).length} / {personas.length}
                </p>
              </div>
              <div>
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Top Issues</p>
                <p className="text-2xl font-bold text-white">{topIssues.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Middle Section: Top Priority Issues */}
        {topIssues.length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded bg-red-500/20 text-red-400 flex items-center justify-center text-sm border border-red-500/30">
                <AlertCircle className="w-4 h-4" />
              </span>
              Top Priority Issues
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {topIssues.map((issue, i) => (
                <IssueCard key={i} issue={issue} />
              ))}
            </div>
          </div>
        )}

        {/* Bottom Section: Individual Personas */}
        <div>
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <span className="w-8 h-8 rounded bg-brand-500/20 text-brand-400 flex items-center justify-center text-sm border border-brand-500/30">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </span>
            Detailed Persona Breakdown
          </h2>
          <div className="flex flex-col gap-3">
            {personas.map((p, i) => (
              <PersonaAccordion key={i} persona={p} />
            ))}
          </div>
        </div>

      </main>
    </div>
  )
}
