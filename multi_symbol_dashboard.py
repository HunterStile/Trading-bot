"""
DASHBOARD SEMPLICE MULTI-SYMBOL
Versione semplice con supporto per BTCUSDT, SUIUSDT, ETHUSDT, SOLUSDT
"""
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import asyncio
import websockets
import json
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi_simple_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class MultiSymbolDashboard:
    def __init__(self):
        # Supported symbols
        self.symbols = ['BTCUSDT', 'SUIUSDT', 'ETHUSDT', 'SOLUSDT']
        self.current_symbol = 'BTCUSDT'
        
        # Stats per symbol
        self.stats = {}
        for symbol in self.symbols:
            self.stats[symbol] = {
                'trades_count': 0,
                'large_orders_count': 0,
                'current_price': 0.0,
                'session_start': time.time()
            }
        
        # Data per symbol
        self.recent_trades = {}
        self.large_orders = {}
        for symbol in self.symbols:
            self.recent_trades[symbol] = []
            self.large_orders[symbol] = []
        
        self.connection_active = False
        
        # WebSocket
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws_thread = None
        
    def get_large_order_threshold(self, symbol):
        """Get large order threshold per symbol"""
        thresholds = {
            'BTCUSDT': 2.0,
            'SUIUSDT': 10000.0,
            'ETHUSDT': 50.0,
            'SOLUSDT': 500.0
        }
        return thresholds.get(symbol, 1000.0)
        
    def start_websocket(self):
        if self.ws_thread is None or not self.ws_thread.is_alive():
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            print("🔴 Multi-Symbol WebSocket started")
    
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
                    
                    # Subscribe to all symbols
                    subscribe_args = [f"publicTrade.{symbol}" for symbol in self.symbols]
                    await websocket.send(json.dumps({
                        "op": "subscribe",
                        "args": subscribe_args
                    }))
                    print(f"📡 Subscribed to: {', '.join(self.symbols)}")
                    
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
                    # Extract symbol
                    symbol = trade_data.get("s", "BTCUSDT")
                    if symbol not in self.symbols:
                        continue
                    
                    price = float(trade_data["p"])
                    volume = float(trade_data["v"])
                    side = 'buy' if trade_data["S"] == "Buy" else 'sell'
                    
                    self.stats[symbol]['trades_count'] += 1
                    self.stats[symbol]['current_price'] = price
                    
                    # Add to recent trades
                    trade_info = {
                        'symbol': symbol,
                        'price': price,
                        'volume': volume,
                        'side': side,
                        'time': time.strftime('%H:%M:%S'),
                        'timestamp': time.time()
                    }
                    
                    self.recent_trades[symbol].append(trade_info)
                    if len(self.recent_trades[symbol]) > 100:
                        self.recent_trades[symbol] = self.recent_trades[symbol][-100:]
                    
                    # Check large order
                    threshold = self.get_large_order_threshold(symbol)
                    if volume >= threshold:
                        self._handle_large_order(trade_info, threshold)
                    
                    # Emit update every 5 trades for current symbol
                    if symbol == self.current_symbol and self.stats[symbol]['trades_count'] % 5 == 0:
                        self._emit_update()
                        
        except Exception as e:
            print(f"❌ Message error: {e}")
    
    def _handle_large_order(self, trade_info, threshold):
        symbol = trade_info['symbol']
        
        large_order = {
            'symbol': symbol,
            'side': trade_info['side'],
            'price': trade_info['price'],
            'volume': trade_info['volume'],
            'value': trade_info['price'] * trade_info['volume'],
            'time': trade_info['time'],
            'timestamp': trade_info['timestamp']
        }
        
        self.large_orders[symbol].append(large_order)
        self.stats[symbol]['large_orders_count'] += 1
        
        if len(self.large_orders[symbol]) > 20:
            self.large_orders[symbol] = self.large_orders[symbol][-20:]
        
        # Print to console
        side_emoji = "🟢" if trade_info['side'] == 'buy' else "🔴"
        print(f"{side_emoji} Large {symbol}: {trade_info['side']} {trade_info['volume']:.2f} @ ${trade_info['price']:,.4f}")
        
        # Emit to frontend only for current symbol
        if symbol == self.current_symbol:
            socketio.emit('large_order', large_order)
    
    def _emit_update(self):
        symbol = self.current_symbol
        
        update_data = {
            'symbol': symbol,
            'trades_count': self.stats[symbol]['trades_count'],
            'large_orders_count': self.stats[symbol]['large_orders_count'],
            'current_price': self.stats[symbol]['current_price'],
            'connection_active': self.connection_active,
            'recent_trades_count': len(self.recent_trades[symbol])
        }
        
        socketio.emit('stats_update', update_data)
    
    def set_current_symbol(self, symbol):
        if symbol in self.symbols:
            self.current_symbol = symbol
            print(f"🔄 Simple Dashboard switched to {symbol}")
            return True
        return False

# Global dashboard
dashboard = MultiSymbolDashboard()

# Multi-Symbol HTML Template
MULTI_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Multi-Symbol Live Dashboard</title>
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
        .symbol-selector {
            margin: 15px 0;
        }
        .symbol-selector select {
            background: #2a2a2a; 
            color: white; 
            border: 1px solid #555; 
            padding: 10px 15px; 
            border-radius: 8px; 
            font-size: 16px;
            margin: 0 10px;
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
        .threshold-info {
            background: rgba(59, 130, 246, 0.1);
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 12px;
            text-align: center;
            color: #93c5fd;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 Multi-Symbol Live Dashboard</h1>
        <div class="symbol-selector">
            <label>Select Symbol:</label>
            <select id="symbol-select">
                <option value="BTCUSDT">BTCUSDT (>2.0)</option>
                <option value="SUIUSDT">SUIUSDT (>10,000)</option>
                <option value="ETHUSDT">ETHUSDT (>50.0)</option>
                <option value="SOLUSDT">SOLUSDT (>500.0)</option>
            </select>
        </div>
        <span id="connection-status" class="status disconnected">Connecting...</span>
        <div class="threshold-info" id="threshold-info">
            Large order threshold: Loading...
        </div>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="trades">0</div>
            <div class="stat-label">Total Trades</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="whales">0</div>
            <div class="stat-label">Large Orders</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="price">$0.00</div>
            <div class="stat-label">Current Price</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="recent">0</div>
            <div class="stat-label">Recent Trades</div>
        </div>
    </div>
    
    <div class="chart-section">
        <h3 id="chart-title">📊 Live Price Chart</h3>
        <div id="chart">Initializing chart...</div>
    </div>
    
    <div class="orders-section">
        <h3 id="orders-title">🐋 Large Orders Stream</h3>
        <div id="orders-list">Waiting for large orders...</div>
    </div>
    
    <script>
        const socket = io();
        let ordersList = [];
        let priceData = [];
        let timeData = [];
        let currentSymbol = 'BTCUSDT';
        let thresholds = {};
        
        // Initialize chart
        const layout = {
            title: 'Live Price',
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
        
        // Setup symbol selector
        document.getElementById('symbol-select').addEventListener('change', function() {
            switchSymbol(this.value);
        });
        
        // Load initial data
        fetch('/api/symbols')
            .then(response => response.json())
            .then(data => {
                currentSymbol = data.current_symbol;
                thresholds = data.thresholds;
                document.getElementById('symbol-select').value = currentSymbol;
                updateThresholdInfo();
                updateTitles();
            });
        
        function switchSymbol(newSymbol) {
            fetch('/api/switch-symbol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: newSymbol })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentSymbol = newSymbol;
                    ordersList = [];
                    priceData = [];
                    timeData = [];
                    
                    updateTitles();
                    updateThresholdInfo();
                    updateOrdersList();
                    
                    // Clear chart
                    Plotly.restyle('chart', {
                        x: [[]],
                        y: [[]]
                    });
                    
                    console.log('🔄 Switched to:', newSymbol);
                }
            });
        }
        
        function updateTitles() {
            document.getElementById('chart-title').textContent = `📊 ${currentSymbol} Live Price Chart`;
            document.getElementById('orders-title').textContent = `🐋 ${currentSymbol} Large Orders`;
        }
        
        function updateThresholdInfo() {
            const threshold = thresholds[currentSymbol] || 0;
            document.getElementById('threshold-info').textContent = 
                `${currentSymbol} large order threshold: ${threshold.toLocaleString()}`;
        }
        
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
            document.getElementById('price').textContent = '$' + data.current_price.toLocaleString(undefined, {minimumFractionDigits: 4});
            document.getElementById('recent').textContent = data.recent_trades_count;
            
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
        
        function addBubbleToChart(order) {
            const color = order.side === 'buy' ? '#4CAF50' : '#f44336';
            const size = Math.min(50, Math.max(15, (order.volume / thresholds[currentSymbol]) * 30));
            
            const bubbleTrace = {
                x: [new Date()],
                y: [order.price],
                mode: 'markers',
                type: 'scatter',
                name: `${order.side.toUpperCase()} ${order.volume.toFixed(2)}`,
                marker: {
                    size: [size],
                    color: color,
                    opacity: 0.7,
                    symbol: 'circle',
                    line: { width: 2, color: 'white' }
                },
                showlegend: false,
                text: [`${order.symbol} ${order.side.toUpperCase()}: ${order.volume.toLocaleString()}<br>Price: $${order.price.toLocaleString()}<br>Value: $${order.value.toLocaleString()}<br>${order.time}`],
                hovertemplate: '%{text}<extra></extra>'
            };
            
            Plotly.addTraces('chart', bubbleTrace);
            
            // Remove old bubbles
            setTimeout(() => {
                const chartDiv = document.getElementById('chart');
                if (chartDiv.data && chartDiv.data.length > 21) {
                    Plotly.deleteTraces('chart', 1);
                }
            }, 100);
        }
        
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
                            ${order.volume.toLocaleString()} ${order.symbol.replace('USDT', '')} @ $${order.price.toLocaleString()}
                        </div>
                        <div style="text-align: right;">
                            <div>$${value}</div>
                            <div style="font-size: 12px; color: #888;">${order.time}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        console.log('🚀 Multi-Symbol Dashboard Ready');
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(MULTI_HTML_TEMPLATE)

@app.route('/api/switch-symbol', methods=['POST'])
def switch_symbol():
    data = request.get_json()
    symbol = data.get('symbol')
    if dashboard.set_current_symbol(symbol):
        return jsonify({'success': True, 'symbol': symbol})
    return jsonify({'success': False, 'error': 'Invalid symbol'}), 400

@app.route('/api/symbols')
def get_symbols():
    return jsonify({
        'symbols': dashboard.symbols,
        'current_symbol': dashboard.current_symbol,
        'thresholds': {symbol: dashboard.get_large_order_threshold(symbol) for symbol in dashboard.symbols}
    })

@app.route('/debug')
def debug():
    return jsonify({
        'current_symbol': dashboard.current_symbol,
        'stats': dashboard.stats,
        'connection_active': dashboard.connection_active,
        'recent_trades_lengths': {symbol: len(trades) for symbol, trades in dashboard.recent_trades.items()},
        'large_orders_lengths': {symbol: len(orders) for symbol, orders in dashboard.large_orders.items()}
    })

@socketio.on('connect')
def handle_connect():
    print("👤 Multi-Symbol client connected")
    dashboard.start_websocket()

if __name__ == '__main__':
    print("🚀 Multi-Symbol Simple Dashboard Starting...")
    print("🌐 URL: http://localhost:5007")
    print("🔴 Live multi-symbol data")
    print("🐋 Symbol-specific whale detection")
    print("💰 Symbols: BTCUSDT, SUIUSDT, ETHUSDT, SOLUSDT")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5007)