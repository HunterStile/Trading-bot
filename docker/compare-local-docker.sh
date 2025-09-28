#!/bin/bash
# 🔍 Confronto Dashboard Locale vs Docker

echo "🔍 Professional Dashboard: Local vs Docker Comparison"
echo "===================================================="
echo ""

# Test 1: Local Dashboard
echo "1️⃣ TESTING LOCAL DASHBOARD"
echo "-------------------------"
cd ..
echo "Starting local dashboard..."
python3 professional_dashboard.py &
LOCAL_PID=$!
sleep 5

if curl -s http://localhost:5006 > /dev/null; then
    echo "✅ Local dashboard: WORKING (http://localhost:5006)"
    LOCAL_STATUS="OK"
else
    echo "❌ Local dashboard: NOT WORKING"
    LOCAL_STATUS="FAILED"
fi

# Stop local
kill $LOCAL_PID 2>/dev/null
sleep 2

echo ""

# Test 2: Docker Dashboard  
echo "2️⃣ TESTING DOCKER DASHBOARD"
echo "----------------------------"
cd docker

# Build and start Docker version
echo "Building Docker image..."
docker-compose -f docker-compose.prod.yml build dashboard-professional --no-cache -q

echo "Starting Docker dashboard..."
docker-compose -f docker-compose.prod.yml up -d dashboard-professional

sleep 10

if curl -s http://localhost:15006 > /dev/null; then
    echo "✅ Docker dashboard: WORKING (http://localhost:15006)"
    DOCKER_STATUS="OK"
else
    echo "❌ Docker dashboard: NOT WORKING"
    DOCKER_STATUS="FAILED"
fi

echo ""

# Test 3: JavaScript Console Logs
echo "3️⃣ CHECKING JAVASCRIPT ERRORS"
echo "------------------------------"
echo "📋 Manual checks needed:"
echo ""
echo "🌐 Local Dashboard:  http://localhost:5006"
echo "🐳 Docker Dashboard: http://localhost:15006"
echo ""
echo "In browser console (F12), look for:"
echo "  ✅ 'Plotly loaded successfully'"
echo "  ✅ 'Chart initialized successfully'"  
echo "  ✅ 'Bubble added successfully'"
echo "  ❌ Any JavaScript errors"
echo ""

# Results Summary
echo "📊 COMPARISON RESULTS"
echo "===================="
echo "Local Dashboard:  $LOCAL_STATUS"
echo "Docker Dashboard: $DOCKER_STATUS"
echo ""

if [ "$LOCAL_STATUS" == "OK" ] && [ "$DOCKER_STATUS" == "FAILED" ]; then
    echo "🔍 DIAGNOSIS: Docker-specific issue detected!"
    echo ""
    echo "Possible causes:"
    echo "1. Missing JavaScript dependencies in Docker"
    echo "2. Plotly.js loading issues in container"
    echo "3. Network/CDN access problems from container"
    echo "4. Browser compatibility issues"
    echo ""
    echo "🛠️ Solutions to try:"
    echo "1. Check Docker container logs:"
    echo "   docker-compose -f docker-compose.prod.yml logs dashboard-professional"
    echo ""
    echo "2. Test browser console on both dashboards"
    echo ""
    echo "3. Compare network requests (F12 > Network tab)"
elif [ "$LOCAL_STATUS" == "OK" ] && [ "$DOCKER_STATUS" == "OK" ]; then
    echo "✅ Both dashboards working!"
    echo "Issue might be browser-specific or intermittent."
else
    echo "❌ Both dashboards having issues - check code/dependencies"
fi

echo ""
echo "🛑 To stop Docker dashboard:"
echo "docker-compose -f docker-compose.prod.yml down"
echo ""

read -p "Press Enter to cleanup and exit..."

# Cleanup
docker-compose -f docker-compose.prod.yml down 2>/dev/null
echo "✅ Cleanup completed!"