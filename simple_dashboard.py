"""
DASHBOARD SEMPLIFICATO - Versione che funziona garantita
"""
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import asyncio
import websockets
import json
import time
import threading
import sys
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class SimpleDashboard:
    def __init__(self):
        self.trades_count = 0
        self.large_orders_count = 0
        self.current_price = 0.0
        self.recent_trades = []
        self.large_orders = []
        self.connection_active = False
        
        # WebSocket
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws_thread = None
        
    def start_websocket(self):
        if self.ws_thread is None or not self.ws_thread.is_alive():
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            print("🔴 WebSocket started")
    
    def _run_websocket(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._websocket_loop())
    
    async def _websocket_loop(self):
        while True:
            try:
                print("🔌 Connecting to Bybit...")
                async with websockets.connect(self.ws_url) as websocket:
                    self.connection_active = True
                    
                    await websocket.send(json.dumps({
                        "op": "subscribe",
                        "args": ["publicTrade.BTCUSDT"]
                    }))
                    print("📡 Subscribed to BTCUSDT")
                    
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                self.connection_active = False
                await asyncio.sleep(5)
    
    async def _handle_message(self, message):
        try:
            data = json.loads(message)
            
            if "topic" in data and "publicTrade" in data["topic"]:
                for trade_data in data["data"]:
                    price = float(trade_data["p"])
                    volume = float(trade_data["v"])
                    side = 'buy' if trade_data["S"] == "Buy" else 'sell'
                    
                    self.trades_count += 1
                    self.current_price = price
                    
                    # Add to recent trades
                    trade_info = {
                        'price': price,
                        'volume': volume,
                        'side': side,
                        'time': time.strftime('%H:%M:%S')
                    }
                    
                    self.recent_trades.append(trade_info)
                    if len(self.recent_trades) > 100:
                        self.recent_trades = self.recent_trades[-100:]
                    
                    # Check large order
                    if volume >= 2.0:
                        self._handle_large_order(trade_info)
                    
                    # Emit update every 5 trades
                    if self.trades_count % 5 == 0:
                        self._emit_update()
                        
        except Exception as e:
            print(f"❌ Message error: {e}")
    
    def _handle_large_order(self, trade_info):
        large_order = {
            'side': trade_info['side'],
            'price': trade_info['price'],
            'volume': trade_info['volume'],
            'value': trade_info['price'] * trade_info['volume'],
            'time': trade_info['time']
        }
        
        self.large_orders.append(large_order)
        self.large_orders_count += 1
        
        if len(self.large_orders) > 20:
            self.large_orders = self.large_orders[-20:]
        
        # Print to console
        side_emoji = "🟢" if trade_info['side'] == 'buy' else "🔴"
        print(f"{side_emoji} Large: {trade_info['side']} {trade_info['volume']:.2f} @ ${trade_info['price']:,.2f}")
        
        # Emit to frontend
        socketio.emit('large_order', large_order)
    
    def _emit_update(self):
        update_data = {
            'trades_count': self.trades_count,
            'large_orders_count': self.large_orders_count,
            'current_price': self.current_price,
            'connection_active': self.connection_active
        }
        
        socketio.emit('stats_update', update_data)

# Global dashboard
dashboard = SimpleDashboard()

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Simple Live Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            background: #1a1a1a; 
            color: white; 
            font-family: Arial, sans-serif; 
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            border-bottom: 2px solid #333; 
            padding-bottom: 20px; 
        }
        .stats { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .stat { 
            background: linear-gradient(135deg, #2a2a2a, #1f1f1f); 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            border: 1px solid #333; 
        }
        .stat-value { 
            font-size: 28px; 
            font-weight: bold; 
            color: #4CAF50; 
            margin-bottom: 5px; 
        }
        .stat-label { 
            color: #888; 
            font-size: 14px; 
        }
        .chart-section { 
            background: #2a2a2a; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px; 
            border: 1px solid #333; 
        }
        .orders-section { 
            background: #2a2a2a; 
            padding: 20px; 
            border-radius: 10px; 
            max-height: 400px; 
            overflow-y: auto; 
            border: 1px solid #333; 
        }
        .order { 
            padding: 10px; 
            margin: 8px 0; 
            border-radius: 6px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
        }
        .buy { 
            background: rgba(76, 175, 80, 0.15); 
            border-left: 4px solid #4CAF50; 
        }
        .sell { 
            background: rgba(244, 67, 54, 0.15); 
            border-left: 4px solid #f44336; 
        }
        .status { 
            display: inline-block; 
            padding: 4px 8px; 
            border-radius: 4px; 
            font-size: 12px; 
        }
        .connected { 
            background: #4CAF50; 
            color: white; 
        }
        .disconnected { 
            background: #f44336; 
            color: white; 
        }
        #chart { 
            min-height: 500px; 
            background: #1a1a1a; 
            border-radius: 8px; 
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 Live BTCUSDT Dashboard</h1>
        <span id="connection-status" class="status disconnected">Connecting...</span>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="trades">0</div>
            <div class="stat-label">Total Trades</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="whales">0</div>
            <div class="stat-label">Large Orders (>2 BTC)</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="price">$0</div>
            <div class="stat-label">Current Price</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="recent">0</div>
            <div class="stat-label">Recent Trades</div>
        </div>
    </div>
    
    <div class="chart-section">
        <h3>📊 Live Price Chart</h3>
        <div id="chart">Initializing chart...</div>
    </div>
    
    <div class="orders-section">
        <h3>🐋 Large Orders Stream</h3>
        <div id="orders-list">Waiting for large orders...</div>
    </div>
    
    <script>
        const socket = io();
        let ordersList = [];
        let priceData = [];
        let timeData = [];
        
        // Initialize chart
        const layout = {
            title: 'BTCUSDT Live Price',
            paper_bgcolor: '#1a1a1a',
            plot_bgcolor: '#1a1a1a',
            font: { color: 'white' },
            xaxis: { 
                gridcolor: '#333', 
                title: 'Time',
                showgrid: true 
            },
            yaxis: { 
                gridcolor: '#333', 
                title: 'Price ($)',
                showgrid: true 
            },
            margin: { t: 50, b: 50, l: 60, r: 60 }
        };
        
        const trace = {
            x: [],
            y: [],
            mode: 'lines+markers',
            type: 'scatter',
            name: 'Price',
            line: { color: '#4CAF50', width: 2 },
            marker: { size: 4, color: '#4CAF50' }
        };
        
        Plotly.newPlot('chart', [trace], layout, {responsive: true});
        
        // Socket events
        socket.on('connect', function() {
            console.log('🔌 Connected to server');
            document.getElementById('connection-status').textContent = 'Connected';
            document.getElementById('connection-status').className = 'status connected';
        });
        
        socket.on('disconnect', function() {
            console.log('❌ Disconnected from server');
            document.getElementById('connection-status').textContent = 'Disconnected';
            document.getElementById('connection-status').className = 'status disconnected';
        });
        
        socket.on('stats_update', function(data) {
            // Update stats
            document.getElementById('trades').textContent = data.trades_count.toLocaleString();
            document.getElementById('whales').textContent = data.large_orders_count;
            document.getElementById('price').textContent = '$' + data.current_price.toLocaleString(undefined, {minimumFractionDigits: 2});
            document.getElementById('recent').textContent = Math.min(100, data.trades_count);
            
            // Update chart
            if (data.current_price > 0) {
                const now = new Date();
                priceData.push(data.current_price);
                timeData.push(now);
                
                // Keep last 50 points
                if (priceData.length > 50) {
                    priceData.shift();
                    timeData.shift();
                }
                
                // Update plot
                Plotly.restyle('chart', {
                    x: [timeData],
                    y: [priceData]
                });
            }
        });
        
        socket.on('large_order', function(order) {
            console.log('🐋 Large order:', order);
            
            ordersList.unshift(order);
            if (ordersList.length > 15) ordersList.pop();
            
            updateOrdersList();
            
            // Add bubble to chart
            addBubbleToChart(order);
        });
        
        function updateOrdersList() {
            const container = document.getElementById('orders-list');
            
            if (ordersList.length === 0) {
                container.innerHTML = '<div style="text-align:center; color:#666; padding:20px;">Waiting for large orders...</div>';
                return;
            }
            
            container.innerHTML = ordersList.map(order => {
                const sideClass = order.side === 'buy' ? 'buy' : 'sell';
                const sideEmoji = order.side === 'buy' ? '🟢' : '🔴';
                const value = (order.value || 0).toLocaleString(undefined, {maximumFractionDigits: 0});
                
                return `
                    <div class="order ${sideClass}">
                        <div>
                            ${sideEmoji} <strong>${order.side.toUpperCase()}</strong> 
                            ${order.volume.toFixed(4)} BTC @ $${order.price.toLocaleString()}
                        </div>
                        <div style="text-align: right;">
                            <div>$${value}</div>
                            <div style="font-size: 12px; color: #888;">${order.time}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Add bubble to chart for large orders
        function addBubbleToChart(order) {
            const now = new Date();
            const color = order.side === 'buy' ? '#4CAF50' : '#f44336';
            const size = Math.min(50, Math.max(15, order.volume * 8));
            
            const bubbleTrace = {
                x: [now],
                y: [order.price],
                mode: 'markers',
                type: 'scatter',
                name: `${order.side.toUpperCase()} ${order.volume.toFixed(2)} BTC`,
                marker: {
                    size: [size],
                    color: color,
                    opacity: 0.7,
                    symbol: 'circle',
                    line: { width: 2, color: 'white' }
                },
                showlegend: false,
                text: [`${order.side.toUpperCase()}: ${order.volume.toFixed(2)} BTC<br>Price: $${order.price.toLocaleString()}<br>Value: $${(order.value || 0).toLocaleString()}`],
                hovertemplate: '%{text}<extra></extra>'
            };
            
            Plotly.addTraces('chart', bubbleTrace);
            
            // Remove old bubbles (keep last 20)
            setTimeout(() => {
                const chartDiv = document.getElementById('chart');
                if (chartDiv.data && chartDiv.data.length > 21) {
                    Plotly.deleteTraces('chart', 1); // Remove oldest bubble trace
                }
            }, 100);
        }
        
        // Initial setup
        setTimeout(() => {
            console.log('🚀 Dashboard ready');
        }, 1000);
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/debug')
def debug():
    return jsonify({
        'trades_count': dashboard.trades_count,
        'large_orders_count': dashboard.large_orders_count,
        'current_price': dashboard.current_price,
        'connection_active': dashboard.connection_active,
        'recent_trades': len(dashboard.recent_trades),
        'large_orders': len(dashboard.large_orders)
    })

@socketio.on('connect')
def handle_connect():
    print("👤 Client connected")
    dashboard.start_websocket()

if __name__ == '__main__':
    print("🚀 Simple Dashboard Starting...")
    print("🌐 URL: http://localhost:5004")
    print("🔴 Live BTCUSDT data")
    print("🐋 Whale detection: >2.0 BTC")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5004)