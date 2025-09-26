'use client'

import Link from 'next/link'
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline'

const plans = [
  {
    name: 'Starter',
    price: '$29',
    period: '/month',
    description: 'Perfect for beginners getting started with automated trading',
    features: [
      '1 Trading Bot',
      '2 Active Strategies',
      'Basic Market Analysis',
      'Email Support',
      'Paper Trading Mode',
      'Basic Portfolio Tracking'
    ],
    limitations: [
      'No advanced strategies',
      'No custom indicators',
      'No API access'
    ],
    popular: false,
    ctaText: 'Start Free Trial'
  },
  {
    name: 'Professional',
    price: '$99',
    period: '/month',
    description: 'Advanced features for serious traders and professionals',
    features: [
      '5 Trading Bots',
      'Unlimited Strategies',
      'Advanced Market Analysis',
      'Priority Support',
      'Live Trading Mode',
      'Advanced Portfolio Analytics',
      'Custom Indicators',
      'Backtesting Engine',
      'Risk Management Tools',
      'Telegram Notifications'
    ],
    limitations: [
      'No white-label options',
      'No custom integrations'
    ],
    popular: true,
    ctaText: 'Start Free Trial'
  },
  {
    name: 'Enterprise',
    price: '$299',
    period: '/month',
    description: 'Complete solution for institutions and trading firms',
    features: [
      'Unlimited Trading Bots',
      'All Strategy Types',
      'AI-Powered Analysis',
      '24/7 Dedicated Support',
      'Multi-Exchange Support',
      'White-label Solution',
      'Custom API Integration',
      'Advanced Risk Controls',
      'Institutional Features',
      'Custom Development',
      'Team Management',
      'Compliance Tools'
    ],
    limitations: [],
    popular: false,
    ctaText: 'Contact Sales'
  }
]

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-dark">
      {/* Navigation */}
      <nav className="border-b border-dark-700/50 backdrop-blur-sm bg-dark-900/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-dark-300 hover:text-white transition-colors">
                ← Back to Home
              </Link>
            </div>
            
            <div className="flex items-center space-x-4">
              <Link href="/login" className="btn-outline">
                Sign In
              </Link>
              <Link href="/login" className="btn-primary">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl lg:text-5xl font-bold text-white mb-6">
            Choose Your Trading Plan
          </h1>
          <p className="text-xl text-dark-300 max-w-3xl mx-auto">
            Start with our free trial and scale your automated trading as you grow. 
            All plans include our core AI-powered trading algorithms.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`card relative ${
                plan.popular 
                  ? 'ring-2 ring-primary-500 transform scale-105' 
                  : 'hover-lift'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-gradient-trading text-white px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="p-8">
                {/* Plan Header */}
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                  <p className="text-dark-300 mb-4">{plan.description}</p>
                  
                  <div className="flex items-baseline justify-center">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-dark-400 ml-2">{plan.period}</span>
                  </div>
                </div>

                {/* CTA Button */}
                <button className={`w-full mb-8 ${
                  plan.popular ? 'btn-primary' : 'btn-outline'
                }`}>
                  {plan.ctaText}
                </button>

                {/* Features List */}
                <div className="space-y-4">
                  <h4 className="font-semibold text-white">What's included:</h4>
                  
                  {plan.features.map((feature, index) => (
                    <div key={index} className="flex items-start space-x-3">
                      <CheckIcon className="w-5 h-5 text-success-400 mt-0.5 flex-shrink-0" />
                      <span className="text-dark-300">{feature}</span>
                    </div>
                  ))}

                  {plan.limitations.length > 0 && (
                    <>
                      <h4 className="font-semibold text-dark-400 mt-6">Not included:</h4>
                      {plan.limitations.map((limitation, index) => (
                        <div key={index} className="flex items-start space-x-3">
                          <XMarkIcon className="w-5 h-5 text-dark-500 mt-0.5 flex-shrink-0" />
                          <span className="text-dark-500">{limitation}</span>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-20">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Frequently Asked Questions
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Can I change plans anytime?
                </h3>
                <p className="text-dark-300">
                  Yes, you can upgrade or downgrade your plan at any time. 
                  Changes will be prorated and reflected in your next billing cycle.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Is there a free trial?
                </h3>
                <p className="text-dark-300">
                  All plans come with a 14-day free trial. No credit card required to start.
                  You can test all features before committing.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  What exchanges are supported?
                </h3>
                <p className="text-dark-300">
                  We support major exchanges including Binance, Bybit, Coinbase Pro, 
                  and more. Enterprise plans include custom exchange integrations.
                </p>
              </div>
            </div>
            
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Is my data secure?
                </h3>
                <p className="text-dark-300">
                  Yes, we use bank-level encryption and never store your exchange API secrets. 
                  All data is encrypted and stored securely.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Can I cancel anytime?
                </h3>
                <p className="text-dark-300">
                  Absolutely. You can cancel your subscription at any time with no cancellation fees. 
                  Your access continues until the end of your billing period.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Do you offer custom solutions?
                </h3>
                <p className="text-dark-300">
                  Yes, our Enterprise plan includes custom development and integrations. 
                  Contact our sales team to discuss your specific requirements.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center mt-20">
          <div className="card max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold text-white mb-4">
              Ready to start automated trading?
            </h3>
            <p className="text-dark-300 mb-6">
              Join thousands of traders who trust our AI-powered platform to optimize their trading strategies.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/login" className="btn-primary">
                Start Free Trial
              </Link>
              <Link href="/contact-sales" className="btn-outline">
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}