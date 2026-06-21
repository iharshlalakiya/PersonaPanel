import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/* ── tiny icons ─────────────────────────────────────────────────────── */
const SparkleIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09z" />
  </svg>
)

const EyeIcon = ({ open }) =>
  open ? (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ) : (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
    </svg>
  )

/* ── field component ─────────────────────────────────────────────────── */
function Field({ id, label, type = 'text', value, onChange, autoComplete }) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-300">{label}</label>
      <div className="relative">
        <input
          id={id}
          type={isPassword && show ? 'text' : type}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500
                     focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
        />
        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShow(s => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
          >
            <EyeIcon open={show} />
          </button>
        )}
      </div>
    </div>
  )
}

/* ── main page ───────────────────────────────────────────────────────── */
export default function LoginPage() {
  const { login, signup, loading, error } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname ?? '/dashboard'
  const [mode, setMode]       = useState('login')   // 'login' | 'signup'
  const [email, setEmail]     = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  const isLogin = mode === 'login'

  async function handleSubmit(e) {
    e.preventDefault()
    setLocalError(null)
    setSuccessMsg(null)

    if (isLogin) {
      const result = await login(email, password)
      if (result.ok) navigate(from, { replace: true })
      else setLocalError(result.message)
    } else {
      const result = await signup(email, password)
      if (result.ok) {
        navigate(from, { replace: true })
      } else if (result.message?.includes('confirm')) {
        setSuccessMsg(result.message)
      } else {
        setLocalError(result.message)
      }
    }
  }

  function switchMode() {
    setMode(m => m === 'login' ? 'signup' : 'login')
    setLocalError(null)
    setSuccessMsg(null)
  }

  const displayError = localError || error

  return (
    <div className="min-h-screen gradient-bg flex flex-col items-center justify-center px-4">
      {/* card */}
      <div className="glass-card w-full max-w-md p-8 flex flex-col gap-6">
        {/* logo */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-xl bg-brand-600/30 flex items-center justify-center text-brand-300">
            <SparkleIcon />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              {isLogin
                ? 'Sign in to access your PersonaPanel workspace.'
                : 'Start testing with AI personas in minutes.'}
            </p>
          </div>
        </div>

        {/* form */}
        <form id="auth-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Field
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            autoComplete="email"
          />
          <Field
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete={isLogin ? 'current-password' : 'new-password'}
          />

          {/* error / success banners */}
          {displayError && (
            <div id="auth-error" className="badge-error px-4 py-3 rounded-lg text-sm leading-relaxed">
              {displayError}
            </div>
          )}
          {successMsg && (
            <div id="auth-success" className="badge-ok px-4 py-3 rounded-lg text-sm leading-relaxed">
              {successMsg}
            </div>
          )}

          <button
            id="btn-auth-submit"
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50
                       disabled:cursor-not-allowed transition-colors text-white font-semibold text-sm mt-1"
          >
            {loading ? 'Please wait…' : isLogin ? 'Sign in' : 'Create account'}
          </button>
        </form>

        {/* toggle */}
        <p className="text-center text-sm text-slate-400">
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            id="btn-toggle-mode"
            type="button"
            onClick={switchMode}
            className="text-brand-300 hover:text-brand-200 font-medium transition-colors"
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>

      <p className="mt-6 text-xs text-slate-600">
        PersonaPanel · AI-powered synthetic user testing
      </p>
    </div>
  )
}
