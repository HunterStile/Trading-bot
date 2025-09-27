import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('Authorization')
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }
    
    console.log('🔄 Get user config request')
    
    // Proxy la richiesta al backend Flask
    const response = await fetch('http://localhost:5000/api/user/config', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader
      },
    })
    
    console.log('📡 Flask user config response status:', response.status)
    
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
    
  } catch (error) {
    console.error('❌ User config proxy error:', error)
    return NextResponse.json(
      { error: 'User config service unavailable' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get('Authorization')
    const configData = await request.json()
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }
    
    console.log('🔄 Update user config request')
    
    // Proxy la richiesta al backend Flask
    const response = await fetch('http://localhost:5000/api/user/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader
      },
      body: JSON.stringify(configData)
    })
    
    console.log('📡 Flask update config response status:', response.status)
    
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
    
  } catch (error) {
    console.error('❌ Update config proxy error:', error)
    return NextResponse.json(
      { error: 'Update config service unavailable' },
      { status: 500 }
    )
  }
}