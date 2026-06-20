import axios from 'axios'

const api = axios.create({
  // In dev, Vite proxies /api → http://localhost:8000
  // In prod, set VITE_API_BASE_URL in .env
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

export default api
