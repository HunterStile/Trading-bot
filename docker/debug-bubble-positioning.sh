#!/bin/bash
# 🧪 Test comparativo: Locale vs Docker per debugging bolle e timer

echo "🧪 COMPARATIVE TEST: Local vs Docker Dashboard"
echo "=============================================="

# Function to test dashboard
test_dashboard() {
    local url=$1
    local name=$2
    
    echo ""
    echo "🔍 Testing $name ($url)"
    echo "------------------------"
    
    # Test basic response
    if curl -s "$url" > /dev/null; then
        echo "✅ Dashboard accessible"
    else
        echo "❌ Dashboard not accessible"
        return 1
    fi
    
    # Test debug API
    echo "📊 Debug API response:"
    curl -s "$url/api/debug" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Trades: {data.get(\"trades_count\", 0)}')
    print(f'  Price: ${data.get(\"current_price\", 0):,.2f}')
    print(f'  Symbol: {data.get(\"current_symbol\", \"N/A\")}')
    print(f'  Connection: {data.get(\"connection_active\", False)}')
    
    # Check stats structure
    all_stats = data.get('all_symbols_stats', {})
    if all_stats:
        for symbol, stats in all_stats.items():
            session_start = stats.get('session_start', 0)
            import time
            current_time = time.time()
            duration = int(current_time - session_start)
            print(f'  {symbol}: {stats.get(\"trades_count\", 0)} trades, running {duration}s')
    else:
        print('  ⚠️ No stats data found')
        
except Exception as e:
    print(f'  ❌ API Error: {e}')
"
}

# Test local dashboard (if running)
echo "1️⃣ TESTING LOCAL DASHBOARD"
test_dashboard "http://localhost:5006" "Local Python"

# Test Docker dashboard
echo ""
echo "2️⃣ TESTING DOCKER DASHBOARD" 
test_dashboard "http://localhost:15006" "Docker Container"

echo ""
echo "🔍 DEBUGGING COMMANDS"
echo "===================="
echo "To check Docker logs:"
echo "  docker-compose -f docker-compose.prod.yml logs --tail=50 dashboard-professional | grep -E '(Timer debug|Bubble order|Chart X range)'"
echo ""
echo "To check timezone in container:"
echo "  docker exec dashboard-professional date"
echo "  docker exec dashboard-professional timedatectl"
echo ""
echo "To check local timezone:"
echo "  date"
echo ""
echo "Browser Console Commands (F12):"
echo "  console.log('Local time:', new Date().toISOString())"
echo "  console.log('Timezone offset:', new Date().getTimezoneOffset())"
echo ""

echo "🎯 WHAT TO CHECK:"
echo "================="
echo "1. Timer shows actual duration (not 00:00:00)"
echo "2. Bubbles appear ON the candlesticks (not far right)"
echo "3. Timestamp synchronization between candles and bubbles"
echo "4. Console logs show correct X coordinates"