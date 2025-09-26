'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  ChartBarIcon,
  CogIcon,
  BellIcon,
  UserIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  PlayIcon,
  PauseIcon,
  EyeIcon
} from '@heroicons/react/24/outline'

export default function DashboardPage() {
  const [botStatus, setBotStatus] = useState({
    running: false,
    symbol: 'BTCUSDT',
    pnl: 12847.50,
    pnlPercentage: 24.3,
    winRate: 87.4,
    totalTrades: 152,
    activeStrategies: 3
  })

  const [recentTrades] = useState([
    { id: 1, symbol: 'BTCUSDT', side: 'BUY', price: 43250.00, quantity: 0.023, pnl: 145.50, time: '2 min ago' },
    { id: 2, symbol: 'ETHUSDT', side: 'SELL', price: 2680.50, quantity: 1.5, pnl: -23.40, time: '5 min ago' },
    { id: 3, symbol: 'AVAXUSDT', side: 'BUY', price: 35.80, quantity: 50, pnl: 87.20, time: '8 min ago' },
  ])

  const toggleBot = () => {
    setBotStatus(prev => ({ ...prev, running: !prev.running }))
  }

  return (
    <div className="min-h-screen bg-gradient-dark">
      {/* Navigation */}
      <nav className="border-b border-dark-700/50 backdrop-blur-sm bg-dark-900/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="w-8 h-8 bg-gradient-trading rounded-lg flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Trading Dashboard</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <button className="p-2 text-dark-300 hover:text-white transition-colors">
                <BellIcon className="w-5 h-5" />
              </button>
              <button className="p-2 text-dark-300 hover:text-white transition-colors">
                <CogIcon className="w-5 h-5" />
              </button>
              <button className="p-2 text-dark-300 hover:text-white transition-colors">
                <UserIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Welcome back, Trader</h1>
              <p className="text-dark-300">Monitor your automated trading strategies and performance</p>
            </div>
            
            <div className="mt-4 lg:mt-0 flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${botStatus.running ? 'bg-success-500 animate-pulse' : 'bg-danger-500'}`}></div>
                <span className={`text-sm font-medium ${botStatus.running ? 'text-success-400' : 'text-danger-400'}`}>
                  {botStatus.running ? 'Bot Active' : 'Bot Stopped'}
                </span>
              </div>
              
              <button 
                onClick={toggleBot}
                className={`flex items-center px-4 py-2 rounded-lg font-medium transition-all ${
                  botStatus.running 
                    ? 'bg-danger-600 hover:bg-danger-700 text-white' 
                    : 'bg-success-600 hover:bg-success-700 text-white'
                }`}
              >
                {botStatus.running ? (
                  <>
                    <PauseIcon className="w-4 h-4 mr-2" />
                    Stop Bot
                  </>
                ) : (
                  <>
                    <PlayIcon className="w-4 h-4 mr-2" />
                    Start Bot
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total P&L"
            value={`$${botStatus.pnl.toLocaleString()}`}
            change={`+${botStatus.pnlPercentage}%`}
            trend="up"
            subtitle="This month"
          />
          
          <StatsCard
            title="Win Rate"
            value={`${botStatus.winRate}%`}
            change={`${botStatus.totalTrades} trades`}
            trend="up"
            subtitle="All time"
          />
          
          <StatsCard
            title="Active Strategies"
            value={botStatus.activeStrategies.toString()}
            change="2 BTC, 1 ETH"
            trend="neutral"
            subtitle="Running now"
          />
          
          <StatsCard
            title="Portfolio Value"
            value="$52,340"
            change="+12.8%"
            trend="up"
            subtitle="24h change"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Trades */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Recent Trades</h2>
                <Link href="/trades" className="text-primary-400 hover:text-primary-300 text-sm font-medium">
                  View all
                </Link>
              </div>
              
              <div className="space-y-4">
                {recentTrades.map((trade) => (
                  <div key={trade.id} className="flex items-center justify-between p-4 bg-dark-800 rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className={`w-2 h-8 rounded-full ${trade.side === 'BUY' ? 'bg-success-500' : 'bg-danger-500'}`}></div>
                      
                      <div>
                        <div className="font-mono text-white font-medium">{trade.symbol}</div>
                        <div className="text-sm text-dark-400">{trade.time}</div>
                      </div>
                      
                      <div className="text-sm">
                        <div className={`font-medium ${trade.side === 'BUY' ? 'text-success-400' : 'text-danger-400'}`}>
                          {trade.side}
                        </div>
                        <div className="text-dark-400">{trade.quantity}</div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-white font-medium">${trade.price.toLocaleString()}</div>
                      <div className={`text-sm font-medium ${trade.pnl >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                        {trade.pnl >= 0 ? '+' : ''}${trade.pnl}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Actions & Strategy Status */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="card">
              <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
              
              <div className="space-y-3">
                <Link href="/strategies" className="block w-full btn-primary text-left">
                  <CogIcon className="w-4 h-4 inline mr-2" />
                  Configure Strategy
                </Link>
                
                <Link href="/backtest" className="block w-full btn-outline text-left">
                  <ChartBarIcon className="w-4 h-4 inline mr-2" />
                  Run Backtest
                </Link>
                
                <Link href="/analysis" className="block w-full btn-outline text-left">
                  <EyeIcon className="w-4 h-4 inline mr-2" />
                  Market Analysis
                </Link>
              </div>
            </div>

            {/* Active Strategies */}
            <div className="card">
              <h2 className="text-xl font-semibold text-white mb-4">Active Strategies</h2>
              
              <div className="space-y-3">
                <StrategyItem 
                  name="EMA Crossover"
                  symbol="BTCUSDT"
                  status="active"
                  pnl={+245.50}
                />
                
                <StrategyItem 
                  name="Momentum Scalp"
                  symbol="ETHUSDT"
                  status="active"
                  pnl={+87.20}
                />
                
                <StrategyItem 
                  name="Grid Trading"
                  symbol="AVAXUSDT"
                  status="paused"
                  pnl={-15.80}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatsCard({ 
  title, 
  value, 
  change, 
  trend, 
  subtitle 
}: {
  title: string
  value: string
  change: string
  trend: 'up' | 'down' | 'neutral'
  subtitle: string
}) {
  return (
    <div className="card hover-lift">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-dark-400">{title}</h3>
        {trend === 'up' && <ArrowTrendingUpIcon className="w-4 h-4 text-success-400" />}
        {trend === 'down' && <ArrowTrendingDownIcon className="w-4 h-4 text-danger-400" />}
      </div>
      
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      
      <div className="flex items-center justify-between">
        <span className={`text-sm font-medium ${
          trend === 'up' ? 'text-success-400' : 
          trend === 'down' ? 'text-danger-400' : 
          'text-dark-300'
        }`}>
          {change}
        </span>
        <span className="text-xs text-dark-400">{subtitle}</span>
      </div>
    </div>
  )
}

function StrategyItem({
  name,
  symbol,
  status,
  pnl
}: {
  name: string
  symbol: string
  status: 'active' | 'paused'
  pnl: number
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-dark-800 rounded-lg">
      <div className="flex items-center space-x-3">
        <div className={`w-2 h-2 rounded-full ${status === 'active' ? 'bg-success-500' : 'bg-warning-500'}`}></div>
        <div>
          <div className="text-white text-sm font-medium">{name}</div>
          <div className="text-xs text-dark-400 font-mono">{symbol}</div>
        </div>
      </div>
      
      <div className="text-right">
        <div className={`text-sm font-medium ${pnl >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
          {pnl >= 0 ? '+' : ''}${pnl}
        </div>
      </div>
    </div>
  )
}