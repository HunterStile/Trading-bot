import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()
    
    console.log('🔄 Registration request for:', email)
    
    // Fai la richiesta al backend Flask per la registrazione
    const response = await fetch('http://localhost:5000/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    
    console.log('📡 Flask registration response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask registration error:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Registration failed: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Registration successful for:', email)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Registration proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Registration service unavailable',
        details: error.message 
      },
      { status: 500 }
    )
  }
}