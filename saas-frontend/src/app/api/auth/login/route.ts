import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()
    
    console.log('🔄 Authentication request for:', email)
    
    // Fai la richiesta al backend Flask per l'autenticazione
    const response = await fetch('http://localhost:5000/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    
    console.log('📡 Flask auth response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask auth error:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Authentication failed: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Authentication successful for:', email)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Auth proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Authentication service unavailable',
        details: error.message 
      },
      { status: 500 }
    )
  }
}