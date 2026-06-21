import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0d0d1a] flex flex-col items-center justify-center p-6 text-center">
          <div className="glass-card p-8 max-w-md w-full border-red-500/30">
            <svg className="w-16 h-16 text-red-500 mx-auto mb-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
            <p className="text-slate-400 text-sm mb-6">
              An unexpected error caused the application to crash. 
              Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.href = '/'}
              className="px-6 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 transition-colors text-white font-medium text-sm w-full"
            >
              Reload Application
            </button>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <pre className="mt-6 text-left bg-black/50 p-4 rounded text-xs text-red-400 overflow-auto max-h-40">
                {this.state.error.toString()}
              </pre>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
