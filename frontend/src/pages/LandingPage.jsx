import { Link } from 'react-router-dom'
import Nav from '../components/Nav.jsx'

export default function LandingPage() {
  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      <Nav actions={
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="text-sm font-medium px-4 py-2 rounded-lg text-slate-300 hover:text-white transition-colors"
          >
            Log In
          </Link>
          <Link
            to="/login"
            className="text-sm font-medium px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 transition-colors text-white shadow-lg shadow-brand-900/30"
          >
            Get Started
          </Link>
        </div>
      } />

      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-8 py-20 max-w-4xl mx-auto">
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-600/20 border border-brand-500/30 text-brand-300 text-sm font-medium">
          ✦ Synthetic User Testing
        </span>

        <h1 className="text-5xl sm:text-7xl font-extrabold text-white leading-tight">
          Test your product with{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-300 to-purple-400">
            AI Personas
          </span>
        </h1>

        <p className="text-xl text-slate-400 leading-relaxed max-w-2xl">
          PersonaPanel generates diverse synthetic users, runs them through your landing page,
          and surfaces rich qualitative insights — all before you talk to a single real customer.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mt-6">
          <Link
            to="/login"
            className="px-8 py-3.5 rounded-xl bg-white text-slate-900 hover:bg-slate-200 transition-colors font-bold text-lg shadow-xl shadow-white/10"
          >
            Start Testing for Free
          </Link>
          <a
            href="https://github.com/iharshlalakiya/PersonaPanel"
            target="_blank"
            rel="noreferrer"
            className="px-8 py-3.5 rounded-xl border-2 border-white/20 hover:border-white/40 transition-colors text-white font-bold text-lg flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            View on GitHub
          </a>
        </div>
      </main>
      
      {/* Footer-like element */}
      <div className="pb-12 text-center text-slate-500 text-sm">
        <p>Built as an AI Agent project demo.</p>
      </div>
    </div>
  )
}
