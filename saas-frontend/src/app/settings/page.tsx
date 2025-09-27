'use client'

import { useState, useEffect } from 'react'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'

export default function SettingsPage() {
  const [config, setConfig] = useState({
    bybitApiKey: '',
    bybitSecretKey: '',
    telegramBotToken: '',
    telegramChatId: '',
    tradingStrategy: 'ema_crossover',
    riskPercentage: 2.0,
  })
  
  const [showSecrets, setShowSecrets] = useState({
    apiKey: false,
    secretKey: false,
    botToken: false
  })
  
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadUserConfig()
  }, [])

  const loadUserConfig = async () => {
    try {
      const response = await fetch('/api/user/config', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      })
      const data = await response.json()
      
      if (data.success) {
        setConfig(data.config)
      }
    } catch (err) {
      console.error('Errore caricamento configurazione:', err)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    setMessage('')

    try {
      const response = await fetch('/api/user/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify(config)
      })

      const data = await response.json()
      
      if (data.success) {
        setMessage('✅ Configurazione salvata con successo!')
      } else {
        setMessage('❌ Errore nel salvataggio: ' + data.error)
      }
    } catch (err) {
      setMessage('❌ Errore di connessione')
    } finally {
      setSaving(false)
    }
  }

  const testTelegramBot = async () => {
    try {
      const response = await fetch('/api/user/test-telegram', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      })

      const data = await response.json()
      
      if (data.success) {
        setMessage('✅ Bot Telegram testato con successo!')
      } else {
        setMessage('❌ Errore test Telegram: ' + data.error)
      }
    } catch (err) {
      setMessage('❌ Errore test Telegram')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">⚙️ Configurazione Account</h1>
        
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          
          {/* Bybit API Configuration */}
          <div className="border-b pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">🔑 API Keys Bybit</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <div className="relative">
                  <input
                    type={showSecrets.apiKey ? 'text' : 'password'}
                    value={config.bybitApiKey}
                    onChange={(e) => setConfig({...config, bybitApiKey: e.target.value})}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Inserisci la tua API Key Bybit"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecrets({...showSecrets, apiKey: !showSecrets.apiKey})}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showSecrets.apiKey ? (
                      <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                    ) : (
                      <EyeIcon className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Secret Key
                </label>
                <div className="relative">
                  <input
                    type={showSecrets.secretKey ? 'text' : 'password'}
                    value={config.bybitSecretKey}
                    onChange={(e) => setConfig({...config, bybitSecretKey: e.target.value})}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Inserisci la tua Secret Key Bybit"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecrets({...showSecrets, secretKey: !showSecrets.secretKey})}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showSecrets.secretKey ? (
                      <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                    ) : (
                      <EyeIcon className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Telegram Bot Configuration */}
          <div className="border-b pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">📱 Bot Telegram</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Token Bot Telegram
                </label>
                <div className="relative">
                  <input
                    type={showSecrets.botToken ? 'text' : 'password'}
                    value={config.telegramBotToken}
                    onChange={(e) => setConfig({...config, telegramBotToken: e.target.value})}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Inserisci il token del tuo bot Telegram"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecrets({...showSecrets, botToken: !showSecrets.botToken})}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showSecrets.botToken ? (
                      <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                    ) : (
                      <EyeIcon className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Chat ID Telegram
                </label>
                <input
                  type="text"
                  value={config.telegramChatId}
                  onChange={(e) => setConfig({...config, telegramChatId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Inserisci il tuo Chat ID Telegram"
                />
              </div>

              <button
                onClick={testTelegramBot}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                🧪 Testa Bot Telegram
              </button>
            </div>
          </div>

          {/* Trading Strategy Configuration */}
          <div className="border-b pb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">📊 Strategia Trading</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Strategia
                </label>
                <select
                  value={config.tradingStrategy}
                  onChange={(e) => setConfig({...config, tradingStrategy: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ema_crossover">EMA Crossover</option>
                  <option value="trend_following">Trend Following</option>
                  <option value="scalping">Scalping</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Risk Management (% del capitale)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  value={config.riskPercentage}
                  onChange={(e) => setConfig({...config, riskPercentage: parseFloat(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-between items-center">
            <div>
              {message && (
                <div className={`text-sm ${message.includes('✅') ? 'text-green-600' : 'text-red-600'}`}>
                  {message}
                </div>
              )}
            </div>
            
            <button
              onClick={saveConfig}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {saving ? 'Salvataggio...' : '💾 Salva Configurazione'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}