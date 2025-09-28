"""
REAL-TIME DASHBOARD SERVER
Server Flask che serve grafici orderflow aggiornati in real-time
"""
from flask import Flask, render_template_string, jsonify, send_file
from flask_socketio import SocketIO, emit
import asyncio
import websockets
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
import sys
import os
import logging

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.chart_system import (
    VolumeProfileCalculator,
    OrderFlowAnalyzer,
    ChartRenderer
)

# Disable Flask logging noise
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orderflow_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class RealTimeDashboard:
    """Dashboard real-time per orderflow"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT']
        self.large_order_threshold = 2.0
        
        # Components
        self.volume_calculator = VolumeProfileCalculator(tick_size=1.0)
        self.analyzer = OrderFlowAnalyzer(large_order_threshold_btc=self.large_order_threshold)
        self.renderer = ChartRenderer()
        
        # Data storage
        self.trades_buffer = []
        self.large_orders = []
        self.connection_active = False
        
        # Statistics
        self.stats = {
            'trades_count': 0,
            'large_orders_count': 0,
            'last_update': None,
            'connection_start': datetime.now().isoformat(),
            'current_price': 0,
            'price_change_24h': 0
        }
        
        # WebSocket connection
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws_thread = None
        
    def start_websocket(self):
        """Avvia WebSocket in background thread"""
        if self.ws_thread is None or not self.ws_thread.is_alive():
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            print("🔴 WebSocket started in background")
    
    def _run_websocket(self):
        """Esegue WebSocket loop"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._websocket_loop())
    
    async def _websocket_loop(self):
        """Loop WebSocket principale"""
        while True:
            try:
                print("🔌 Connecting to Bybit WebSocket...")
                async with websockets.connect(self.ws_url) as websocket:
                    self.connection_active = True
                    
                    # Subscribe
                    subscription = {
                        "op": "subscribe",
                        "args": ["publicTrade.BTCUSDT"]
                    }
                    await websocket.send(json.dumps(subscription))
                    print("📡 Subscribed to BTCUSDT")
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                self.connection_active = False
                await asyncio.sleep(5)  # Retry after 5 seconds
    
    async def _handle_message(self, message):
        """Handle WebSocket messages"""
        try:
            data = json.loads(message)
            
            if "success" in data:
                return
            
            if "topic" in data and "publicTrade" in data["topic"]:
                await self._process_trades(data)
                
        except Exception as e:
            print(f"❌ Message error: {e}")
    
    async def _process_trades(self, data):
        """Process trade data"""
        try:
            trades_data = data["data"]
            
            for trade_data in trades_data:
                trade_info = {
                    'symbol': 'BTCUSDT',
                    'price': float(trade_data["p"]),
                    'volume': float(trade_data["v"]),
                    'side': 'buy' if trade_data["S"] == "Buy" else 'sell',
                    'timestamp': datetime.fromtimestamp(int(trade_data["T"]) / 1000),
                    'trade_id': trade_data["i"]
                }
                
                # Add to buffer
                self.trades_buffer.append(trade_info)
                
                # Keep only last 2000 trades
                if len(self.trades_buffer) > 2000:
                    self.trades_buffer = self.trades_buffer[-2000:]
                
                # Update stats
                self.stats['trades_count'] += 1
                self.stats['current_price'] = trade_info['price']
                self.stats['last_update'] = datetime.now().isoformat()
                
                # Check large order
                if trade_info['volume'] >= self.large_order_threshold:
                    self._handle_large_order(trade_info)
                
                # Emit to frontend every 5 trades
                if self.stats['trades_count'] % 5 == 0:
                    self._emit_update()
                    
        except Exception as e:
            print(f"❌ Process trades error: {e}")
    
    def _handle_large_order(self, trade_info):
        """Handle large order"""
        large_order = {
            'symbol': trade_info['symbol'],
            'side': trade_info['side'],
            'price': trade_info['price'],
            'volume': trade_info['volume'],
            'value': trade_info['price'] * trade_info['volume'],
            'timestamp': trade_info['timestamp'].isoformat(),  # Convert datetime to string
            'impact_score': min(100, (trade_info['volume'] / self.large_order_threshold) * 20)
        }
        
        self.large_orders.append(large_order)
        self.stats['large_orders_count'] += 1
        
        # Keep only last 100 large orders
        if len(self.large_orders) > 100:
            self.large_orders = self.large_orders[-100:]
        
        print(f"🐋 Large Order: {trade_info['side']} {trade_info['volume']:.2f} @ ${trade_info['price']:,.2f}")
        
        # Emit large order to frontend
        try:
            socketio.emit('large_order', large_order)
        except Exception as e:
            print(f"❌ Emit large order error: {e}")
    
    def _emit_update(self):
        """Emit update to frontend"""
        try:
            # Calculate basic stats
            recent_trades = [t for t in self.trades_buffer if t['timestamp'] >= datetime.now() - timedelta(minutes=5)]
            
            # Prepare update data (all datetime already converted to string)
            update_data = {
                'stats': self.stats.copy(),
                'connection_active': self.connection_active,
                'recent_trades_count': len(recent_trades),
                'avg_price_5min': float(np.mean([t['price'] for t in recent_trades])) if recent_trades else 0.0
            }
            
            try:
                socketio.emit('stats_update', update_data)
            except Exception as e:
                print(f"❌ Emit stats error: {e}")
            
        except Exception as e:
            print(f"❌ Emit error: {e}")
    
    def generate_current_chart(self, lookback_minutes=30):
        """Generate chart with current data"""
        try:
            if not self.trades_buffer:
                return None
            
            # Filter recent trades
            cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
            recent_trades = [t for t in self.trades_buffer if t['timestamp'] >= cutoff_time]
            
            if len(recent_trades) < 10:
                return None
            
            trades_df = pd.DataFrame(recent_trades)
            
            # Calculate volume profile
            volume_profile = self.volume_calculator.calculate_profile(trades_df)
            
            # Generate candle data
            candles_df = self._create_candle_data(trades_df)
            
            # Get recent large orders
            recent_large_orders = [
                order for order in self.large_orders
                if order['timestamp'] >= cutoff_time
            ]
            
            # Convert to analyzer format
            analyzer_large_orders = []
            for order in recent_large_orders:
                analyzer_large_orders.append(type('LargeOrder', (), order)())
            
            # Generate signals
            signals = self.analyzer.analyze_volume_profile_signals('BTCUSDT', trades_df)
            
            # Create chart
            fig = self.renderer.create_orderflow_chart(
                'BTCUSDT', candles_df, volume_profile, analyzer_large_orders, signals
            )
            
            # Convert to HTML
            chart_html = fig.to_html(include_plotlyjs='cdn', div_id="orderflow-chart")
            
            return chart_html
            
        except Exception as e:
            print(f"❌ Chart generation error: {e}")
            return None
    
    def _create_candle_data(self, trades_df, timeframe_minutes=2):
        """Create candlestick data from trades"""
        try:
            df = trades_df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            freq = f"{timeframe_minutes}min"
            ohlc = df['price'].resample(freq).ohlc()
            volume = df['volume'].resample(freq).sum()
            
            candles = pd.DataFrame({
                'timestamp': ohlc.index,
                'open': ohlc['open'].ffill(),
                'high': ohlc['high'].ffill(),
                'low': ohlc['low'].ffill(),
                'close': ohlc['close'].ffill(),
                'volume': volume.fillna(0)
            }).dropna()
            
            return candles.reset_index(drop=True)
        except:
            return pd.DataFrame()

# Global dashboard instance
dashboard = RealTimeDashboard()

# HTML Template for dashboard
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Live Orderflow Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { margin: 0; padding: 20px; background: #1a1a1a; color: white; font-family: Arial; }
        .header { text-align: center; margin-bottom: 20px; }
        .status { display: flex; justify-content: space-around; margin-bottom: 20px; }
        .stat-box { background: #2a2a2a; padding: 15px; border-radius: 8px; text-align: center; min-width: 150px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
        .stat-label { font-size: 12px; color: #888; }
        .chart-container { background: #2a2a2a; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .large-orders { background: #2a2a2a; border-radius: 8px; padding: 20px; max-height: 300px; overflow-y: auto; }
        .large-order { padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid; }
        .large-order.buy { border-left-color: #4CAF50; background: rgba(76, 175, 80, 0.1); }
        .large-order.sell { border-left-color: #f44336; background: rgba(244, 67, 54, 0.1); }
        .connection-status { padding: 5px 10px; border-radius: 15px; font-size: 12px; }
        .connected { background: #4CAF50; }
        .disconnected { background: #f44336; }
        .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 Live Orderflow Dashboard - BTCUSDT</h1>
        <div id="connection-status" class="connection-status disconnected">Connecting...</div>
        <button class="refresh-btn" onclick="refreshChart()">🔄 Refresh Chart</button>
    </div>
    
    <div class="status">
        <div class="stat-box">
            <div class="stat-value" id="trades-count">0</div>
            <div class="stat-label">Total Trades</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="large-orders-count">0</div>
            <div class="stat-label">Large Orders</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="current-price">$0</div>
            <div class="stat-label">Current Price</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="recent-trades">0</div>
            <div class="stat-label">Trades (5min)</div>
        </div>
    </div>
    
    <div class="chart-container">
        <h3>📊 Real-Time Orderflow Chart</h3>
        <div id="orderflow-chart">Loading chart...</div>
    </div>
    
    <div class="large-orders">
        <h3>🐋 Recent Large Orders</h3>
        <div id="large-orders-list">Waiting for large orders...</div>
    </div>
    
    <script>
        const socket = io();
        let largeOrdersList = [];
        
        socket.on('connect', function() {
            console.log('Connected to server');
            document.getElementById('connection-status').textContent = '🟢 Connected';
            document.getElementById('connection-status').className = 'connection-status connected';
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            document.getElementById('connection-status').textContent = '🔴 Disconnected';
            document.getElementById('connection-status').className = 'connection-status disconnected';
        });
        
        socket.on('stats_update', function(data) {
            document.getElementById('trades-count').textContent = data.stats.trades_count.toLocaleString();
            document.getElementById('large-orders-count').textContent = data.stats.large_orders_count;
            document.getElementById('current-price').textContent = '$' + data.stats.current_price.toLocaleString(undefined, {minimumFractionDigits: 2});
            document.getElementById('recent-trades').textContent = data.recent_trades_count;
        });
        
        socket.on('large_order', function(order) {
            largeOrdersList.unshift(order);
            if (largeOrdersList.length > 20) largeOrdersList.pop();
            updateLargeOrdersList();
        });
        
        function updateLargeOrdersList() {
            const container = document.getElementById('large-orders-list');
            if (largeOrdersList.length === 0) {
                container.innerHTML = 'Waiting for large orders...';
                return;
            }
            
            container.innerHTML = largeOrdersList.map(order => {
                const time = new Date(order.timestamp).toLocaleTimeString();
                const sideEmoji = order.side === 'buy' ? '🟢' : '🔴';
                return `
                    <div class="large-order ${order.side}">
                        ${sideEmoji} <strong>${order.side.toUpperCase()}</strong> 
                        ${order.volume.toFixed(4)} BTC @ $${order.price.toLocaleString()}
                        <small style="float: right;">${time} | Impact: ${order.impact_score.toFixed(1)}</small>
                    </div>
                `;
            }).join('');
        }
        
        function refreshChart() {
            fetch('/get_chart')
                .then(response => response.text())
                .then(html => {
                    if (html && html !== 'null') {
                        document.getElementById('orderflow-chart').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        // Auto-refresh chart every 30 seconds
        setInterval(refreshChart, 30000);
        
        // Initial chart load
        setTimeout(refreshChart, 3000);
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard_page():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/get_chart')
def get_chart():
    """Get current chart HTML"""
    chart_html = dashboard.generate_current_chart(lookback_minutes=30)
    return chart_html or "No data available yet"

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"👤 Client connected")
    # Start WebSocket if not already running
    dashboard.start_websocket()

if __name__ == '__main__':
    print("🚀 Starting Real-Time Orderflow Dashboard")
    print("=" * 50)
    print("🌐 Dashboard will be available at: http://localhost:5002")
    print("🔴 Real-time data from Bybit WebSocket")
    print("📊 Auto-refreshing charts every 30 seconds") 
    print("🐋 Live whale detection")
    print("\n💡 Open browser to: http://localhost:5002")
    print("-" * 50)
    
    # Start dashboard
    socketio.run(app, debug=False, host='0.0.0.0', port=5002)