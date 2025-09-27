import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    console.log('🔄 Proxy request to stop bot')
    
    // Fai la richiesta al backend Flask
    const response = await fetch('http://localhost:5000/api/bot/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    console.log('📡 Flask bot stop response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask backend error for bot stop:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Flask backend error: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Bot stopped successfully:', data)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Bot stop proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Failed to stop bot',
        details: error.message 
      },
      { status: 500 }
    )
  }
}