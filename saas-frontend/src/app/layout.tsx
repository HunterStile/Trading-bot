import './globals-test.css'
import { Inter } from 'next/font/google'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'TradingBot SaaS - AI-Powered Trading Platform',
  description: 'Professional trading automation with advanced AI strategies and real-time market analysis.',
  keywords: 'trading bot, cryptocurrency, AI trading, automated trading, SaaS',
  author: 'TradingBot Team',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}