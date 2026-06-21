/**
 * NewTestPage — /new-test
 *
 * Form:
 *   - URL input
 *   - 5 persona checkboxes (all checked by default)
 *   - Run Test button
 *
 * States:
 *   idle     → form is ready for input
 *   running  → POST /api/test/run in-flight; animated loading UI
 *   error    → API or validation failure; clear message + retry
 *   (success → navigate to /results/:session_id)
 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { longApi } from '../api/client.js'
import Nav from '../components/Nav.jsx'

// ── Persona definitions (mirrors backend personas_config) ────────────────
const PERSONAS = [
  {
    key: 'skeptical_buyer',
    name: 'Skeptical Buyer',
    description: 'Distrusts claims without evidence; hunts for proof and guarantees',
    icon: '🔍',
    color: 'from-violet-500/20 to-violet-600/10 border-violet-500/30',
    dot: 'bg-violet-400',
  },
  {
    key: 'confused_first_timer',
    name: 'Confused First-Timer',
    description: 'No product context; needs "what is this?" answered in 5 seconds',
    icon: '🤔',
    color: 'from-sky-500/20 to-sky-600/10 border-sky-500/30',
    dot: 'bg-sky-400',
  },
  {
    key: 'price_sensitive_shopper',
    name: 'Price-Sensitive Shopper',
    description: 'Immediately hunts for pricing; frustrated by hidden costs',
    icon: '💰',
    color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30',
    dot: 'bg-emerald-400',
  },
  {
    key: 'impatient_mobile_scroller',
    name: 'Impatient Mobile Scroller',
    description: 'Fast-scroll, headlines-only; bounces if value prop isn\'t instant',
    icon: '📱',
    color: 'from-orange-500/20 to-orange-600/10 border-orange-500/30',
    dot: 'bg-orange-400',
  },
  {
    key: 'detail_oriented_researcher',
    name: 'Detail-Oriented Researcher',
    description: 'Wants specs, FAQs, and terms; suspicious of incomplete info',
    icon: '📋',
    color: 'from-pink-500/20 to-pink-600/10 border-pink-500/30',
    dot: 'bg-pink-400',
  },
]

// ── Loading stage messages (cycles during the wait) ──────────────────────
const LOADING_STAGES = [
  { icon: '📸', message: 'Capturing page screenshot…' },
  { icon: '🔍', message: 'Skeptical Buyer reading your page…' },
  { icon: '🤔', message: 'Confused First-Timer trying to understand…' },
  { icon: '💰', message: 'Price-Sensitive Shopper hunting for costs…' },
  { icon: '📱', message: 'Mobile Scroller skimming the hero…' },
  { icon: '📋', message: 'Researcher diving into the details…' },
  { icon: '🧠', message: 'Synthesising insights across personas…' },
  { icon: '💾', message: 'Saving results…' },
]

// ── Animated dots ─────────────────────────────────────────────────────────
function LoadingDots() {
  return (
    <span className="inline-flex gap-1 ml-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: '0.9s' }}
        />
      ))}
    </span>
  )
}

// ── Circular progress ring ────────────────────────────────────────────────
function ProgressRing({ progress }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const offset = circ - (progress / 100) * circ

  return (
    <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
      {/* Track */}
      <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
      {/* Fill */}
      <circle
        cx="60" cy="60" r={r} fill="none"
        stroke="url(#ring-gradient)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <defs>
        <linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#7a87fa" />
          <stop offset="100%" stopColor="#5c5ff5" />
        </linearGradient>
      </defs>
    </svg>
  )
}

// ── Persona checkbox card ─────────────────────────────────────────────────
function PersonaCard({ persona, checked, onChange, disabled }) {
  return (
    <label
      className={`
        relative flex items-start gap-3 p-4 rounded-xl border cursor-pointer
        bg-gradient-to-br transition-all duration-200 select-none
        ${persona.color}
        ${checked ? 'ring-1 ring-white/20' : 'opacity-60'}
        ${disabled ? 'cursor-not-allowed' : 'hover:opacity-100 hover:scale-[1.01]'}
      `}
    >
      {/* Custom checkbox */}
      <div className={`
        mt-0.5 w-5 h-5 rounded-md border flex-shrink-0 flex items-center justify-center
        transition-all duration-150
        ${checked
          ? 'bg-brand-500 border-brand-400'
          : 'bg-white/5 border-white/20'
        }
      `}>
        {checked && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none">{persona.icon}</span>
          <span className="text-sm font-semibold text-white">{persona.name}</span>
        </div>
        <p className="text-xs text-slate-400 mt-1 leading-relaxed">{persona.description}</p>
      </div>
    </label>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────
export default function NewTestPage() {
  const { auth } = useAuth()
  const navigate = useNavigate()

  const [url, setUrl]           = useState('')
  const [selected, setSelected] = useState(() => Object.fromEntries(PERSONAS.map(p => [p.key, true])))
  const [phase, setPhase]       = useState('idle')   // 'idle' | 'running' | 'error'
  const [error, setError]       = useState(null)
  const [stageIdx, setStageIdx] = useState(0)
  const [progress, setProgress] = useState(0)

  const stageTimer = useRef(null)
  const progressTimer = useRef(null)

  // Rotate stage messages while running
  useEffect(() => {
    if (phase !== 'running') return
    stageTimer.current = setInterval(() => {
      setStageIdx(i => (i + 1) % LOADING_STAGES.length)
    }, 4000)
    return () => clearInterval(stageTimer.current)
  }, [phase])

  // Simulate progress (advances to ~90% then stalls waiting for response)
  useEffect(() => {
    if (phase !== 'running') return
    setProgress(0)
    let p = 0
    progressTimer.current = setInterval(() => {
      p += Math.random() * 2.2
      if (p >= 90) {
        p = 90
        clearInterval(progressTimer.current)
      }
      setProgress(Math.min(p, 90))
    }, 800)
    return () => clearInterval(progressTimer.current)
  }, [phase])

  function togglePersona(key) {
    setSelected(s => ({ ...s, [key]: !s[key] }))
  }

  function selectAll(val) {
    setSelected(Object.fromEntries(PERSONAS.map(p => [p.key, val])))
  }

  const selectedNames = PERSONAS.filter(p => selected[p.key]).map(p => p.name)
  let isValidUrl = false
  try {
    const parsed = new URL(url.trim())
    isValidUrl = parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch (_) {
    isValidUrl = false
  }
  const canSubmit  = isValidUrl && selectedNames.length > 0 && phase === 'idle'

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return

    setError(null)
    setPhase('running')
    setStageIdx(0)

    try {
      const { data } = await longApi.post('/api/test/run', {
        url: url.trim(),
        personas: selectedNames,
        user_id: auth?.user_id ?? null,
      })

      // Jump progress to 100 on success
      clearInterval(progressTimer.current)
      setProgress(100)

      if (!data.ok) {
        throw new Error(data.error || 'Pipeline returned ok=false')
      }

      // Brief pause so user sees 100% before redirect
      await new Promise(r => setTimeout(r, 600))
      navigate(`/results/${data.session_id}`, { state: { runData: data } })

    } catch (err) {
      clearInterval(stageTimer.current)
      clearInterval(progressTimer.current)
      setProgress(0)
      setPhase('error')

      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. The pipeline can take up to 70 s — please try again.')
      } else {
        const detail = err.response?.data?.detail ?? err.response?.data?.error ?? err.message
        setError(detail || 'Something went wrong. Check the backend is running.')
      }
    }
  }

  const isRunning = phase === 'running'
  const stage = LOADING_STAGES[stageIdx]

  return (
    <div className="min-h-screen bg-[#0d0d1a] flex flex-col">
      <Nav />

      <main className="flex-1 flex flex-col items-center justify-start px-4 py-12 sm:py-16">

        {/* ── Header ── */}
        <div className="w-full max-w-2xl mb-10 text-center">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-600/20
                           border border-brand-500/30 text-brand-300 text-xs font-medium mb-4">
            ✦ AI Persona Analysis
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            New Test
          </h1>
          <p className="text-slate-400 mt-2 text-sm sm:text-base">
            Enter a URL and choose which personas will analyse it.
            Results are ready in ~40 seconds.
          </p>
        </div>

        {/* ── Card ── */}
        <div className="w-full max-w-2xl glass-card p-6 sm:p-8 flex flex-col gap-8">

          {/* ── URL field ── */}
          <section>
            <label htmlFor="url-input" className="block text-sm font-semibold text-slate-200 mb-2">
              Page URL
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm select-none pointer-events-none">
                🔗
              </span>
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={e => { setUrl(e.target.value); setError(null) }}
                disabled={isRunning}
                placeholder="https://your-landing-page.com"
                autoComplete="off"
                spellCheck={false}
                className={`
                  w-full pl-9 pr-4 py-3 rounded-xl border bg-white/5 text-white text-sm
                  placeholder-slate-600 transition-all duration-150 outline-none
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${url && !isValidUrl
                    ? 'border-red-500/60 focus:ring-1 focus:ring-red-500/40'
                    : 'border-white/10 focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30'
                  }
                `}
              />
            </div>
            {url && !isValidUrl && (
              <p className="text-xs text-red-400 mt-1.5">Please enter a valid URL (e.g. https://example.com)</p>
            )}
          </section>

          {/* ── Personas ── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-slate-200">
                Personas
                <span className="ml-2 text-xs font-normal text-slate-500">
                  ({selectedNames.length} / {PERSONAS.length} selected)
                </span>
              </span>
              <div className="flex gap-3 text-xs">
                <button
                  type="button"
                  onClick={() => selectAll(true)}
                  disabled={isRunning}
                  className="text-brand-300 hover:text-brand-200 transition-colors disabled:opacity-40"
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => selectAll(false)}
                  disabled={isRunning}
                  className="text-slate-400 hover:text-slate-300 transition-colors disabled:opacity-40"
                >
                  None
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PERSONAS.map(p => (
                <PersonaCard
                  key={p.key}
                  persona={p}
                  checked={selected[p.key]}
                  onChange={() => togglePersona(p.key)}
                  disabled={isRunning}
                />
              ))}
            </div>

            {selectedNames.length === 0 && (
              <p className="text-xs text-amber-400 mt-2">Select at least one persona to run a test.</p>
            )}
          </section>

          {/* ── Error banner ── */}
          {phase === 'error' && error && (
            <div
              id="run-error"
              className="flex items-start gap-3 px-4 py-3 rounded-xl bg-red-500/10
                         border border-red-500/25 text-red-300 text-sm leading-relaxed"
            >
              <span className="text-base mt-0.5">⚠️</span>
              <div>
                <p className="font-semibold mb-0.5">Test failed</p>
                <p className="text-red-400 text-xs">{error}</p>
              </div>
            </div>
          )}

          {/* ── Submit button ── */}
          {!isRunning && (
            <button
              id="btn-run-test"
              type="submit"
              form="new-test-form"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={`
                w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-200
                shadow-lg shadow-brand-900/30
                ${canSubmit
                  ? 'bg-brand-600 hover:bg-brand-500 text-white hover:shadow-xl hover:shadow-brand-700/30 active:scale-[0.99]'
                  : 'bg-brand-900/40 text-brand-600 cursor-not-allowed'
                }
              `}
            >
              {phase === 'error' ? '↺ Try Again' : `Run Test with ${selectedNames.length} Persona${selectedNames.length !== 1 ? 's' : ''}`}
            </button>
          )}
        </div>

        {/* ── Loading overlay card ── */}
        {isRunning && (
          <div className="w-full max-w-2xl mt-4 glass-card p-8 flex flex-col items-center gap-6 animate-in fade-in">

            {/* Ring + percentage */}
            <div className="relative">
              <ProgressRing progress={progress} />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white tabular-nums">
                  {Math.round(progress)}%
                </span>
              </div>
            </div>

            {/* Stage message */}
            <div className="text-center">
              <p className="text-lg font-semibold text-white flex items-center justify-center gap-2">
                <span className="text-2xl">{stage.icon}</span>
                {stage.message}
                <LoadingDots />
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Running {selectedNames.length} persona{selectedNames.length !== 1 ? 's' : ''} in parallel — usually 40-60 s total
              </p>
            </div>

            {/* Persona pills — show which ones are running */}
            <div className="flex flex-wrap justify-center gap-2">
              {PERSONAS.filter(p => selected[p.key]).map(p => (
                <span
                  key={p.key}
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
                    bg-gradient-to-r ${p.color} border
                  `}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${p.dot} animate-pulse`} />
                  {p.name}
                </span>
              ))}
            </div>

            {/* Cancel hint */}
            <p className="text-xs text-slate-600">
              Analysing page content with Gemini 2.0 Flash — please wait…
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
