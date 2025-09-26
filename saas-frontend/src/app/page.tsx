'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Navigation from '../components/Navigation'
import { 
  ChartBarIcon, 
  RocketLaunchIcon, 
  ShieldCheckIcon, 
  CpuChipIcon,
  ArrowRightIcon,
  PlayIcon
} from '@heroicons/react/24/outline'

export default function HomePage() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  return (
    <div className="min-h-screen bg-gray-900">
      <Navigation variant="public" />

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <div className="animate-fade-in">
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              <span className="text-gradient">AI-Powered Trading</span>
              <br />
              <span className="text-white">Made Simple</span>
            </h1>
            
            <p className="text-xl text-dark-300 mb-8 max-w-3xl mx-auto">
              Automate your cryptocurrency trading with advanced AI strategies, 
              real-time market analysis, and professional-grade risk management tools.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link href="/register" className="btn-primary text-lg px-8 py-3">
                Start Free Trial
                <ArrowRightIcon className="w-5 h-5 ml-2 inline" />
              </Link>
              
              <button className="flex items-center text-white hover:text-primary-400 transition-colors">
                <PlayIcon className="w-5 h-5 mr-2" />
                Watch Demo
              </button>
            </div>
          </div>
          
          {/* Hero Dashboard Preview */}
          <div className="mt-16 animate-slide-up">
            <div className="card-trading max-w-4xl mx-auto">
              <div className="bg-dark-900 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Live Trading Dashboard</h3>
                  <div className="flex items-center space-x-2">
                    <div className="status-online"></div>
                    <span className="text-sm text-success-400">Connected</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-dark-800 rounded-lg p-4">
                    <div className="text-sm text-dark-400">Total P&L</div>
                    <div className="text-2xl font-bold price-up">+$12,847.50</div>
                    <div className="text-sm text-success-400">+24.3% this month</div>
                  </div>
                  
                  <div className="bg-dark-800 rounded-lg p-4">
                    <div className="text-sm text-dark-400">Active Strategies</div>
                    <div className="text-2xl font-bold text-white">3</div>
                    <div className="text-sm text-dark-400">2 BTC, 1 ETH</div>
                  </div>
                  
                  <div className="bg-dark-800 rounded-lg p-4">
                    <div className="text-sm text-dark-400">Win Rate</div>
                    <div className="text-2xl font-bold text-white">87.4%</div>
                    <div className="text-sm text-success-400">152 trades</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Powerful Features for Every Trader
            </h2>
            <p className="text-xl text-dark-300 max-w-2xl mx-auto">
              From beginners to professionals, our platform provides everything you need 
              to succeed in cryptocurrency trading.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <FeatureCard
              icon={<CpuChipIcon className="w-8 h-8" />}
              title="AI Strategies"
              description="Advanced machine learning algorithms analyze market patterns and execute optimal trades."
            />
            
            <FeatureCard
              icon={<ChartBarIcon className="w-8 h-8" />}
              title="Real-time Analysis"
              description="Multi-timeframe technical analysis with EMA crossovers and momentum indicators."
            />
            
            <FeatureCard
              icon={<ShieldCheckIcon className="w-8 h-8" />}
              title="Risk Management"
              description="Automated stop-losses, position sizing, and portfolio risk controls."
            />
            
            <FeatureCard
              icon={<RocketLaunchIcon className="w-8 h-8" />}
              title="High Performance"
              description="Lightning-fast execution with 99.9% uptime and institutional-grade infrastructure."
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-dark-900/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">$50M+</div>
              <div className="text-dark-300">Total Volume Traded</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">10K+</div>
              <div className="text-dark-300">Active Users</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">89.7%</div>
              <div className="text-dark-300">Average Win Rate</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">24/7</div>
              <div className="text-dark-300">Market Monitoring</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Ready to Start Trading?
          </h2>
          <p className="text-xl text-dark-300 mb-8">
            Join thousands of traders who trust our AI-powered platform for their success.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/register" className="btn-primary text-lg px-8 py-3">
              Start Free Trial
            </Link>
            <Link href="/pricing" className="btn-outline text-lg px-8 py-3">
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="w-6 h-6 bg-gradient-trading rounded"></div>
              <span className="text-lg font-semibold text-white">TradingBot SaaS</span>
            </div>
            
            <div className="text-dark-400 text-sm">
              © 2025 TradingBot SaaS. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="card hover-lift">
      <div className="text-primary-400 mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-dark-300">{description}</p>
    </div>
  )
}