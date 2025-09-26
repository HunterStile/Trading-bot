import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    console.log('🔄 Proxy request to Flask backend for bot status')
    
    // Fai la richiesta al backend Flask
    const response = await fetch('http://localhost:5000/api/bot/status', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    console.log('📡 Flask response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask backend error:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Flask backend error: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Flask response data:', data)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask backend',
        details: error.message 
      },
      { status: 500 }
    )
  }
}