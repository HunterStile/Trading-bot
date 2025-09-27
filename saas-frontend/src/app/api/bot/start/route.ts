import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    console.log('🔄 Proxy request to start bot')
    
    const body = await request.json().catch(() => ({}))
    
    // Fai la richiesta al backend Flask
    const response = await fetch('http://localhost:5000/api/bot/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    
    console.log('📡 Flask bot start response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask backend error for bot start:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Flask backend error: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Bot started successfully:', data)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Bot start proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Failed to start bot',
        details: error.message 
      },
      { status: 500 }
    )
  }
}