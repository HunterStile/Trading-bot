"""
LIVE REAL-TIME ORDERFLOW SYSTEM
Connessione WebSocket reale a Bybit per analisi orderflow live
"""
import asyncio
import websockets
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os
from threading import Thread
import time

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.chart_system import (
    VolumeProfileCalculator,
    OrderFlowAnalyzer,
    ChartRenderer
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveOrderflowTracker:
    """Tracker orderflow real-time da Bybit"""
    
    def __init__(self, symbols=['BTCUSDT'], large_order_threshold=3.0):
        self.symbols = symbols
        self.large_order_threshold = large_order_threshold
        
        # WebSocket URL Bybit
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        
        # Components
        self.volume_calculator = VolumeProfileCalculator(tick_size=1.0)
        self.analyzer = OrderFlowAnalyzer(large_order_threshold_btc=large_order_threshold)
        self.renderer = ChartRenderer()
        
        # Data storage
        self.trades_buffer = {symbol: [] for symbol in symbols}
        self.large_orders_live = []
        self.connection_active = False
        
        # Statistics
        self.stats = {
            'trades_received': 0,
            'large_orders_detected': 0,
            'connection_start': None,
            'last_update': None
        }
    
    async def connect_and_stream(self):
        """Connette e inizia streaming real-time"""
        try:
            logger.info("🔌 Connessione a Bybit WebSocket...")
            
            async with websockets.connect(self.ws_url) as websocket:
                self.connection_active = True
                self.stats['connection_start'] = datetime.now()
                
                # Subscribe ai simboli
                await self._subscribe_to_trades(websocket)
                
                logger.info("✅ Connesso! Streaming dati real-time...")
                
                # Loop principale ricezione messaggi
                async for message in websocket:
                    await self._handle_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 Connessione WebSocket chiusa")
            self.connection_active = False
        except Exception as e:
            logger.error(f"❌ Errore WebSocket: {e}")
            self.connection_active = False
    
    async def _subscribe_to_trades(self, websocket):
        """Subscribe ai trade feeds"""
        for symbol in self.symbols:
            subscription = {
                "op": "subscribe",
                "args": [f"publicTrade.{symbol}"]
            }
            await websocket.send(json.dumps(subscription))
            logger.info(f"📡 Subscribed to {symbol} trades")
    
    async def _handle_message(self, message):
        """Gestisce messaggi WebSocket"""
        try:
            data = json.loads(message)
            
            # Skip subscription confirmations
            if "success" in data:
                return
            
            # Handle trade data
            if "topic" in data and "publicTrade" in data["topic"]:
                await self._process_trade_data(data)
                
        except json.JSONDecodeError:
            logger.warning("⚠️ Invalid JSON received")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    async def _process_trade_data(self, data):
        """Processa dati trade real-time"""
        try:
            topic = data["topic"]
            symbol = topic.split(".")[1]
            trades_data = data["data"]
            
            for trade_data in trades_data:
                # Parse trade
                trade_info = {
                    'symbol': symbol,
                    'price': float(trade_data["p"]),
                    'volume': float(trade_data["v"]),
                    'side': 'buy' if trade_data["S"] == "Buy" else 'sell',
                    'timestamp': datetime.fromtimestamp(int(trade_data["T"]) / 1000),
                    'trade_id': trade_data["i"]
                }
                
                # Aggiungi a buffer
                self.trades_buffer[symbol].append(trade_info)
                
                # Mantieni solo ultimi 1000 trades per performance
                if len(self.trades_buffer[symbol]) > 1000:
                    self.trades_buffer[symbol] = self.trades_buffer[symbol][-1000:]
                
                # Check large order
                if trade_info['volume'] >= self.large_order_threshold:
                    await self._handle_large_order(trade_info)
                
                # Update stats
                self.stats['trades_received'] += 1
                self.stats['last_update'] = datetime.now()
                
                # Print ogni 10 trades per evitare spam
                if self.stats['trades_received'] % 10 == 0:
                    await self._print_status()
                    
        except Exception as e:
            logger.error(f"❌ Error processing trade: {e}")
    
    async def _handle_large_order(self, trade_info):
        """Gestisce large orders rilevati"""
        # Calcola impact score
        impact_score = min(100, (trade_info['volume'] / self.large_order_threshold) * 20)
        
        large_order = {
            'symbol': trade_info['symbol'],
            'side': trade_info['side'],
            'price': trade_info['price'],
            'volume': trade_info['volume'],
            'value': trade_info['price'] * trade_info['volume'],
            'timestamp': trade_info['timestamp'],
            'impact_score': impact_score
        }
        
        self.large_orders_live.append(large_order)
        self.stats['large_orders_detected'] += 1
        
        # Print large order immediately
        side_emoji = "🟢" if trade_info['side'] == 'buy' else "🔴"
        print(f"\n{side_emoji} 🐋 LARGE ORDER DETECTED!")
        print(f"   {trade_info['symbol']}: {trade_info['side'].upper()} {trade_info['volume']:.4f}")
        print(f"   Price: ${trade_info['price']:,.2f}")
        print(f"   Value: ${large_order['value']:,.2f}")
        print(f"   Impact: {impact_score:.1f}/100")
        print(f"   Time: {trade_info['timestamp'].strftime('%H:%M:%S')}")
    
    async def _print_status(self):
        """Stampa status periodico"""
        uptime = datetime.now() - self.stats['connection_start'] if self.stats['connection_start'] else timedelta(0)
        
        print(f"\r📊 Live: {self.stats['trades_received']} trades | "
              f"🐋 {self.stats['large_orders_detected']} whales | "
              f"⏱️ {str(uptime).split('.')[0]}", end="", flush=True)
    
    def generate_live_chart(self, symbol='BTCUSDT', lookback_minutes=60):
        """Genera grafico con dati live attuali"""
        try:
            if symbol not in self.trades_buffer or not self.trades_buffer[symbol]:
                logger.warning(f"No data available for {symbol}")
                return None
            
            # Convert to DataFrame
            trades_df = pd.DataFrame(self.trades_buffer[symbol])
            
            # Filter last N minutes
            cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
            recent_trades = trades_df[trades_df['timestamp'] >= cutoff_time]
            
            if recent_trades.empty:
                logger.warning(f"No recent trades for {symbol}")
                return None
            
            print(f"\n📊 Generating live chart for {symbol}...")
            print(f"   Trades: {len(recent_trades)}")
            print(f"   Timespan: {lookback_minutes} minutes")
            
            # Calculate volume profile
            volume_profile = self.volume_calculator.calculate_profile(recent_trades)
            
            # Generate candle data (simplified)
            candles_df = self._create_candle_data(recent_trades)
            
            # Get recent large orders
            recent_large_orders = [
                order for order in self.large_orders_live
                if order['timestamp'] >= cutoff_time and order['symbol'] == symbol
            ]
            
            # Convert to analyzer format
            analyzer_large_orders = []
            for order in recent_large_orders:
                analyzer_large_orders.append(type('LargeOrder', (), order)())
            
            # Generate signals
            signals = self.analyzer.analyze_volume_profile_signals(symbol, recent_trades)
            
            # Create chart
            fig = self.renderer.create_orderflow_chart(
                symbol, candles_df, volume_profile, analyzer_large_orders, signals
            )
            
            # Save with timestamp
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"LIVE_{symbol}_{timestamp}.html"
            fig.write_html(filename)
            
            print(f"✅ Live chart saved: {filename}")
            
            # Print stats
            print(f"\n📈 LIVE ANALYSIS RESULTS:")
            print(f"   POC: ${volume_profile.poc_price:.2f}")
            print(f"   VAH: ${volume_profile.vah_price:.2f}")
            print(f"   VAL: ${volume_profile.val_price:.2f}")
            print(f"   Large Orders: {len(recent_large_orders)}")
            print(f"   Signals: {len(signals)}")
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error generating chart: {e}")
            return None
    
    def _create_candle_data(self, trades_df, timeframe_minutes=5):
        """Crea candlestick data da trades"""
        if trades_df.empty:
            return pd.DataFrame()
        
        df = trades_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample per timeframe
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

def start_live_tracking(symbols=['BTCUSDT'], threshold=3.0):
    """Avvia tracking live"""
    print("🚀 STARTING LIVE ORDERFLOW TRACKING")
    print("=" * 50)
    print(f"📡 Symbols: {', '.join(symbols)}")
    print(f"🐋 Large order threshold: {threshold} BTC")
    print(f"⏰ Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🔴 LIVE MODE - Press Ctrl+C to stop and generate chart")
    print("-" * 50)
    
    tracker = LiveOrderflowTracker(symbols, threshold)
    
    try:
        # Start WebSocket in async loop
        asyncio.run(tracker.connect_and_stream())
    except KeyboardInterrupt:
        print(f"\n\n🛑 STOPPING LIVE TRACKING...")
        print("📊 Generating final chart with collected data...")
        
        # Generate chart with collected data
        filename = tracker.generate_live_chart(symbols[0])
        if filename:
            print(f"\n✅ LIVE SESSION COMPLETE!")
            print(f"📁 Chart saved: {filename}")
            print(f"🌐 Open with: start {filename}")
        
        # Final stats
        print(f"\n📊 SESSION STATISTICS:")
        print(f"   Total trades: {tracker.stats['trades_received']}")
        print(f"   Large orders: {tracker.stats['large_orders_detected']}")
        if tracker.stats['connection_start']:
            duration = datetime.now() - tracker.stats['connection_start']
            print(f"   Duration: {str(duration).split('.')[0]}")

if __name__ == "__main__":
    # Start live tracking
    start_live_tracking(['BTCUSDT'], threshold=2.0)  # Lower threshold for more action