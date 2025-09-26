/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
  },
  images: {
    domains: ['cdn.jsdelivr.net', 'via.placeholder.com'],
  },
  env: {
    CUSTOM_KEY: 'trading-bot-saas',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:5000/api/:path*', // Flask backend
      },
    ]
  },
}

module.exports = nextConfig