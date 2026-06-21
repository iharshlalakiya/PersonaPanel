import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

/** Standard API client — 10 s timeout for quick endpoints */
const api = axios.create({
  baseURL: BASE,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Long-timeout client for the pipeline endpoint (/api/test/run).
 * The full capture → 5 personas → synthesis → persist pipeline
 * can take 40-70 s; we give it a comfortable 3-minute ceiling.
 */
export const longApi = axios.create({
  baseURL: BASE,
  timeout: 180_000,
  headers: { 'Content-Type': 'application/json' },
})

export default api
