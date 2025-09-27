import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '10'
    
    console.log('🔄 Proxy request for trades history, limit:', limit)
    
    // Fai la richiesta al backend Flask
    const response = await fetch(`http://localhost:5000/api/trades/history?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    console.log('📡 Flask trades response status:', response.status)
    
    if (!response.ok) {
      console.error('❌ Flask backend error for trades:', response.status, response.statusText)
      return NextResponse.json(
        { error: `Flask backend error: ${response.status}` },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    console.log('✅ Flask trades response data:', data)
    
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('❌ Trades proxy error:', error)
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask backend for trades',
        details: error.message 
      },
      { status: 500 }
    )
  }
}