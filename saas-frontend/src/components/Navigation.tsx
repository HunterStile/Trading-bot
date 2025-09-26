'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  ChartBarIcon,
  Bars3Icon,
  XMarkIcon,
  BellIcon,
  CogIcon,
  UserIcon
} from '@heroicons/react/24/outline'
import { useState } from 'react'

interface NavigationProps {
  isAuthenticated?: boolean
  variant?: 'public' | 'dashboard'
}

export default function Navigation({ isAuthenticated = false, variant = 'public' }: NavigationProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  const publicLinks = [
    { href: '/', label: 'Home' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/features', label: 'Features' },
    { href: '/about', label: 'About' }
  ]

  const dashboardLinks = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/strategies', label: 'Strategies' },
    { href: '/backtest', label: 'Backtesting' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/trades', label: 'Trades' }
  ]

  const links = variant === 'dashboard' ? dashboardLinks : publicLinks

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === href
    }
    return pathname.startsWith(href)
  }

  return (
    <nav className="border-b border-dark-700/50 backdrop-blur-sm bg-dark-900/80 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link href={variant === 'dashboard' ? '/dashboard' : '/'} className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-trading rounded-lg flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white hidden sm:block">
                {variant === 'dashboard' ? 'Dashboard' : 'TradingBot AI'}
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  isActive(link.href)
                    ? 'text-primary-400'
                    : 'text-dark-300 hover:text-white'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right Side Actions */}
          <div className="flex items-center space-x-4">
            {variant === 'dashboard' && isAuthenticated ? (
              // Dashboard Actions
              <>
                <button className="p-2 text-dark-300 hover:text-white transition-colors">
                  <BellIcon className="w-5 h-5" />
                </button>
                <button className="p-2 text-dark-300 hover:text-white transition-colors">
                  <CogIcon className="w-5 h-5" />
                </button>
                <button className="p-2 text-dark-300 hover:text-white transition-colors">
                  <UserIcon className="w-5 h-5" />
                </button>
              </>
            ) : (
              // Public Actions
              <>
                {!isAuthenticated && (
                  <>
                    <Link 
                      href="/login" 
                      className="hidden sm:block text-dark-300 hover:text-white text-sm font-medium transition-colors"
                    >
                      Sign In
                    </Link>
                    <Link href="/register" className="btn-primary hidden sm:block">
                      Get Started
                    </Link>
                  </>
                )}
                {isAuthenticated && (
                  <Link href="/dashboard" className="btn-primary hidden sm:block">
                    Dashboard
                  </Link>
                )}
              </>
            )}

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 text-dark-300 hover:text-white transition-colors"
            >
              {isMobileMenuOpen ? (
                <XMarkIcon className="w-6 h-6" />
              ) : (
                <Bars3Icon className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-dark-700/50 py-4">
            <div className="space-y-2">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`block px-4 py-2 text-sm font-medium transition-colors ${
                    isActive(link.href)
                      ? 'text-primary-400 bg-primary-400/10'
                      : 'text-dark-300 hover:text-white hover:bg-dark-800'
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              
              {variant === 'public' && !isAuthenticated && (
                <div className="px-4 py-2 space-y-2">
                  <Link
                    href="/login"
                    className="block w-full btn-outline text-center"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/register"
                    className="block w-full btn-primary text-center"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}