/**
 * Nav — shared top navigation bar for all authenticated pages.
 *
 * Props:
 *   title?    string   — page title shown in the center (optional)
 *   actions?  ReactNode — extra buttons/links to inject right of the logo area
 */
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const SparkleIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09z" />
  </svg>
)

export default function Nav({ actions }) {
  const { auth, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <nav className="flex items-center justify-between px-6 sm:px-8 py-4 border-b border-white/10 backdrop-blur-sm sticky top-0 z-30 bg-[#0d0d1a]/70">
      {/* Logo */}
      <Link
        to="/"
        className="flex items-center gap-2 font-bold text-lg tracking-tight text-white hover:text-brand-300 transition-colors"
      >
        <span className="w-7 h-7 rounded-lg bg-brand-600/40 flex items-center justify-center text-brand-300">
          <SparkleIcon />
        </span>
        PersonaPanel
      </Link>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {actions}

        {auth && (
          <>
            <Link
              to="/history"
              className="text-sm font-medium px-3 py-2 rounded-lg text-slate-300 hover:text-white transition-colors"
            >
              History
            </Link>
            <Link
              to="/new-test"
              className="hidden sm:inline-flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-lg
                         bg-brand-600 hover:bg-brand-500 transition-colors text-white shadow-lg shadow-brand-900/30"
            >
              + New Test
            </Link>
            <span className="text-xs text-slate-500 hidden md:block max-w-[140px] truncate">
              {auth.email}
            </span>
            <button
              id="btn-logout"
              onClick={() => { logout(); navigate('/login') }}
              className="text-sm font-medium px-3 py-2 rounded-lg border border-white/15
                         hover:border-white/30 transition-colors text-slate-300 hover:text-white"
            >
              Log out
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
