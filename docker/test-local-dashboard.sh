#!/bin/bash
# 🧪 Test locale per verificare il rendering delle bolle

echo "🧪 Testing Professional Dashboard locally..."
echo ""

# Stop existing processes
echo "1️⃣ Stopping existing Python processes..."
pkill -f "professional_dashboard.py" 2>/dev/null || true

# Start the dashboard in background
echo "2️⃣ Starting Professional Dashboard..."
cd ..
python3 professional_dashboard.py &
DASHBOARD_PID=$!

# Wait for startup
echo "3️⃣ Waiting for dashboard to start..."
sleep 5

# Test if dashboard is responding
echo "4️⃣ Testing dashboard response..."
if curl -s http://localhost:5006 > /dev/null; then
    echo "✅ Dashboard is responding on http://localhost:5006"
else
    echo "❌ Dashboard is not responding"
    kill $DASHBOARD_PID 2>/dev/null
    exit 1
fi

# Open in browser
echo "5️⃣ Opening dashboard in browser..."
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:5006
elif command -v open > /dev/null 2>&1; then
    open http://localhost:5006
else
    echo "Please open http://localhost:5006 in your browser manually"
fi

echo ""
echo "🔍 Test Instructions:"
echo "1. Open http://localhost:5006 in your browser"
echo "2. Wait for trades to appear"
echo "3. Check if bubble charts (🐋 large orders) appear correctly on the candlestick chart"
echo "4. Press Ctrl+C to stop the test"
echo ""
echo "📊 Dashboard PID: $DASHBOARD_PID"
echo "🛑 To stop: kill $DASHBOARD_PID"

# Wait for user input
read -p "Press Enter to stop the test..."

# Cleanup
echo "🧹 Stopping dashboard..."
kill $DASHBOARD_PID 2>/dev/null
echo "✅ Test completed!"