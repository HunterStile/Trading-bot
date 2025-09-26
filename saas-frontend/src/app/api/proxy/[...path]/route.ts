import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    // Costruisci il path dell'API dal parametro dinamico
    const apiPath = params.path ? params.path.join('/') : ''
    const { searchParams } = new URL(request.url)
    
    // Costruisci l'URL del backend Flask
    const backendUrl = `http://localhost:5000/api/${apiPath}?${searchParams.toString()}`
    
    console.log('🔄 Proxy GET request to:', backendUrl)
    
    // Fai la richiesta al backend Flask
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    const data = await response.json()
    
    console.log('✅ Backend response:', response.status)
    
    return NextResponse.json(data, { status: response.status })
    
  } catch (error) {
    console.error('❌ Proxy error:', error)
    return NextResponse.json(
      { error: 'Proxy request failed' },
      { status: 500 }
    )
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const apiPath = params.path ? params.path.join('/') : ''
    const { searchParams } = new URL(request.url)
    const body = await request.json()
    
    const backendUrl = `http://localhost:5000/api/${apiPath}?${searchParams.toString()}`
    
    console.log('🔄 Proxy POST request to:', backendUrl)
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    
    const data = await response.json()
    
    return NextResponse.json(data, { status: response.status })
    
  } catch (error) {
    console.error('❌ Proxy POST error:', error)
    return NextResponse.json(
      { error: 'Proxy POST request failed' },
      { status: 500 }
    )
  }
}