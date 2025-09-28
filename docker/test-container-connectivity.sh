#!/bin/bash
# 🧪 Test connettività WebSocket da dentro il container Docker

echo "🧪 Testing WebSocket connectivity from inside Docker container"
echo "============================================================"

# Check if running inside container
if [ -f /.dockerenv ]; then
    echo "✅ Running inside Docker container"
else
    echo "❌ Not running inside Docker container"
    echo "This script should be run from inside the dashboard-professional container"
    exit 1
fi

echo ""

# Test 1: Basic internet connectivity
echo "1️⃣ Testing basic internet connectivity..."
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ Internet: OK"
else
    echo "❌ Internet: FAILED"
fi

echo ""

# Test 2: DNS resolution
echo "2️⃣ Testing DNS resolution..."
if nslookup stream.bybit.com > /dev/null 2>&1; then
    echo "✅ DNS: OK"
    nslookup stream.bybit.com | grep -A 1 "Name:"
else
    echo "❌ DNS: FAILED"
fi

echo ""

# Test 3: HTTPS connectivity to Bybit API
echo "3️⃣ Testing HTTPS API connectivity..."
if curl -s --connect-timeout 10 https://api.bybit.com/v5/market/time | grep -q "timeSecond"; then
    echo "✅ HTTPS API: OK"
else
    echo "❌ HTTPS API: FAILED"
fi

echo ""

# Test 4: WebSocket port connectivity
echo "4️⃣ Testing WebSocket port (443)..."
if timeout 5 bash -c '</dev/tcp/stream.bybit.com/443' > /dev/null 2>&1; then
    echo "✅ Port 443: OPEN"
else
    echo "❌ Port 443: BLOCKED"
fi

echo ""

# Test 5: Python WebSocket test
echo "5️⃣ Testing Python WebSocket connection..."
python3 << 'EOF'
import asyncio
import websockets
import sys

async def test_ws():
    urls = [
        "wss://stream.bybit.com/v5/public/linear",
        "wss://stream-testnet.bybit.com/v5/public/linear"
    ]
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"Testing URL {i}: {url}")
            async with websockets.connect(url, ping_interval=20, ping_timeout=10, open_timeout=5) as websocket:
                print(f"✅ WebSocket {i}: CONNECTION SUCCESS")
                
                # Test subscription
                sub_msg = '{"op":"subscribe","args":["publicTrade.BTCUSDT"]}'
                await websocket.send(sub_msg)
                print(f"✅ WebSocket {i}: SUBSCRIPTION SENT")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"✅ WebSocket {i}: RESPONSE OK: {response[:100]}...")
                    return True
                except asyncio.TimeoutError:
                    print(f"⚠️ WebSocket {i}: No response (but connection works)")
                    return True
                    
        except Exception as e:
            print(f"❌ WebSocket {i}: FAILED - {e}")
            
    print("❌ All WebSocket tests failed")
    return False

# Run test
success = asyncio.run(test_ws())
sys.exit(0 if success else 1)
EOF

WS_RESULT=$?

echo ""

# Summary
echo "📊 CONNECTIVITY TEST SUMMARY"
echo "============================"
if [ $WS_RESULT -eq 0 ]; then
    echo "✅ WebSocket connectivity: WORKING"
    echo "🎉 Container can connect to Bybit!"
else
    echo "❌ WebSocket connectivity: FAILED"
    echo "🔧 Possible solutions:"
    echo "   1. Check Docker network configuration"
    echo "   2. Verify firewall settings on host"
    echo "   3. Check if corporate proxy/firewall blocks WebSocket"
    echo "   4. Try using host networking: --network=host"
fi

echo ""
echo "💡 To run this test:"
echo "docker exec -it dashboard-professional bash"
echo "chmod +x /app/test-container-connectivity.sh"
echo "/app/test-container-connectivity.sh"