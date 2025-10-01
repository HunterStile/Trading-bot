#!/usr/bin/env python3
"""
🚀 Professional TradingView Dashboard
Enhanced trading dashboard with TradingView Charting Library + Custom Analytics

Features:
- Professional TradingView charts
- Real-time Bybit WebSocket data
- Custom volume profile analysis
- Whale detection system  
- Order flow analytics
- Multi-symbol support
"""

import asyncio
import json
import threading
import time
import websockets
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
from collections import defaultdict, deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tradingview_professional_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class TradingViewDashboard:
    def __init__(self):
        # Supported symbols
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'SUIUSDT', 'SOLUSDT']
        self.current_symbol = 'BTCUSDT'
        
        # Data storage
        self.ohlcv_data = {}  # For TradingView
        self.volume_profile = {}
        self.whale_orders = {}
        self.order_flow = {}
        
        # Stats tracking
        self.stats = {}
        
        # Initialize data structures
        self._initialize_data_structures()
        
        # WebSocket connection
        self.connection_active = False
        self.ws_urls = [
            "wss://stream.bybit.com/v5/public/linear",
            "wss://stream-testnet.bybit.com/v5/public/linear"
        ]
        self.current_ws_url = 0
        self.ws_thread = None
        
        print("🚀 TradingView Professional Dashboard initialized")
    
    def _initialize_data_structures(self):
        """Initialize all data structures for all symbols"""
        for symbol in self.symbols:
            # OHLCV data for TradingView (1 minute bars)
            self.ohlcv_data[symbol] = {
                'time': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': []
            }
            
            # Volume Profile data
            self.volume_profile[symbol] = {}
            
            # Whale orders (large orders)
            self.whale_orders[symbol] = deque(maxlen=100)
            
            # Order flow analysis
            self.order_flow[symbol] = {
                'buy_volume': 0,
                'sell_volume': 0,
                'delta': 0,
                'cumulative_delta': 0
            }
            
            # Statistics
            self.stats[symbol] = {
                'trades_count': 0,
                'whale_count': 0,
                'current_price': 0.0,
                'session_start': time.time(),
                'volume_24h': 0.0
            }
    
    def start_websocket(self):
        """Start WebSocket connection in background thread"""
        if self.ws_thread is None or not self.ws_thread.is_alive():
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            print("🔴 WebSocket thread started")
    
    def _run_websocket(self):
        """Run WebSocket in asyncio loop"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._websocket_loop())
    
    async def _websocket_loop(self):
        """Main WebSocket connection loop"""
        while True:
            try:
                current_url = self.ws_urls[self.current_ws_url]
                print(f"🔌 Connecting to {current_url}")
                
                async with websockets.connect(
                    current_url,
                    ping_interval=20,
                    ping_timeout=10,
                    open_timeout=10
                ) as websocket:
                    self.connection_active = True
                    print("✅ WebSocket connected")
                    
                    # Subscribe to all symbols
                    subscribe_args = [f"publicTrade.{symbol}" for symbol in self.symbols]
                    await websocket.send(json.dumps({
                        "op": "subscribe",
                        "args": subscribe_args
                    }))
                    print(f"📡 Subscribed to: {', '.join(self.symbols)}")
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._process_message(message)
                        
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                self.connection_active = False
                
                # Try next URL
                self.current_ws_url = (self.current_ws_url + 1) % len(self.ws_urls)
                if self.current_ws_url == 0:
                    await asyncio.sleep(10)
                else:
                    await asyncio.sleep(2)
    
    async def _process_message(self, message):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if "topic" in data and "publicTrade" in data["topic"]:
                for trade_data in data["data"]:
                    await self._process_trade(trade_data)
        except Exception as e:
            print(f"❌ Message processing error: {e}")
    
    async def _process_trade(self, trade_data):
        """Process individual trade"""
        try:
            symbol = trade_data.get("s")
            if symbol not in self.symbols:
                return
                
            price = float(trade_data["p"])
            volume = float(trade_data["v"])
            side = 'buy' if trade_data["S"] == "Buy" else 'sell'
            timestamp = int(trade_data["T"]) / 1000
            
            # Update stats
            self.stats[symbol]['trades_count'] += 1
            self.stats[symbol]['current_price'] = price
            
            # Update order flow
            if side == 'buy':
                self.order_flow[symbol]['buy_volume'] += volume
                self.order_flow[symbol]['delta'] += volume
            else:
                self.order_flow[symbol]['sell_volume'] += volume
                self.order_flow[symbol]['delta'] -= volume
            
            self.order_flow[symbol]['cumulative_delta'] += self.order_flow[symbol]['delta']
            
            # Check for whale orders
            threshold = self._get_whale_threshold(symbol)
            if volume >= threshold:
                whale_order = {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'side': side,
                    'timestamp': timestamp,
                    'value': price * volume,
                    'time': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                }
                
                self.whale_orders[symbol].append(whale_order)
                self.stats[symbol]['whale_count'] += 1
                
                print(f"🐋 WHALE {symbol}: {side} {volume:.2f} @ ${price:,.2f}")
                
                # Emit whale order to frontend
                socketio.emit('whale_order', whale_order)
            
            # Update OHLCV data (1-minute candles)
            self._update_ohlcv(symbol, price, volume, timestamp)
            
            # Update volume profile
            self._update_volume_profile(symbol, price, volume)
            
            # Emit real-time updates
            socketio.emit('trade_update', {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'side': side,
                'timestamp': timestamp
            })
            
        except Exception as e:
            print(f"❌ Trade processing error: {e}")
    
    def _get_whale_threshold(self, symbol):
        """Get whale detection threshold for symbol"""
        thresholds = {
            'BTCUSDT': 2.0,
            'ETHUSDT': 50.0,
            'SUIUSDT': 10000.0,
            'SOLUSDT': 500.0
        }
        return thresholds.get(symbol, 1000.0)
    
    def _update_ohlcv(self, symbol, price, volume, timestamp):
        """Update OHLCV data for TradingView"""
        # Convert to minute timestamp
        minute_ts = int(timestamp // 60) * 60
        
        ohlcv = self.ohlcv_data[symbol]
        
        # Check if we have data for this minute
        if ohlcv['time'] and ohlcv['time'][-1] == minute_ts:
            # Update existing candle
            idx = -1
            ohlcv['high'][idx] = max(ohlcv['high'][idx], price)
            ohlcv['low'][idx] = min(ohlcv['low'][idx], price)
            ohlcv['close'][idx] = price
            ohlcv['volume'][idx] += volume
        else:
            # New candle
            ohlcv['time'].append(minute_ts)
            ohlcv['open'].append(price)
            ohlcv['high'].append(price)
            ohlcv['low'].append(price)
            ohlcv['close'].append(price)
            ohlcv['volume'].append(volume)
            
            # Keep only last 1000 candles
            if len(ohlcv['time']) > 1000:
                for key in ohlcv:
                    ohlcv[key] = ohlcv[key][-1000:]
    
    def _update_volume_profile(self, symbol, price, volume):
        """Update volume profile data"""
        # Round price to nearest tick
        price_level = round(price, 2)
        
        if price_level not in self.volume_profile[symbol]:
            self.volume_profile[symbol][price_level] = 0
        
        self.volume_profile[symbol][price_level] += volume
    
    def get_volume_profile_data(self, symbol):
        """Get volume profile data with POC, VAH, VAL"""
        if symbol not in self.volume_profile or not self.volume_profile[symbol]:
            return {'poc': 0, 'vah': 0, 'val': 0, 'profile': []}
        
        profile = self.volume_profile[symbol]
        total_volume = sum(profile.values())
        
        if total_volume == 0:
            return {'poc': 0, 'vah': 0, 'val': 0, 'profile': []}
        
        # Find POC (Point of Control)
        poc_price = max(profile.keys(), key=lambda k: profile[k])
        
        # Calculate Value Area (70% of volume)
        sorted_levels = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        value_area_volume = 0
        value_area_prices = []
        
        for price, vol in sorted_levels:
            value_area_volume += vol
            value_area_prices.append(price)
            if value_area_volume >= total_volume * 0.7:
                break
        
        vah = max(value_area_prices) if value_area_prices else poc_price
        val = min(value_area_prices) if value_area_prices else poc_price
        
        # Format profile data
        profile_data = [
            {'price': price, 'volume': volume}
            for price, volume in sorted(profile.items())
        ]
        
        return {
            'poc': poc_price,
            'vah': vah,
            'val': val,
            'profile': profile_data
        }

# Initialize dashboard
dashboard = TradingViewDashboard()

# TradingView Professional Template
TRADINGVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🚀 TradingView Professional Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- TradingView Widget Script (Public Version) -->
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    
    <!-- Socket.IO -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            background: #131722; 
            color: #d1d4dc; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow: hidden;
        }
        
        /* Header */
        .header {
            height: 60px;
            background: #1e222d;
            border-bottom: 1px solid #2a2d3a;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            position: relative;
            z-index: 1000;
        }
        
        .logo {
            display: flex;
            align-items: center;
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .status-indicators {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #2a2d3a;
            border-radius: 6px;
            font-size: 12px;
        }
        
        .connection-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Main Layout */
        .main-container {
            display: flex;
            height: calc(100vh - 60px);
        }
        
        /* Symbol Selector */
        .symbol-selector {
            width: 200px;
            background: #1e222d;
            border-right: 1px solid #2a2d3a;
            padding: 20px;
        }
        
        .symbol-list {
            list-style: none;
        }
        
        .symbol-item {
            padding: 12px 16px;
            margin: 4px 0;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .symbol-item:hover {
            background: #2a2d3a;
        }
        
        .symbol-item.active {
            background: #1f4ed8;
            color: white;
        }
        
        .symbol-price {
            font-size: 11px;
            opacity: 0.7;
        }
        
        /* Chart Container */
        .chart-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        /* TradingView Chart */
        #tradingview_chart {
            flex: 1;
            background: #131722;
        }
        
        /* Analytics Sidebar */
        .analytics-sidebar {
            width: 300px;
            background: #1e222d;
            border-left: 1px solid #2a2d3a;
            display: flex;
            flex-direction: column;
        }
        
        .analytics-section {
            padding: 20px;
            border-bottom: 1px solid #2a2d3a;
        }
        
        .section-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #ffffff;
        }
        
        /* Volume Profile */
        .volume-profile {
            height: 200px;
            background: #131722;
            border-radius: 4px;
            padding: 10px;
        }
        
        /* Whale Orders */
        .whale-orders {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .whale-order {
            padding: 8px 12px;
            margin: 4px 0;
            background: #2a2d3a;
            border-radius: 4px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .whale-order.buy {
            border-left: 3px solid #22c55e;
        }
        
        .whale-order.sell {
            border-left: 3px solid #ef4444;
        }
        
        .whale-volume {
            font-weight: 600;
        }
        
        .whale-price {
            color: #888;
        }
        
        /* Order Flow */
        .order-flow-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .flow-stat {
            text-align: center;
            padding: 10px;
            background: #131722;
            border-radius: 4px;
        }
        
        .flow-label {
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 4px;
        }
        
        .flow-value {
            font-size: 14px;
            font-weight: 600;
        }
        
        .flow-value.positive { color: #22c55e; }
        .flow-value.negative { color: #ef4444; }
        


        /* Trade Statistics */
        #trade-stats {
            background: rgba(34, 34, 34, 0.8);
            border: 1px solid #444;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }

        .stat-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stat-label {
            color: #888;
            font-weight: 500;
        }

        .stat-value {
            color: #fff;
            font-weight: bold;
        }

        .stat-value.buy {
            color: #00ff88;
        }

        .stat-value.sell {
            color: #ff4444;
        }

        /* Whale Orders */
        #whale-orders {
            max-height: 300px;
            overflow-y: auto;
            background: rgba(34, 34, 34, 0.8);
            border: 1px solid #444;
            border-radius: 8px;
            padding: 10px;
        }

        .whale-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 6px;
            border-left: 4px solid;
        }

        .whale-item.buy {
            background: rgba(0, 255, 136, 0.1);
            border-left-color: #00ff88;
        }

        .whale-item.sell {
            background: rgba(255, 68, 68, 0.1);
            border-left-color: #ff4444;
        }

        .whale-info {
            display: flex;
            gap: 15px;
        }

        .whale-price, .whale-volume {
            font-weight: bold;
            color: #fff;
        }

        .whale-side {
            font-weight: bold;
            text-transform: uppercase;
        }

        .whale-item.buy .whale-side {
            color: #00ff88;
        }

        .whale-item.sell .whale-side {
            color: #ff4444;
        }

        .whale-time {
            font-size: 12px;
            color: #888;
        }

        /* Whale Notifications */
        .whale-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(34, 34, 34, 0.95);
            border: 2px solid;
            border-radius: 12px;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            min-width: 300px;
        }

        .whale-notification.buy {
            border-color: #00ff88;
            box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
        }

        .whale-notification.sell {
            border-color: #ff4444;
            box-shadow: 0 4px 20px rgba(255, 68, 68, 0.3);
        }

        .notification-icon {
            font-size: 24px;
        }

        .notification-title {
            font-weight: bold;
            color: #fff;
            margin-bottom: 4px;
        }

        .notification-details {
            color: #ccc;
            font-size: 14px;
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        /* Volume Profile */
        #volume-profile {
            background: rgba(34, 34, 34, 0.8);
            border: 1px solid #444;
            border-radius: 8px;
            padding: 15px;
        }

        .profile-info {
            display: grid;
            gap: 8px;
        }

        .profile-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .profile-label {
            color: #888;
            font-weight: 500;
        }

        .profile-value {
            color: #fff;
            font-weight: bold;
        }

        /* Whale Bubbles on Chart */
        .whale-bubble {
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
        }

        .whale-bubble:hover {
            transform: scale(1.1);
            z-index: 1001 !important;
        }

        .whale-bubble.buy {
            border-color: #00ff88;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }

        .whale-bubble.sell {
            border-color: #ff4444;
            box-shadow: 0 0 20px rgba(255, 68, 68, 0.5);
        }

        .bubble-content {
            text-align: center;
            color: white;
            font-size: 10px;
            line-height: 1.2;
        }

        .bubble-icon {
            font-size: 16px;
            margin-bottom: 2px;
        }

        .bubble-side {
            font-weight: bold;
            text-transform: uppercase;
        }

        .whale-bubble.buy .bubble-side {
            color: #00ff88;
        }

        .whale-bubble.sell .bubble-side {
            color: #ff4444;
        }

        .bubble-volume, .bubble-price {
            font-size: 8px;
            margin: 1px 0;
        }

        @keyframes bubbleAppear {
            0% {
                transform: scale(0) rotate(0deg);
                opacity: 0;
            }
            50% {
                transform: scale(1.2) rotate(180deg);
            }
            100% {
                transform: scale(1) rotate(360deg);
                opacity: 1;
            }
        }

        @keyframes bubbleDisappear {
            0% {
                transform: scale(1);
                opacity: 1;
            }
            100% {
                transform: scale(0);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="logo">
            🚀 TradingView Professional Dashboard
        </div>
        <div class="status-indicators">
            <div class="status-item">
                <div class="connection-dot"></div>
                <span id="connection-status">Live Connected</span>
            </div>
            <div class="status-item">
                📊 <span id="session-timer">00:00:00</span>
            </div>
            <div class="status-item">
                💰 <span id="current-symbol">BTCUSDT</span> • $<span id="current-price">0.00</span>
            </div>
        </div>
    </div>
    
    <!-- Main Container -->
    <div class="main-container">
        <!-- Symbol Selector -->
        <div class="symbol-selector">
            <h3 class="section-title">Symbols</h3>
            <ul class="symbol-list" id="symbol-list">
                <li class="symbol-item active" data-symbol="BTCUSDT">
                    <span>BTCUSDT</span>
                    <span class="symbol-price">$0.00</span>
                </li>
                <li class="symbol-item" data-symbol="ETHUSDT">
                    <span>ETHUSDT</span>
                    <span class="symbol-price">$0.00</span>
                </li>
                <li class="symbol-item" data-symbol="SUIUSDT">
                    <span>SUIUSDT</span>
                    <span class="symbol-price">$0.00</span>
                </li>
                <li class="symbol-item" data-symbol="SOLUSDT">
                    <span>SOLUSDT</span>
                    <span class="symbol-price">$0.00</span>
                </li>
            </ul>
        </div>
        
        <!-- Chart Container -->
        <div class="chart-container">
            <div id="tradingview_chart"></div>
        </div>
        
        <!-- Analytics Sidebar -->
        <div class="analytics-sidebar">
            <!-- Real-time Trade Data -->
            <div class="analytics-section">
                <h3 class="section-title">⚡ Live Data</h3>
                <div id="trade-stats">
                    <div style="text-align: center; padding: 20px; opacity: 0.5;">
                        Connecting to live data...
                    </div>
                </div>
            </div>
            
            <!-- Volume Profile -->
            <div class="analytics-section">
                <h3 class="section-title">📊 Volume Profile</h3>
                <div class="volume-profile" id="volume-profile">
                    <div style="text-align: center; padding: 20px; opacity: 0.5;">
                        Waiting for data...
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 12px;">
                    <div>POC: $<span id="poc-price">0.00</span></div>
                    <div>VAH: $<span id="vah-price">0.00</span></div>
                    <div>VAL: $<span id="val-price">0.00</span></div>
                </div>
            </div>
            
            <!-- Whale Orders -->
            <div class="analytics-section">
                <h3 class="section-title">🐋 Whale Orders</h3>
                <div id="whale-orders">
                    <div style="text-align: center; padding: 20px; opacity: 0.5;">
                        No whale orders yet...
                    </div>
                </div>
            </div>
            
            <!-- Order Flow -->
            <div class="analytics-section">
                <h3 class="section-title">📈 Order Flow</h3>
                <div class="order-flow-stats">
                    <div class="flow-stat">
                        <div class="flow-label">Buy Volume</div>
                        <div class="flow-value positive" id="buy-volume">0</div>
                    </div>
                    <div class="flow-stat">
                        <div class="flow-label">Sell Volume</div>
                        <div class="flow-value negative" id="sell-volume">0</div>
                    </div>
                    <div class="flow-stat">
                        <div class="flow-label">Delta</div>
                        <div class="flow-value" id="delta">0</div>
                    </div>
                    <div class="flow-stat">
                        <div class="flow-label">Cum. Delta</div>
                        <div class="flow-value" id="cumulative-delta">0</div>
                    </div>
                </div>
            </div>
            
            <!-- Whale Orders -->
            <div class="analytics-section">
                <h3 class="section-title">🐋 Large Orders</h3>
                <div id="whale-orders">
                    <div style="text-align: center; padding: 20px; opacity: 0.5;">
                        Waiting for whales...
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        console.log('🚀 TradingView Professional Dashboard Loading...');
        
        // Initialize Socket.IO
        const socket = io();
        
        // Global state
        let currentSymbol = 'BTCUSDT';
        let sessionStart = Date.now();
        let tvWidget = null;
        
        // Initialize Dashboard
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📊 Initializing TradingView Dashboard...');
            
            // This will be implemented in the next step
            initializeTradingView();
            initializeEventListeners();
            startSessionTimer();
            

        });
        
        function initializeTradingView() {
            console.log('📈 Setting up TradingView widget...');
            
            // TradingView Widget Configuration
            const widgetOptions = {
                symbol: "BYBIT:BTCUSDT",
                interval: "1",
                timezone: "Europe/Rome",
                theme: "dark",
                style: "1",
                locale: "en",
                toolbar_bg: "#1e222d",
                enable_publishing: false,
                hide_top_toolbar: false,
                hide_legend: false,
                save_image: true,
                container_id: "tradingview_chart",
                width: "100%",
                height: "100%",
                autosize: true,
                studies: [
                    "Volume@tv-basicstudies",
                    "MASimple@tv-basicstudies"
                ],
                disabled_features: [
                    "use_localstorage_for_settings",
                    "header_symbol_search",
                    "header_saveload",
                    "study_dialog_search_control",
                    "symbol_search_hot_key"
                ],
                enabled_features: [
                    "hide_left_toolbar_by_default"
                ],
                overrides: {
                    "paneProperties.background": "#131722",
                    "paneProperties.vertGridProperties.color": "#2a2d3a",
                    "paneProperties.horzGridProperties.color": "#2a2d3a",
                    "symbolWatermarkProperties.transparency": 90,
                    "scalesProperties.textColor": "#AAA",
                    "mainSeriesProperties.candleStyle.upColor": "#22c55e",
                    "mainSeriesProperties.candleStyle.downColor": "#ef4444",
                    "mainSeriesProperties.candleStyle.borderUpColor": "#22c55e",
                    "mainSeriesProperties.candleStyle.borderDownColor": "#ef4444",
                    "mainSeriesProperties.candleStyle.wickUpColor": "#22c55e",
                    "mainSeriesProperties.candleStyle.wickDownColor": "#ef4444",
                    "volumePaneSize": "medium"
                }
            };
            
            // Check if TradingView is loaded
            if (typeof TradingView !== 'undefined') {
                console.log('✅ TradingView library loaded, creating widget...');
                
                tvWidget = new TradingView.widget(widgetOptions);
                
                tvWidget.onChartReady(() => {
                    console.log('✅ TradingView chart ready!');
                    

                    
                    // Setup custom overlays after chart is ready
                    setupCustomOverlays();
                });
                
            } else {
                console.error('❌ TradingView library not loaded');
                // Fallback - load from CDN
                loadTradingViewFromCDN();
            }
        }
        
        function loadTradingViewFromCDN() {
            console.log('🔄 Loading TradingView from alternative CDN...');
            

            
            // Create TradingView widget using public widget
            const script = document.createElement('script');
            script.src = 'https://s3.tradingview.com/tv.js';
            script.onload = function() {
                console.log('✅ TradingView public widget loaded');
                createPublicTradingViewWidget();
            };
            script.onerror = function() {
                console.error('❌ Failed to load TradingView');
                showTradingViewError();
            };
            document.head.appendChild(script);
        }
        
        function createPublicTradingViewWidget() {
            // Use TradingView public widget as fallback
            const tvSymbol = `BYBIT:${currentSymbol}`;
            
            new TradingView.widget({
                "width": "100%",
                "height": "100%",
                "symbol": tvSymbol,
                "interval": "1",
                "timezone": "Europe/Rome",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#1e222d",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "hide_legend": false,
                "save_image": true,
                "container_id": "tradingview_chart",
                "autosize": true
            });
            
            console.log(`✅ Public TradingView widget created with symbol: ${tvSymbol}`);
        }

        function showTradingViewError() {
            console.error('❌ All TradingView loading methods failed');
            const loadingElement = document.getElementById('loading');
            if (loadingElement) {
                loadingElement.innerHTML = `
                    <div style="color: #ff4444; text-align: center;">
                        <div>❌ Unable to load TradingView charts</div>
                        <div style="font-size: 14px; margin-top: 10px;">
                            Please check your internet connection and refresh the page
                        </div>
                        <button onclick="location.reload()" style="margin-top: 15px; padding: 8px 16px; background: #333; color: white; border: 1px solid #555; border-radius: 4px; cursor: pointer;">
                            Retry
                        </button>
                    </div>
                `;
            }
        }
        
        function showTradingViewError() {
            document.getElementById('loading').innerHTML = `
                <div class="spinner"></div>
                <div>❌ TradingView loading failed</div>
                <div style="font-size: 12px; margin-top: 10px; opacity: 0.7;">
                    Using fallback chart...
                </div>
            `;
            
            // Create basic fallback chart
            setTimeout(() => {
                createFallbackChart();
            }, 2000);
        }
        
        function createFallbackChart() {
            const container = document.getElementById('tradingview_chart');
            container.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #131722; color: #d1d4dc;">
                    <div style="text-align: center;">
                        <h3>📈 Real-Time Data Feed Active</h3>
                        <p style="margin: 10px 0; opacity: 0.7;">Professional chart loading...</p>
                        <div id="price-display" style="font-size: 24px; font-weight: bold; color: #22c55e;">
                            $0.00
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('loading').style.display = 'none';
        }
        
        function setupCustomOverlays() {
            console.log('🔬 Setting up custom analytics overlays...');
            
            // This is where we'll add our whale bubbles and volume profile overlays
            // after TradingView chart is ready
            
            // Enable real-time data updates to TradingView
            enableRealTimeDataFeed();
        }
        
        function enableRealTimeDataFeed() {
            console.log('⚡ Enabling real-time data feed to TradingView...');
            
            // Update TradingView symbol when switching
            socket.on('symbol_switched', function(data) {
                if (tvWidget && tvWidget.chart) {
                    const symbol = `BYBIT:${data.symbol}`;
                    tvWidget.chart().setSymbol(symbol);
                    console.log(`🔄 TradingView switched to ${symbol}`);
                }
            });
        }
        
        function initializeEventListeners() {
            // Symbol selection
            document.querySelectorAll('.symbol-item').forEach(item => {
                console.log('🔧 Adding click listener to:', item.dataset.symbol);
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const symbol = this.dataset.symbol;
                    console.log('🖱️ Symbol clicked:', symbol);
                    switchSymbol(symbol);
                });
            });
            
            // Socket events
            socket.on('connect', function() {
                console.log('✅ Socket connected');
                updateConnectionStatus(true);
            });
            
            socket.on('disconnect', function() {
                console.log('❌ Socket disconnected');
                updateConnectionStatus(false);
            });
            
            socket.on('trade_update', function(data) {
                if (data.symbol === currentSymbol) {
                    updateTradeData(data);
                    updateTradingViewData(data);
                }
            });
            
            socket.on('whale_order', function(data) {
                console.log('🐋 Received whale order:', data);
                if (data.symbol === currentSymbol) {
                    console.log('🐋 Processing whale order for current symbol:', currentSymbol);
                    addWhaleOrder(data);
                    showWhaleNotification(data);
                    // Add bubble to TradingView chart
                    addTradingViewBubble(data);
                } else {
                    console.log('🐋 Ignoring whale order for different symbol:', data.symbol, 'current:', currentSymbol);
                }
            });
            
            socket.on('volume_profile', function(data) {
                if (data.symbol === currentSymbol) {
                    updateVolumeProfile(data);
                }
            });
        }
        
        function switchSymbol(symbol) {
            currentSymbol = symbol;
            
            // Update UI
            document.querySelectorAll('.symbol-item').forEach(item => {
                item.classList.toggle('active', item.dataset.symbol === symbol);
            });
            
            document.getElementById('current-symbol').textContent = symbol;
            
            // Update TradingView chart
            if (tvWidget && tvWidget.chart && typeof tvWidget.chart().setSymbol === 'function') {
                // Advanced widget with API access
                const tvSymbol = `BYBIT:${symbol}`;
                try {
                    tvWidget.chart().setSymbol(tvSymbol);
                    console.log(`📈 TradingView updated to ${tvSymbol}`);
                } catch (e) {
                    console.warn('❌ Could not update symbol via API, recreating widget:', e);
                    recreateTradingViewWidget(symbol);
                }
            } else {
                // Public widget or widget without API - need to recreate
                console.log('🔄 Recreating TradingView widget for symbol change');
                recreateTradingViewWidget(symbol);
            }
            
            // Notify backend
            socket.emit('switch_symbol', { symbol: symbol });
            
            console.log(`🔄 Switched to ${symbol}`);
        }

        function recreateTradingViewWidget(symbol) {
            // Clear existing widget
            const container = document.getElementById('tradingview_chart');
            if (container) {
                container.innerHTML = '';
            }
            
            // Create new widget with selected symbol
            const tvSymbol = `BYBIT:${symbol}`;
            
            new TradingView.widget({
                "width": "100%",
                "height": "100%",
                "symbol": tvSymbol,
                "interval": "1",
                "timezone": "Europe/Rome",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#1e222d",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "hide_legend": false,
                "save_image": true,
                "container_id": "tradingview_chart",
                "autosize": true
            });
            
            console.log(`✅ TradingView widget recreated with symbol: ${tvSymbol}`);
        }

        function updateTradingViewData(data) {
            // Update real-time data for TradingView overlays
            console.log('📊 Updating TradingView data:', data);
            
            // Future: Add custom overlays here
            // This will integrate with TradingView's Drawing API
        }

        function updateTradeData(data) {
            // Update trade statistics
            const stats = document.getElementById('trade-stats');
            if (stats && data.price) {
                stats.innerHTML = `
                    <div class="stat-item">
                        <span class="stat-label">Price:</span>
                        <span class="stat-value">$${data.price.toFixed(2)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Volume:</span>
                        <span class="stat-value">${data.volume.toFixed(4)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Side:</span>
                        <span class="stat-value ${data.side}">${data.side.toUpperCase()}</span>
                    </div>
                `;
            }
        }

        function addWhaleOrder(data) {
            console.log('🐋 Whale order detected:', data);
            
            // Add to whale orders list
            const whaleList = document.getElementById('whale-orders');
            if (whaleList) {
                const whaleItem = document.createElement('div');
                whaleItem.className = `whale-item ${data.side}`;
                whaleItem.innerHTML = `
                    <div class="whale-info">
                        <span class="whale-price">$${data.price.toFixed(2)}</span>
                        <span class="whale-volume">${data.volume.toFixed(2)}</span>
                        <span class="whale-side">${data.side.toUpperCase()}</span>
                    </div>
                    <div class="whale-time">${new Date().toLocaleTimeString()}</div>
                `;
                
                whaleList.insertBefore(whaleItem, whaleList.firstChild);
                
                // Keep only last 20 whale orders
                while (whaleList.children.length > 20) {
                    whaleList.removeChild(whaleList.lastChild);
                }
            }
        }

        function showWhaleNotification(data) {
            // Show floating notification
            const notification = document.createElement('div');
            notification.className = `whale-notification ${data.side}`;
            notification.innerHTML = `
                <div class="notification-icon">🐋</div>
                <div class="notification-content">
                    <div class="notification-title">Whale Order Detected!</div>
                    <div class="notification-details">
                        ${data.side.toUpperCase()} ${data.volume.toFixed(2)} at $${data.price.toFixed(2)}
                    </div>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }

        function updateVolumeProfile(data) {
            console.log('📊 Volume profile update:', data);
            
            // Update volume profile display
            const profileContainer = document.getElementById('volume-profile');
            if (profileContainer && data.profile) {
                // Display POC, VAH, VAL
                const profileInfo = document.createElement('div');
                profileInfo.className = 'profile-info';
                profileInfo.innerHTML = `
                    <div class="profile-item">
                        <span class="profile-label">POC:</span>
                        <span class="profile-value">$${data.poc.toFixed(2)}</span>
                    </div>
                    <div class="profile-item">
                        <span class="profile-label">VAH:</span>
                        <span class="profile-value">$${data.vah.toFixed(2)}</span>
                    </div>
                    <div class="profile-item">
                        <span class="profile-label">VAL:</span>
                        <span class="profile-value">$${data.val.toFixed(2)}</span>
                    </div>
                `;
                
                profileContainer.innerHTML = '';
                profileContainer.appendChild(profileInfo);
            }
        }

        function updateConnectionStatus(connected) {
            const status = document.getElementById('connection-status');
            if (status) {
                status.textContent = connected ? 'Connected' : 'Disconnected';
                status.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
            }
        }

        function addTradingViewBubble(whaleData) {
            console.log('🎯 Adding TradingView bubble:', whaleData);
            
            try {
                if (tvWidget && tvWidget.chart) {
                    const chart = tvWidget.chart();
                    
                    // Create a shape (bubble) for the whale order
                    const bubbleOptions = {
                        time: Math.floor(whaleData.timestamp / 1000), // Convert to seconds
                        price: whaleData.price,
                        shape: 'circle',
                        size: Math.min(Math.max(whaleData.volume / 100, 10), 50), // Dynamic size based on volume
                        color: whaleData.side === 'buy' ? '#00ff88' : '#ff4444',
                        text: `🐋 ${whaleData.side.toUpperCase()}\\n${whaleData.volume.toFixed(2)}\\n$${whaleData.price.toFixed(2)}`,
                        textColor: '#ffffff',
                        borderColor: whaleData.side === 'buy' ? '#00ff88' : '#ff4444',
                        borderWidth: 2,
                        transparency: 20
                    };
                    
                    // Add the shape to the chart
                    chart.createShape(bubbleOptions);
                    
                    console.log('✅ Bubble added to TradingView chart');
                } else {
                    console.log('⚠️ TradingView widget not ready for bubble');
                    
                    // Alternative: Add bubble overlay to chart container
                    addHTMLBubble(whaleData);
                }
            } catch (error) {
                console.error('❌ Error adding TradingView bubble:', error);
                
                // Fallback: Add HTML bubble
                addHTMLBubble(whaleData);
            }
        }

        function addHTMLBubble(whaleData) {
            console.log('🎯 Adding HTML bubble overlay:', whaleData);
            
            const chartContainer = document.getElementById('tradingview_chart');
            if (!chartContainer) return;
            
            const bubble = document.createElement('div');
            bubble.className = `whale-bubble ${whaleData.side}`;
            bubble.innerHTML = `
                <div class="bubble-content">
                    <div class="bubble-icon">🐋</div>
                    <div class="bubble-info">
                        <div class="bubble-side">${whaleData.side.toUpperCase()}</div>
                        <div class="bubble-volume">${whaleData.volume.toFixed(2)}</div>
                        <div class="bubble-price">$${whaleData.price.toFixed(2)}</div>
                    </div>
                </div>
            `;
            
            // Position the bubble (simplified positioning)
            const randomX = Math.random() * 80 + 10; // 10-90%
            const randomY = Math.random() * 80 + 10; // 10-90%
            
            bubble.style.cssText = `
                position: absolute;
                left: ${randomX}%;
                top: ${randomY}%;
                z-index: 1000;
                animation: bubbleAppear 0.5s ease-out;
            `;
            
            chartContainer.style.position = 'relative';
            chartContainer.appendChild(bubble);
            
            // Auto remove after 10 seconds
            setTimeout(() => {
                if (bubble.parentNode) {
                    bubble.style.animation = 'bubbleDisappear 0.3s ease-in';
                    setTimeout(() => {
                        if (bubble.parentNode) {
                            bubble.parentNode.removeChild(bubble);
                        }
                    }, 300);
                }
            }, 10000);
            
            console.log('✅ HTML bubble added');
        }
        
        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connection-status');
            const dotEl = document.querySelector('.connection-dot');
            
            if (connected) {
                statusEl.textContent = 'Live Connected';
                dotEl.style.background = '#22c55e';
            } else {
                statusEl.textContent = 'Disconnected';
                dotEl.style.background = '#ef4444';
            }
        }
        
        function updateTradeData(data) {
            if (data.symbol === currentSymbol) {
                document.getElementById('current-price').textContent = data.price.toFixed(2);
            }
            
            // Update symbol price in list
            const symbolItem = document.querySelector(`[data-symbol="${data.symbol}"] .symbol-price`);
            if (symbolItem) {
                symbolItem.textContent = `$${data.price.toFixed(2)}`;
            }
        }
        
        function addWhaleOrder(order) {
            const container = document.getElementById('whale-orders');
            
            // Remove placeholder if present
            if (container.innerHTML.includes('Waiting for whales')) {
                container.innerHTML = '';
            }
            
            const orderEl = document.createElement('div');
            orderEl.className = `whale-order ${order.side}`;
            orderEl.innerHTML = `
                <div>
                    <div class="whale-volume">${order.volume.toFixed(2)} ${order.symbol.replace('USDT', '')}</div>
                    <div class="whale-price">$${order.price.toLocaleString()}</div>
                </div>
                <div style="text-align: right; font-size: 10px;">
                    <div>${order.time}</div>
                    <div>$${(order.value/1000).toFixed(1)}K</div>
                </div>
            `;
            
            // Add to top
            container.insertBefore(orderEl, container.firstChild);
            
            // Keep only last 20 orders
            while (container.children.length > 20) {
                container.removeChild(container.lastChild);
            }
            
            console.log('🐋 Added whale order:', order);
        }
        
        function startSessionTimer() {
            setInterval(function() {
                const elapsed = Math.floor((Date.now() - sessionStart) / 1000);
                const hours = Math.floor(elapsed / 3600).toString().padStart(2, '0');
                const minutes = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0');
                const seconds = (elapsed % 60).toString().padStart(2, '0');
                
                document.getElementById('session-timer').textContent = `${hours}:${minutes}:${seconds}`;
            }, 1000);
        }
        
        console.log('✅ TradingView Professional Dashboard loaded');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(TRADINGVIEW_TEMPLATE)

@app.route('/api/ohlcv/<symbol>')
def get_ohlcv_data(symbol):
    """Get OHLCV data for TradingView"""
    if symbol not in dashboard.ohlcv_data:
        return jsonify({'error': 'Symbol not found'}), 404
    
    data = dashboard.ohlcv_data[symbol]
    
    # Convert to TradingView format
    bars = []
    for i in range(len(data['time'])):
        bars.append({
            'time': data['time'][i] * 1000,  # TradingView expects milliseconds
            'open': data['open'][i],
            'high': data['high'][i],
            'low': data['low'][i],
            'close': data['close'][i],
            'volume': data['volume'][i]
        })
    
    return jsonify(bars)

@app.route('/api/volume-profile/<symbol>')
def get_volume_profile(symbol):
    """Get volume profile data"""
    if symbol not in dashboard.symbols:
        return jsonify({'error': 'Symbol not found'}), 404
    
    return jsonify(dashboard.get_volume_profile_data(symbol))

@app.route('/api/whale-orders/<symbol>')
def get_whale_orders(symbol):
    """Get recent whale orders"""
    if symbol not in dashboard.whale_orders:
        return jsonify([])
    
    return jsonify(list(dashboard.whale_orders[symbol]))

@app.route('/api/order-flow/<symbol>')
def get_order_flow(symbol):
    """Get order flow data"""
    if symbol not in dashboard.order_flow:
        return jsonify({'error': 'Symbol not found'}), 404
    
    return jsonify(dashboard.order_flow[symbol])

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    return jsonify({
        'current_symbol': dashboard.current_symbol,
        'connection_active': dashboard.connection_active,
        'stats': dashboard.stats
    })

@socketio.on('connect')
def handle_connect():
    print("👤 Client connected to TradingView dashboard")

@socketio.on('disconnect')
def handle_disconnect():
    print("👤 Client disconnected from TradingView dashboard")

@socketio.on('switch_symbol')
def handle_switch_symbol(data):
    symbol = data.get('symbol')
    if symbol in dashboard.symbols:
        dashboard.current_symbol = symbol
        print(f"🔄 Switched to {symbol}")

if __name__ == '__main__':
    print("🚀 Starting TradingView Professional Dashboard...")
    print("🌐 URL: http://localhost:5008")
    print("📈 TradingView integration with custom analytics")
    print("🔬 Real-time Bybit data with whale detection")
    print("📊 Volume Profile + Order Flow analysis")
    
    # Start WebSocket connection
    dashboard.start_websocket()
    
    # Run Flask app
    socketio.run(app, debug=False, host='0.0.0.0', port=5008)