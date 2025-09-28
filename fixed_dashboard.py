"""
REAL-TIME DASHBOARD FIXED
Versione corretta senza errori di serializzazione
"""
from flask import Flask, render_template_string, jsonify
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
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orderflow_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class SafeRealTimeDashboard:
    """Dashboard real-time senza problemi di serializzazione"""
    
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
        
        # Statistics (JSON-safe)
        self.stats = {
            'trades_count': 0,
            'large_orders_count': 0,
            'current_price': 0.0,
            'session_start': time.time()
        }
        
        # WebSocket
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws_thread = None
        
    def start_websocket(self):
        """Avvia WebSocket in background"""
        if self.ws_thread is None or not self.ws_thread.is_alive():
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            print("🔴 WebSocket thread started")
    
    def _run_websocket(self):
        """WebSocket loop"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._websocket_loop())
    
    async def _websocket_loop(self):
        """Main WebSocket loop"""
        while True:
            try:
                print("🔌 Connecting to Bybit...")
                async with websockets.connect(self.ws_url) as websocket:
                    self.connection_active = True
                    
                    # Subscribe
                    await websocket.send(json.dumps({
                        "op": "subscribe",
                        "args": ["publicTrade.BTCUSDT"]
                    }))
                    print("📡 Subscribed to BTCUSDT")
                    
                    # Message loop
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                self.connection_active = False
                await asyncio.sleep(5)
    
    async def _handle_message(self, message):
        """Handle messages"""
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
            for trade_data in data["data"]:
                # Create trade info (JSON-safe)
                trade_info = {
                    'price': float(trade_data["p"]),
                    'volume': float(trade_data["v"]),
                    'side': 'buy' if trade_data["S"] == "Buy" else 'sell',
                    'timestamp': int(trade_data["T"]) / 1000,  # Unix timestamp
                    'trade_id': trade_data["i"]
                }
                
                # Add to buffer
                self.trades_buffer.append(trade_info)
                if len(self.trades_buffer) > 1000:
                    self.trades_buffer = self.trades_buffer[-1000:]
                
                # Update stats
                self.stats['trades_count'] += 1
                self.stats['current_price'] = trade_info['price']
                
                # Check large order
                if trade_info['volume'] >= self.large_order_threshold:
                    self._handle_large_order(trade_info)
                
                # Emit update every 10 trades
                if self.stats['trades_count'] % 10 == 0:
                    self._safe_emit_update()
                    
        except Exception as e:
            print(f"❌ Process error: {e}")
    
    def _handle_large_order(self, trade_info):
        """Handle large orders"""
        try:
            large_order = {
                'side': trade_info['side'],
                'price': trade_info['price'],
                'volume': trade_info['volume'],
                'value': trade_info['price'] * trade_info['volume'],
                'timestamp': trade_info['timestamp'],
                'impact_score': min(100, (trade_info['volume'] / self.large_order_threshold) * 20)
            }
            
            self.large_orders.append(large_order)
            self.stats['large_orders_count'] += 1
            
            # Keep only recent orders
            if len(self.large_orders) > 50:
                self.large_orders = self.large_orders[-50:]
            
            # Print to console
            side_emoji = "🟢" if trade_info['side'] == 'buy' else "🔴"
            print(f"{side_emoji} Large Order: {trade_info['side']} {trade_info['volume']:.2f} @ ${trade_info['price']:,.2f}")
            
            # Emit to frontend
            socketio.emit('large_order', large_order)
            
        except Exception as e:
            print(f"❌ Large order error: {e}")
    
    def _safe_emit_update(self):
        """Safe emit without datetime issues"""
        try:
            # Calculate recent trades
            cutoff_time = time.time() - 300  # Last 5 minutes
            recent_trades = [t for t in self.trades_buffer if t['timestamp'] >= cutoff_time]
            
            # Session duration
            session_duration = int(time.time() - self.stats['session_start'])
            
            update_data = {
                'stats': {
                    'trades_count': self.stats['trades_count'],
                    'large_orders_count': self.stats['large_orders_count'],
                    'current_price': self.stats['current_price'],
                    'session_duration': session_duration
                },
                'connection_active': self.connection_active,
                'recent_trades_count': len(recent_trades),
                'avg_price_5min': float(np.mean([t['price'] for t in recent_trades])) if recent_trades else 0.0
            }
            
            socketio.emit('stats_update', update_data)
            
        except Exception as e:
            print(f"❌ Emit error: {e}")
    
    def generate_current_chart(self):
        """Generate chart with current data"""
        try:
            if len(self.trades_buffer) < 10:
                return f"<div style='text-align:center; padding:40px; color:#888;'>Collecting data... {len(self.trades_buffer)} trades so far</div>"
            
            # Simple price chart with Plotly
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            # Get recent trades
            recent_trades = self.trades_buffer[-200:]  # Last 200 trades
            
            # Prepare data
            timestamps = [datetime.fromtimestamp(t['timestamp']) for t in recent_trades]
            prices = [t['price'] for t in recent_trades]
            volumes = [t['volume'] for t in recent_trades]
            sides = [t['side'] for t in recent_trades]
            
            # Create price line
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=['BTCUSDT Price', 'Volume Profile'],
                row_heights=[0.7, 0.3],
                vertical_spacing=0.05
            )
            
            # Price line
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=prices,
                    mode='lines+markers',
                    name='Price',
                    line=dict(color='white', width=2),
                    marker=dict(size=4)
                ),
                row=1, col=1
            )
            
            # Add large orders as bubbles
            large_orders_recent = [o for o in self.large_orders if o['timestamp'] > (time.time() - 1800)]
            
            if large_orders_recent:
                large_times = [datetime.fromtimestamp(o['timestamp']) for o in large_orders_recent]
                large_prices = [o['price'] for o in large_orders_recent]
                large_volumes = [o['volume'] for o in large_orders_recent]
                large_sides = [o['side'] for o in large_orders_recent]
                
                # Buy orders
                buy_orders = [(t, p, v) for t, p, v, s in zip(large_times, large_prices, large_volumes, large_sides) if s == 'buy']
                if buy_orders:
                    buy_times, buy_prices, buy_vols = zip(*buy_orders)
                    fig.add_trace(
                        go.Scatter(
                            x=buy_times,
                            y=buy_prices,
                            mode='markers',
                            name='Large Buys',
                            marker=dict(
                                size=[min(50, v*5) for v in buy_vols],
                                color='green',
                                opacity=0.7,
                                symbol='circle'
                            )
                        ),
                        row=1, col=1
                    )
                
                # Sell orders
                sell_orders = [(t, p, v) for t, p, v, s in zip(large_times, large_prices, large_volumes, large_sides) if s == 'sell']
                if sell_orders:
                    sell_times, sell_prices, sell_vols = zip(*sell_orders)
                    fig.add_trace(
                        go.Scatter(
                            x=sell_times,
                            y=sell_prices,
                            mode='markers',
                            name='Large Sells',
                            marker=dict(
                                size=[min(50, v*5) for v in sell_vols],
                                color='red',
                                opacity=0.7,
                                symbol='circle'
                            )
                        ),
                        row=1, col=1
                    )
            
            # Volume bars
            buy_volumes = [v if s == 'buy' else 0 for v, s in zip(volumes, sides)]
            sell_volumes = [v if s == 'sell' else 0 for v, s in zip(volumes, sides)]
            
            fig.add_trace(
                go.Bar(x=timestamps, y=buy_volumes, name='Buy Volume', marker_color='green', opacity=0.7),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(x=timestamps, y=sell_volumes, name='Sell Volume', marker_color='red', opacity=0.7),
                row=2, col=1
            )
            
            # Styling
            fig.update_layout(
                title=f'🔴 Live BTCUSDT Orderflow ({len(recent_trades)} trades)',
                template='plotly_dark',
                height=800,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id="chart")
            
        except Exception as e:
            print(f"❌ Chart error: {e}")
            import traceback
            traceback.print_exc()
            return f"<div style='color:red; padding:20px;'>Chart error: {e}<br>Check console for details.</div>"
    
    def _create_simple_candles(self, trades_df):
        """Create simple candlestick data"""
        try:
            # Group by 2-minute intervals
            trades_df['time_group'] = pd.to_datetime(trades_df['timestamp']).dt.floor('2min')
            
            grouped = trades_df.groupby('time_group')
            
            candles_data = []
            for time_group, group in grouped:
                if len(group) > 0:
                    candles_data.append({
                        'timestamp': time_group,
                        'open': group['price'].iloc[0],
                        'high': group['price'].max(),
                        'low': group['price'].min(),
                        'close': group['price'].iloc[-1],
                        'volume': group['volume'].sum()
                    })
            
            return pd.DataFrame(candles_data)
        except:
            return pd.DataFrame()

# Global dashboard
dashboard = SafeRealTimeDashboard()

# Simple HTML template
SIMPLE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Live Orderflow</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        body { margin: 0; padding: 20px; background: #1a1a1a; color: white; font-family: Arial; }
        .header { text-align: center; margin-bottom: 20px; }
        .stats { display: flex; justify-content: space-around; margin-bottom: 20px; }
        .stat { background: #2a2a2a; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
        .chart { background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .orders { background: #2a2a2a; padding: 20px; border-radius: 8px; max-height: 400px; overflow-y: auto; }
        .order { padding: 8px; margin: 5px 0; border-radius: 4px; }
        .buy { background: rgba(76, 175, 80, 0.2); border-left: 3px solid #4CAF50; }
        .sell { background: rgba(244, 67, 54, 0.2); border-left: 3px solid #f44336; }
        .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 Live BTCUSDT Orderflow</h1>
        <button class="refresh-btn" onclick="refreshChart()">🔄 Refresh</button>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="trades">0</div>
            <div>Trades</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="whales">0</div>
            <div>Whales</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="price">$0</div>
            <div>Price</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="recent">0</div>
            <div>Recent (5m)</div>
        </div>
    </div>
    
    <div class="chart">
        <div id="chart-container">Loading chart...</div>
    </div>
    
    <div class="orders">
        <h3>🐋 Large Orders</h3>
        <div id="orders-list">Waiting for large orders...</div>
    </div>
    
    <script>
        const socket = io();
        let ordersList = [];
        
        socket.on('stats_update', function(data) {
            document.getElementById('trades').textContent = data.stats.trades_count.toLocaleString();
            document.getElementById('whales').textContent = data.stats.large_orders_count;
            document.getElementById('price').textContent = '$' + data.stats.current_price.toLocaleString();
            document.getElementById('recent').textContent = data.recent_trades_count;
        });
        
        socket.on('large_order', function(order) {
            ordersList.unshift(order);
            if (ordersList.length > 15) ordersList.pop();
            updateOrdersList();
        });
        
        function updateOrdersList() {
            const container = document.getElementById('orders-list');
            if (ordersList.length === 0) {
                container.innerHTML = 'Waiting for large orders...';
                return;
            }
            
            container.innerHTML = ordersList.map(order => {
                const time = new Date(order.timestamp * 1000).toLocaleTimeString();
                const sideClass = order.side === 'buy' ? 'buy' : 'sell';
                const sideEmoji = order.side === 'buy' ? '🟢' : '🔴';
                return `
                    <div class="order ${sideClass}">
                        ${sideEmoji} <strong>${order.side.toUpperCase()}</strong> 
                        ${order.volume.toFixed(4)} BTC @ $${order.price.toLocaleString()}
                        <small style="float: right;">${time}</small>
                    </div>
                `;
            }).join('');
        }
        
        function refreshChart() {
            fetch('/chart')
                .then(response => response.text())
                .then(html => {
                    document.getElementById('chart-container').innerHTML = html;
                });
        }
        
        setInterval(refreshChart, 30000); // Auto-refresh every 30s
        setTimeout(refreshChart, 5000);   // Initial load after 5s
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(SIMPLE_TEMPLATE)

@app.route('/chart')
def get_chart():
    try:
        print(f"📊 Chart requested - trades buffer: {len(dashboard.trades_buffer)}")
        chart_html = dashboard.generate_current_chart()
        print(f"📊 Chart generated - length: {len(chart_html)}")
        return chart_html
    except Exception as e:
        print(f"❌ Chart error: {e}")
        return f"<div style='color:red;'>Chart error: {e}</div>"

@app.route('/debug')
def debug_info():
    """Debug endpoint"""
    return jsonify({
        'trades_count': len(dashboard.trades_buffer),
        'large_orders_count': len(dashboard.large_orders),
        'connection_active': dashboard.connection_active,
        'stats': dashboard.stats
    })

@socketio.on('connect')
def handle_connect():
    print("👤 Client connected")
    dashboard.start_websocket()

if __name__ == '__main__':
    print("🚀 Fixed Real-Time Dashboard Starting...")
    print("🌐 URL: http://localhost:5003")
    print("🔴 Live BTCUSDT data")
    print("🐋 Whale detection: >2.0 BTC")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5003)