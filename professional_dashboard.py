"""
DASHBOARD PROFESSIONALE CON CANDELE E STORICO
Versione avanzata con volume profile, POC, VAH, VAL
"""
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import asyncio
import websockets
import json
import time
import threading
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'professional_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class ProfessionalDashboard:
    def __init__(self):
        # Supported symbols
        self.symbols = ['BTCUSDT', 'SUIUSDT', 'ETHUSDT', 'SOLUSDT']
        self.current_symbol = 'BTCUSDT'  # Default symbol
        
        # Stats per symbol
        self.stats = {}
        for symbol in self.symbols:
            self.stats[symbol] = {
                'trades_count': 0,
                'large_orders_count': 0,
                'current_price': 0.0,
                'session_start': time.time()
            }
        
        # Data storage per symbol
        self.raw_trades = {}  # All trades with timestamp
        self.candle_data = {}  # Organized by symbol and timeframe
        self.large_orders = {}
        self.volume_profile = {}
        
        # Initialize data structures
        self.timeframes = ['1m', '5m', '15m', '1h']
        for symbol in self.symbols:
            self.raw_trades[symbol] = []
            self.large_orders[symbol] = []
            self.volume_profile[symbol] = {}
            self.candle_data[symbol] = {}
            for tf in self.timeframes:
                self.candle_data[symbol][tf] = []
        
        # WebSocket
        self.connection_active = False
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
                    await self._process_trade(trade_data)
                        
        except Exception as e:
            print(f"❌ Message error: {e}")
    
    async def _process_trade(self, trade_data):
        try:
            # Extract symbol from trade data
            symbol = trade_data.get("s", "BTCUSDT")  # Default to BTCUSDT if not found
            if symbol not in self.symbols:
                return  # Skip unsupported symbols
            
            price = float(trade_data["p"])
            volume = float(trade_data["v"])
            side = 'buy' if trade_data["S"] == "Buy" else 'sell'
            timestamp = int(trade_data["T"]) / 1000
            
            # Store raw trade
            trade_info = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'side': side,
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp)
            }
            
            self.raw_trades[symbol].append(trade_info)
            self.stats[symbol]['trades_count'] += 1
            self.stats[symbol]['current_price'] = price
            
            # Keep last 10000 trades per symbol
            if len(self.raw_trades[symbol]) > 10000:
                self.raw_trades[symbol] = self.raw_trades[symbol][-10000:]
            
            # Update candles for all timeframes
            self._update_candles(trade_info)
            
            # Update volume profile
            self._update_volume_profile(trade_info)
            
            # Check large order (different thresholds per coin)
            threshold = self._get_large_order_threshold(symbol)
            if volume >= threshold:
                self._handle_large_order(trade_info)
            
            # Emit update every 10 trades for current symbol
            if symbol == self.current_symbol and self.stats[symbol]['trades_count'] % 10 == 0:
                self._emit_update()
                
        except Exception as e:
            print(f"❌ Process trade error: {e}")
    
    def _get_large_order_threshold(self, symbol):
        """Get large order threshold per symbol"""
        thresholds = {
            'BTCUSDT': 2.0,
            'SUIUSDT': 10000.0,
            'ETHUSDT': 50.0,
            'SOLUSDT': 500.0
        }
        return thresholds.get(symbol, 1000.0)
    
    def _update_candles(self, trade_info):
        """Update candlestick data for all timeframes"""
        try:
            symbol = trade_info['symbol']
            dt = trade_info['datetime']
            
            timeframe_seconds = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '1h': 3600
            }
            
            for tf, seconds in timeframe_seconds.items():
                # Calculate candle start time
                candle_start = dt.replace(second=0, microsecond=0)
                if tf == '5m':
                    candle_start = candle_start.replace(minute=(candle_start.minute // 5) * 5)
                elif tf == '15m':
                    candle_start = candle_start.replace(minute=(candle_start.minute // 15) * 15)
                elif tf == '1h':
                    candle_start = candle_start.replace(minute=0)
                
                # Find or create candle
                candles = self.candle_data[symbol][tf]
                current_candle = None
                
                if candles and candles[-1]['time'] == candle_start:
                    current_candle = candles[-1]
                else:
                    # Create new candle
                    current_candle = {
                        'time': candle_start,
                        'open': trade_info['price'],
                        'high': trade_info['price'],
                        'low': trade_info['price'],
                        'close': trade_info['price'],
                        'volume': 0,
                        'buy_volume': 0,
                        'sell_volume': 0
                    }
                    candles.append(current_candle)
                
                # Update candle
                current_candle['high'] = max(current_candle['high'], trade_info['price'])
                current_candle['low'] = min(current_candle['low'], trade_info['price'])
                current_candle['close'] = trade_info['price']
                current_candle['volume'] += trade_info['volume']
                
                if trade_info['side'] == 'buy':
                    current_candle['buy_volume'] += trade_info['volume']
                else:
                    current_candle['sell_volume'] += trade_info['volume']
                
                # Keep last 200 candles
                if len(candles) > 200:
                    candles.pop(0)
        
        except Exception as e:
            print(f"❌ Update candles error: {e}")
    
    def _update_volume_profile(self, trade_info):
        """Update volume profile data"""
        try:
            symbol = trade_info['symbol']
            
            # Round price to appropriate level based on symbol
            price_precision = self._get_price_precision(symbol)
            price_level = round(trade_info['price'], price_precision)
            
            if price_level not in self.volume_profile[symbol]:
                self.volume_profile[symbol][price_level] = {
                    'total_volume': 0,
                    'buy_volume': 0,
                    'sell_volume': 0
                }
            
            profile = self.volume_profile[symbol][price_level]
            profile['total_volume'] += trade_info['volume']
            
            if trade_info['side'] == 'buy':
                profile['buy_volume'] += trade_info['volume']
            else:
                profile['sell_volume'] += trade_info['volume']
            
            # Keep only last 1000 price levels per symbol
            if len(self.volume_profile[symbol]) > 1000:
                # Remove oldest entries
                sorted_levels = sorted(self.volume_profile[symbol].keys())
                for level in sorted_levels[:200]:
                    del self.volume_profile[symbol][level]
        
        except Exception as e:
            print(f"❌ Volume profile error: {e}")
    
    def _get_price_precision(self, symbol):
        """Get price precision for rounding based on symbol"""
        precisions = {
            'BTCUSDT': 0,    # Round to dollars
            'SUIUSDT': 3,    # Round to 3 decimals
            'ETHUSDT': 0,    # Round to dollars
            'SOLUSDT': 1     # Round to 1 decimal
        }
        return precisions.get(symbol, 2)
    
    def _handle_large_order(self, trade_info):
        """Handle large orders"""
        try:
            symbol = trade_info['symbol']
            threshold = self._get_large_order_threshold(symbol)
            
            large_order = {
                'symbol': symbol,
                'side': trade_info['side'],
                'price': trade_info['price'],
                'volume': trade_info['volume'],
                'value': trade_info['price'] * trade_info['volume'],
                'timestamp': trade_info['timestamp'],
                'time': trade_info['datetime'].strftime('%H:%M:%S'),
                'impact_score': min(100, (trade_info['volume'] / threshold) * 20)
            }
            
            self.large_orders[symbol].append(large_order)
            self.stats[symbol]['large_orders_count'] += 1
            
            # Keep last 100 per symbol
            if len(self.large_orders[symbol]) > 100:
                self.large_orders[symbol] = self.large_orders[symbol][-100:]
            
            # Print
            side_emoji = "🟢" if trade_info['side'] == 'buy' else "🔴"
            print(f"{side_emoji} Large {symbol}: {trade_info['side']} {trade_info['volume']:.2f} @ ${trade_info['price']:,.4f}")
            
            # Emit only for current symbol
            if symbol == self.current_symbol:
                socketio.emit('large_order', large_order)
            
        except Exception as e:
            print(f"❌ Large order error: {e}")
    
    def _emit_update(self):
        """Emit stats update"""
        try:
            symbol = self.current_symbol
            session_duration = int(time.time() - self.stats[symbol]['session_start'])
            
            # Calculate POC, VAH, VAL for current symbol
            poc_data = self._calculate_poc_vah_val(symbol)
            
            update_data = {
                'symbol': symbol,
                'trades_count': self.stats[symbol]['trades_count'],
                'large_orders_count': self.stats[symbol]['large_orders_count'],
                'current_price': self.stats[symbol]['current_price'],
                'connection_active': self.connection_active,
                'session_duration': session_duration,
                'poc_price': poc_data['poc'],
                'vah_price': poc_data['vah'],
                'val_price': poc_data['val']
            }
            
            socketio.emit('stats_update', update_data)
            
        except Exception as e:
            print(f"❌ Emit update error: {e}")
    
    def _calculate_poc_vah_val(self, symbol):
        """Calculate Point of Control, Value Area High/Low"""
        try:
            if not self.volume_profile[symbol]:
                return {'poc': 0, 'vah': 0, 'val': 0}
            
            # Find POC (highest volume price)
            poc_price = max(self.volume_profile[symbol].keys(), 
                           key=lambda p: self.volume_profile[symbol][p]['total_volume'])
            
            # Calculate total volume
            total_volume = sum(p['total_volume'] for p in self.volume_profile[symbol].values())
            value_area_volume = total_volume * 0.7  # 70% value area
            
            # Find VAH and VAL
            sorted_prices = sorted(self.volume_profile[symbol].keys())
            poc_index = sorted_prices.index(poc_price)
            
            accumulated_volume = self.volume_profile[symbol][poc_price]['total_volume']
            vah_price = poc_price
            val_price = poc_price
            
            # Expand around POC until we reach 70% of volume
            upper_idx = poc_index + 1
            lower_idx = poc_index - 1
            
            while accumulated_volume < value_area_volume and (upper_idx < len(sorted_prices) or lower_idx >= 0):
                upper_vol = self.volume_profile[symbol][sorted_prices[upper_idx]]['total_volume'] if upper_idx < len(sorted_prices) else 0
                lower_vol = self.volume_profile[symbol][sorted_prices[lower_idx]]['total_volume'] if lower_idx >= 0 else 0
                
                if upper_vol >= lower_vol and upper_idx < len(sorted_prices):
                    accumulated_volume += upper_vol
                    vah_price = sorted_prices[upper_idx]
                    upper_idx += 1
                elif lower_idx >= 0:
                    accumulated_volume += lower_vol
                    val_price = sorted_prices[lower_idx]
                    lower_idx -= 1
                else:
                    break
            
            return {
                'poc': float(poc_price),
                'vah': float(vah_price),
                'val': float(val_price)
            }
            
        except Exception as e:
            print(f"❌ POC calculation error: {e}")
            return {'poc': 0, 'vah': 0, 'val': 0}
    
    def get_candle_data(self, symbol=None, timeframe='5m', limit=100):
        """Get candlestick data for chart"""
        try:
            if symbol is None:
                symbol = self.current_symbol
            
            if symbol not in self.candle_data or timeframe not in self.candle_data[symbol]:
                return []
            
            candles = self.candle_data[symbol][timeframe][-limit:]
            
            result = []
            for candle in candles:
                result.append({
                    'time': candle['time'].isoformat(),
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume'],
                    'buy_volume': candle['buy_volume'],
                    'sell_volume': candle['sell_volume']
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Get candle data error: {e}")
            return []
    
    def get_large_orders_recent(self, symbol=None, limit=20):
        """Get recent large orders"""
        try:
            if symbol is None:
                symbol = self.current_symbol
            return self.large_orders[symbol][-limit:] if self.large_orders[symbol] else []
        except:
            return []
    
    def set_current_symbol(self, symbol):
        """Change current symbol"""
        if symbol in self.symbols:
            self.current_symbol = symbol
            print(f"🔄 Switched to {symbol}")
            return True
        return False

# Global dashboard
dashboard = ProfessionalDashboard()

# Professional HTML Template
PROFESSIONAL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Professional Trading Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0d1421; 
            color: #ffffff; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow-x: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3a8a, #3730a3);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #2563eb;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.3);
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .status-item {
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        
        .main-container {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            padding: 20px;
            min-height: calc(100vh - 120px);
        }
        
        .chart-panel {
            background: #1f2937;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #374151;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #374151, #1f2937);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #4b5563;
            transition: transform 0.2s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(0,0,0,0.4);
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #10b981;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #9ca3af;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .widget {
            background: #1f2937;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #374151;
        }
        
        .widget h3 {
            margin-bottom: 15px;
            color: #f3f4f6;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .orders-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .order-item {
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 4px solid;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
        }
        
        .order-item:hover {
            transform: translateX(5px);
        }
        
        .buy-order {
            background: rgba(16, 185, 129, 0.1);
            border-left-color: #10b981;
        }
        
        .sell-order {
            background: rgba(239, 68, 68, 0.1);
            border-left-color: #ef4444;
        }
        
        .timeframe-selector {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
        }
        
        .timeframe-btn {
            background: #374151;
            color: #d1d5db;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .timeframe-btn.active {
            background: #2563eb;
            color: white;
        }
        
        .timeframe-btn:hover {
            background: #4b5563;
        }
        
        #chart {
            height: 600px;
            border-radius: 8px;
        }
        
        .connection-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .connected { background: #10b981; }
        .disconnected { background: #ef4444; }
        
        .vwap-info {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        
        .vwap-item {
            background: rgba(59, 130, 246, 0.1);
            padding: 10px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        
        @media (max-width: 1200px) {
            .main-container {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }
    </style>
</head>
<body>
        <div class="header">
        <h1>🚀 Professional Trading Dashboard</h1>
        <div class="status-bar">
            <div class="status-item">
                <span class="connection-indicator" id="connection-dot"></span>
                <span id="connection-text">Connecting...</span>
            </div>
            <div class="status-item">
                📊 <span id="session-duration">00:00:00</span>
            </div>
            <div class="status-item">
                💰 <span id="current-symbol">BTCUSDT</span> • <span id="current-price">$0.00</span>
            </div>
        </div>
    </div>    <div class="main-container">
        <div class="chart-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div class="symbol-selector">
                    <select id="symbol-select" style="background: #374151; color: white; border: 1px solid #4b5563; padding: 8px 12px; border-radius: 6px;">
                        <option value="BTCUSDT">BTCUSDT</option>
                        <option value="SUIUSDT">SUIUSDT</option>
                        <option value="ETHUSDT">ETHUSDT</option>
                        <option value="SOLUSDT">SOLUSDT</option>
                    </select>
                </div>
                <div class="timeframe-selector">
                    <button class="timeframe-btn active" data-tf="1m">1m</button>
                    <button class="timeframe-btn" data-tf="5m">5m</button>
                    <button class="timeframe-btn" data-tf="15m">15m</button>
                    <button class="timeframe-btn" data-tf="1h">1h</button>
                </div>
            </div>
            <div id="chart">Loading professional chart...</div>
            
            <div class="vwap-info">
                <div class="vwap-item">
                    <div style="color: #ef4444; font-weight: bold;">VAH</div>
                    <div id="vah-price">$0.00</div>
                </div>
                <div class="vwap-item">
                    <div style="color: #f59e0b; font-weight: bold;">POC</div>
                    <div id="poc-price">$0.00</div>
                </div>
                <div class="vwap-item">
                    <div style="color: #10b981; font-weight: bold;">VAL</div>
                    <div id="val-price">$0.00</div>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="trades-count">0</div>
                    <div class="stat-label">Total Trades</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="whales-count">0</div>
                    <div class="stat-label">Whales (>2 BTC)</div>
                </div>
            </div>
            
            <div class="widget">
                <h3>🐋 Large Orders Stream</h3>
                <div class="orders-list" id="orders-container">
                    <div style="text-align: center; color: #6b7280; padding: 20px;">
                        Waiting for large orders...
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentTimeframe = '5m';
        let chartInitialized = false;
        let ordersList = [];
        
        let currentSymbol = 'BTCUSDT';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            setupTimeframeButtons();
            setupSymbolSelector();
            initializeChart();
            loadSymbolsData();
        });
        
        function setupTimeframeButtons() {
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentTimeframe = this.dataset.tf;
                    updateChart();
                });
            });
        }
        
        function setupSymbolSelector() {
            const symbolSelect = document.getElementById('symbol-select');
            symbolSelect.addEventListener('change', function() {
                switchSymbol(this.value);
            });
        }
        
        function loadSymbolsData() {
            fetch('/api/symbols')
                .then(response => response.json())
                .then(data => {
                    currentSymbol = data.current_symbol;
                    document.getElementById('symbol-select').value = currentSymbol;
                    document.getElementById('current-symbol').textContent = currentSymbol;
                    console.log('📊 Symbols loaded:', data.symbols);
                    console.log('🎯 Thresholds:', data.thresholds);
                });
        }
        
        function switchSymbol(newSymbol) {
            fetch('/api/switch-symbol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ symbol: newSymbol })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentSymbol = newSymbol;
                    document.getElementById('current-symbol').textContent = newSymbol;
                    ordersList = []; // Clear orders list
                    updateOrdersList();
                    updateChart();
                    console.log('🔄 Switched to:', newSymbol);
                } else {
                    console.error('❌ Failed to switch symbol:', data.error);
                }
            })
            .catch(err => console.error('❌ Switch error:', err));
        }
        
        function initializeChart() {
            const layout = {
                title: {
                    text: `BTCUSDT ${currentTimeframe.toUpperCase()} Candlesticks + Volume Profile`,
                    font: { color: 'white', size: 16 }
                },
                paper_bgcolor: '#1f2937',
                plot_bgcolor: '#111827',
                font: { color: 'white' },
                xaxis: { 
                    gridcolor: '#374151',
                    showgrid: true,
                    type: 'date'
                },
                yaxis: { 
                    gridcolor: '#374151',
                    showgrid: true,
                    title: 'Price ($)'
                },
                margin: { t: 60, b: 50, l: 60, r: 60 },
                showlegend: false
            };
            
            Plotly.newPlot('chart', [], layout, {responsive: true, displayModeBar: false});
            chartInitialized = true;
        }
        
        function updateChart() {
            if (!chartInitialized) return;
            
            fetch(`/api/candles?symbol=${currentSymbol}&timeframe=${currentTimeframe}&limit=100`)
                .then(response => response.json())
                .then(data => {
                    if (data.length === 0) return;
                    
                    const times = data.map(d => d.time);
                    const opens = data.map(d => d.open);
                    const highs = data.map(d => d.high);
                    const lows = data.map(d => d.low);
                    const closes = data.map(d => d.close);
                    const volumes = data.map(d => d.volume);
                    
                    const candlestickTrace = {
                        x: times,
                        open: opens,
                        high: highs,
                        low: lows,
                        close: closes,
                        type: 'candlestick',
                        name: 'BTCUSDT',
                        increasing: { line: { color: '#10b981' } },
                        decreasing: { line: { color: '#ef4444' } }
                    };
                    
                    Plotly.newPlot('chart', [candlestickTrace], {
                        title: {
                            text: `${currentSymbol} ${currentTimeframe.toUpperCase()} Candlesticks + Large Orders`,
                            font: { color: 'white', size: 16 }
                        },
                        paper_bgcolor: '#1f2937',
                        plot_bgcolor: '#111827',
                        font: { color: 'white' },
                        xaxis: { 
                            gridcolor: '#374151',
                            showgrid: true,
                            type: 'date'
                        },
                        yaxis: { 
                            gridcolor: '#374151',
                            showgrid: true,
                            title: 'Price ($)'
                        },
                        margin: { t: 60, b: 50, l: 60, r: 60 },
                        showlegend: false
                    }, {responsive: true, displayModeBar: false});
                    
                    // Add existing large orders as bubbles
                    addExistingBubbles();
                })
                .catch(err => console.error('Chart update error:', err));
        }
        
        function addExistingBubbles() {
            fetch(`/api/large-orders?symbol=${currentSymbol}&limit=20`)
                .then(response => response.json())
                .then(orders => {
                    orders.forEach(order => {
                        addBubbleToChart(order, false);
                    });
                });
        }
        
        function addBubbleToChart(order, animate = true) {
            const color = order.side === 'buy' ? '#10b981' : '#ef4444';
            const size = Math.min(40, Math.max(15, order.volume * 6));
            
            const bubbleTrace = {
                x: [new Date(order.timestamp * 1000)],
                y: [order.price],
                mode: 'markers',
                type: 'scatter',
                name: `${order.side.toUpperCase()} ${order.volume.toFixed(2)}`,
                marker: {
                    size: [size],
                    color: color,
                    opacity: 0.8,
                    symbol: 'circle',
                    line: { width: 2, color: 'white' }
                },
                showlegend: false,
                text: [`🐋 ${order.side.toUpperCase()}: ${order.volume.toFixed(2)} BTC<br>💰 Price: $${order.price.toLocaleString()}<br>📊 Value: $${order.value.toLocaleString()}<br>⏰ ${order.time}`],
                hovertemplate: '%{text}<extra></extra>'
            };
            
            Plotly.addTraces('chart', bubbleTrace);
            
            if (animate) {
                // Flash effect
                setTimeout(() => {
                    const chartDiv = document.getElementById('chart');
                    if (chartDiv.data && chartDiv.data.length > 50) {
                        Plotly.deleteTraces('chart', 1);
                    }
                }, 30000); // Remove after 30 seconds
            }
        }
        
        // Socket events
        socket.on('connect', function() {
            console.log('🔌 Connected');
            updateConnectionStatus(true);
            updateChart();
        });
        
        socket.on('disconnect', function() {
            console.log('❌ Disconnected');
            updateConnectionStatus(false);
        });
        
        socket.on('stats_update', function(data) {
            document.getElementById('trades-count').textContent = data.trades_count.toLocaleString();
            document.getElementById('whales-count').textContent = data.large_orders_count;
            document.getElementById('current-price').textContent = '$' + data.current_price.toLocaleString(undefined, {minimumFractionDigits: 2});
            
            // Update session duration
            const duration = formatDuration(data.session_duration);
            document.getElementById('session-duration').textContent = duration;
            
            // Update POC/VAH/VAL
            if (data.poc_price) {
                document.getElementById('poc-price').textContent = '$' + data.poc_price.toLocaleString();
                document.getElementById('vah-price').textContent = '$' + data.vah_price.toLocaleString();
                document.getElementById('val-price').textContent = '$' + data.val_price.toLocaleString();
            }
        });
        
        socket.on('large_order', function(order) {
            console.log('🐋 Large order:', order);
            
            // Only show orders for current symbol
            if (order.symbol === currentSymbol) {
                // Add to orders list
                ordersList.unshift(order);
                if (ordersList.length > 20) ordersList.pop();
                updateOrdersList();
                
                // Add bubble to chart
                addBubbleToChart(order, true);
            }
        });
        
        function updateConnectionStatus(connected) {
            const dot = document.getElementById('connection-dot');
            const text = document.getElementById('connection-text');
            
            if (connected) {
                dot.className = 'connection-indicator connected';
                text.textContent = 'Live Connected';
            } else {
                dot.className = 'connection-indicator disconnected';
                text.textContent = 'Disconnected';
            }
        }
        
        function updateOrdersList() {
            const container = document.getElementById('orders-container');
            
            if (ordersList.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 20px;">Waiting for large orders...</div>';
                return;
            }
            
            container.innerHTML = ordersList.map(order => {
                const sideClass = order.side === 'buy' ? 'buy-order' : 'sell-order';
                const sideEmoji = order.side === 'buy' ? '🟢' : '🔴';
                const impact = order.impact_score ? ` (${order.impact_score.toFixed(0)}%)` : '';
                
                return `
                    <div class="order-item ${sideClass}">
                        <div>
                            <div style="font-weight: bold;">
                                ${sideEmoji} ${order.side.toUpperCase()} ${order.volume.toFixed(4)} BTC
                            </div>
                            <div style="font-size: 12px; color: #9ca3af;">
                                $${order.price.toLocaleString()} • $${order.value.toLocaleString()}${impact}
                            </div>
                        </div>
                        <div style="text-align: right; font-size: 11px; color: #6b7280;">
                            ${order.time}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function formatDuration(seconds) {
            const hrs = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Auto-update chart every 30 seconds
        setInterval(() => {
            if (currentTimeframe) {
                updateChart();
            }
        }, 30000);
        
        console.log('🚀 Professional Dashboard Ready');
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(PROFESSIONAL_TEMPLATE)

@app.route('/api/candles')
def get_candles():
    symbol = request.args.get('symbol', dashboard.current_symbol)
    timeframe = request.args.get('timeframe', '5m')
    limit = int(request.args.get('limit', 100))
    return jsonify(dashboard.get_candle_data(symbol, timeframe, limit))

@app.route('/api/large-orders')
def get_large_orders():
    symbol = request.args.get('symbol', dashboard.current_symbol)
    limit = int(request.args.get('limit', 20))
    return jsonify(dashboard.get_large_orders_recent(symbol, limit))

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
        'thresholds': {symbol: dashboard._get_large_order_threshold(symbol) for symbol in dashboard.symbols}
    })

@app.route('/api/debug')
def debug():
    # Get stats for current symbol
    current_stats = dashboard.stats.get(dashboard.current_symbol, {})
    
    return jsonify({
        'trades_count': current_stats.get('trades_count', 0),
        'large_orders_count': current_stats.get('large_orders_count', 0),
        'current_price': current_stats.get('current_price', 0.0),
        'connection_active': dashboard.connection_active,
        'current_symbol': dashboard.current_symbol,
        'all_symbols_stats': dashboard.stats,
        'candle_data_lengths': {symbol: {tf: len(candles) for tf, candles in data.items()} 
                               for symbol, data in dashboard.candle_data.items()},
        'volume_profile_levels': {symbol: len(vp) for symbol, vp in dashboard.volume_profile.items()}
    })

@socketio.on('connect')
def handle_connect():
    print("👤 Professional client connected")
    dashboard.start_websocket()

if __name__ == '__main__':
    print("🚀 Professional Dashboard Starting...")
    print("🌐 URL: http://localhost:5006")
    print("🕯️ Multi-timeframe candlesticks")
    print("📊 Volume Profile with POC/VAH/VAL") 
    print("🐋 Large orders with bubbles")
    print("📈 Historical data storage")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5006)