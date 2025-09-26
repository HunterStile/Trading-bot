'use client'

import { useState } from 'react'

export default function APITestPage() {
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const testAPI = async () => {
    setLoading(true)
    try {
      console.log('🧪 Testing API connection...')
      
      const response = await fetch('/api/bot/status')
      
      console.log('📡 Response status:', response.status)
      console.log('📡 Response ok:', response.ok)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ API Response:', data)
      
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      console.error('❌ API Error:', error)
      setResult(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">API Test</h1>
        
        <div className="bg-white rounded-lg shadow p-6">
          <button
            onClick={testAPI}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Testing...' : 'Test API'}
          </button>
          
          {result && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold mb-2">Result:</h3>
              <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
                {result}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}