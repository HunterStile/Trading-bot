'use client'

import { useState } from 'react'
import Link from 'next/link'
import { 
  PlusIcon,
  PlayIcon,
  PauseIcon,
  CogIcon,
  ChartBarIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'

interface Strategy {
  id: number
  name: string
  symbol: string
  status: 'active' | 'paused' | 'stopped'
  type: string
  pnl: number
  winRate: number
  trades: number
  lastTrade: string
  configuration: {
    timeframe: string
    riskPercent: number
    stopLoss: number
    takeProfit: number
  }
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([
    {
      id: 1,
      name: 'EMA Crossover BTC',
      symbol: 'BTCUSDT',
      status: 'active',
      type: 'EMA Cross',
      pnl: 1247.50,
      winRate: 78.5,
      trades: 45,
      lastTrade: '2 min ago',
      configuration: {
        timeframe: '15m',
        riskPercent: 2.5,
        stopLoss: 1.2,
        takeProfit: 2.4
      }
    },
    {
      id: 2,
      name: 'Momentum ETH',
      symbol: 'ETHUSDT',
      status: 'active',
      type: 'Momentum',
      pnl: 567.80,
      winRate: 82.1,
      trades: 28,
      lastTrade: '5 min ago',
      configuration: {
        timeframe: '5m',
        riskPercent: 1.5,
        stopLoss: 0.8,
        takeProfit: 1.6
      }
    },
    {
      id: 3,
      name: 'Grid AVAX',
      symbol: 'AVAXUSDT',
      status: 'paused',
      type: 'Grid Trading',
      pnl: -45.20,
      winRate: 65.3,
      trades: 67,
      lastTrade: '1h ago',
      configuration: {
        timeframe: '1m',
        riskPercent: 1.0,
        stopLoss: 2.0,
        takeProfit: 1.0
      }
    }
  ])

  const toggleStrategy = (id: number) => {
    setStrategies(prev => prev.map(strategy => 
      strategy.id === id 
        ? { 
            ...strategy, 
            status: strategy.status === 'active' ? 'paused' : 'active' 
          }
        : strategy
    ))
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-success-400 bg-success-400/10'
      case 'paused': return 'text-warning-400 bg-warning-400/10'
      case 'stopped': return 'text-danger-400 bg-danger-400/10'
      default: return 'text-dark-400 bg-dark-400/10'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-dark">
      {/* Navigation */}
      <nav className="border-b border-dark-700/50 backdrop-blur-sm bg-dark-900/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="text-dark-300 hover:text-white transition-colors">
                ← Back to Dashboard
              </Link>
            </div>
            
            <div className="flex items-center space-x-4">
              <button className="btn-primary">
                <PlusIcon className="w-4 h-4 mr-2" />
                New Strategy
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Trading Strategies</h1>
          <p className="text-dark-300">Manage and monitor your automated trading strategies</p>
        </div>

        {/* Strategy Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="text-2xl font-bold text-white">3</div>
            <div className="text-sm text-dark-400">Total Strategies</div>
          </div>
          
          <div className="card">
            <div className="text-2xl font-bold text-success-400">2</div>
            <div className="text-sm text-dark-400">Active</div>
          </div>
          
          <div className="card">
            <div className="text-2xl font-bold text-white">75.8%</div>
            <div className="text-sm text-dark-400">Avg Win Rate</div>
          </div>
          
          <div className="card">
            <div className="text-2xl font-bold text-success-400">+$1,770</div>
            <div className="text-sm text-dark-400">Total P&L</div>
          </div>
        </div>

        {/* Strategies List */}
        <div className="space-y-6">
          {strategies.map((strategy) => (
            <div key={strategy.id} className="card hover-lift">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                {/* Strategy Info */}
                <div className="flex-1">
                  <div className="flex items-center space-x-4 mb-4 lg:mb-0">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-xl font-semibold text-white">{strategy.name}</h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(strategy.status)}`}>
                          {strategy.status.toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-6 text-sm text-dark-300">
                        <span className="font-mono">{strategy.symbol}</span>
                        <span>{strategy.type}</span>
                        <span className="flex items-center">
                          <ClockIcon className="w-4 h-4 mr-1" />
                          {strategy.configuration.timeframe}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Strategy Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-4 lg:mb-0 lg:mx-8">
                  <div className="text-center">
                    <div className={`text-lg font-bold ${strategy.pnl >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                      {strategy.pnl >= 0 ? '+' : ''}${strategy.pnl}
                    </div>
                    <div className="text-xs text-dark-400">P&L</div>
                  </div>
                  
                  <div className="text-center">
                    <div className="text-lg font-bold text-white">{strategy.winRate}%</div>
                    <div className="text-xs text-dark-400">Win Rate</div>
                  </div>
                  
                  <div className="text-center">
                    <div className="text-lg font-bold text-white">{strategy.trades}</div>
                    <div className="text-xs text-dark-400">Trades</div>
                  </div>
                  
                  <div className="text-center">
                    <div className="text-lg font-bold text-primary-400">{strategy.configuration.riskPercent}%</div>
                    <div className="text-xs text-dark-400">Risk</div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => toggleStrategy(strategy.id)}
                    className={`flex items-center px-4 py-2 rounded-lg font-medium transition-all ${
                      strategy.status === 'active'
                        ? 'bg-warning-600 hover:bg-warning-700 text-white'
                        : 'bg-success-600 hover:bg-success-700 text-white'
                    }`}
                  >
                    {strategy.status === 'active' ? (
                      <>
                        <PauseIcon className="w-4 h-4 mr-2" />
                        Pause
                      </>
                    ) : (
                      <>
                        <PlayIcon className="w-4 h-4 mr-2" />
                        Start
                      </>
                    )}
                  </button>
                  
                  <button className="p-2 text-dark-300 hover:text-white transition-colors">
                    <CogIcon className="w-5 h-5" />
                  </button>
                  
                  <button className="p-2 text-dark-300 hover:text-white transition-colors">
                    <ChartBarIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Strategy Configuration Details */}
              <div className="mt-4 pt-4 border-t border-dark-700">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-dark-400">Stop Loss:</span>
                    <span className="ml-2 text-danger-400 font-medium">{strategy.configuration.stopLoss}%</span>
                  </div>
                  
                  <div>
                    <span className="text-dark-400">Take Profit:</span>
                    <span className="ml-2 text-success-400 font-medium">{strategy.configuration.takeProfit}%</span>
                  </div>
                  
                  <div>
                    <span className="text-dark-400">Last Trade:</span>
                    <span className="ml-2 text-white">{strategy.lastTrade}</span>
                  </div>
                  
                  <div>
                    <span className="text-dark-400">Risk per Trade:</span>
                    <span className="ml-2 text-primary-400 font-medium">{strategy.configuration.riskPercent}%</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {strategies.length === 0 && (
          <div className="text-center py-12">
            <ArrowPathIcon className="w-16 h-16 text-dark-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No strategies yet</h3>
            <p className="text-dark-300 mb-6">Create your first automated trading strategy to get started</p>
            <button className="btn-primary">
              <PlusIcon className="w-4 h-4 mr-2" />
              Create Strategy
            </button>
          </div>
        )}
      </div>
    </div>
  )
}