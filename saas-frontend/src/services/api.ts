/**
 * API Service - usando proxy Next.js per evitare problemi CORS
 */

const API_BASE_URL = '/api/proxy'

// Helper per gestire le risposte API
const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Network error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  return response.json()
}

// Bot API
export const botAPI = {
  getStatus: async () => {
    const response = await fetch('/api/bot/status')
    return handleResponse(response)
  },
  
  start: async (params = {}) => {
    const response = await fetch('/api/bot/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    })
    return handleResponse(response)
  },
  
  stop: async () => {
    const response = await fetch('/api/bot/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    return handleResponse(response)
  },
}

// Trades API (semplificato)
export const tradesAPI = {
  getHistory: async (limit = 10) => {
    const response = await fetch(`/api/trades/history?limit=${limit}`)
    return handleResponse(response)
  },
}

// Export default
const api = {
  bot: botAPI,
  trades: tradesAPI,
}

export default api