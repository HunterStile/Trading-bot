"""
ESEMPIO COMPLETO - Sistema Chart Orderflow Real-Time
Integra tutti i componenti per analisi live del mercato
"""

import asyncio
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.chart_system import (
    VolumeProfileCalculator, 
    RealTimeFeed, 
    OrderFlowAnalyzer,
    ChartRenderer
)

class LiveOrderflowSystem:
    """Sistema completo per analisi orderflow real-time"""
    
    def __init__(self, symbols=['BTCUSDT']):
        self.symbols = symbols
        
        # Inizializza componenti
        self.feed = RealTimeFeed(symbols)
        self.analyzer = OrderFlowAnalyzer(
            large_order_threshold_btc=5.0,
            large_order_threshold_eth=50.0
        )
        self.renderer = ChartRenderer()
        
        # Storage per grafici
        self.candles_data = {symbol: [] for symbol in symbols}
        self.last_update = datetime.now()
        
        # Callback setup
        self.feed.add_trade_callback(self._on_trade)
        self.feed.add_orderbook_callback(self._on_orderbook)
    
    def _on_trade(self, trade):
        """Callback per trades real-time"""
        # Analizza ordini grossi
        large_orders = self.analyzer.analyze_trade(trade)
        
        if large_orders:
            for order in large_orders:
                print(f"🐋 {order.symbol}: {order.side} {order.volume:.2f} @ ${order.price:.2f}")
    
    def _on_orderbook(self, orderbook):
        """Callback per orderbook updates"""
        large_orders, microstructure = self.analyzer.analyze_orderbook(orderbook)
        
        if microstructure.absorption_detected:
            print(f"🌊 Absorption pattern detected on {orderbook.symbol}")
    
    async def start_live_analysis(self):
        """Avvia analisi live"""
        print("🚀 Starting Live Orderflow Analysis...")
        
        # Avvia feed in background
        self.feed.start_background_feed()
        
        # Loop per aggiornamenti grafici
        while True:
            await asyncio.sleep(30)  # Update ogni 30 secondi
            await self._update_charts()
    
    async def _update_charts(self):
        """Aggiorna grafici con dati correnti"""
        for symbol in self.symbols:
            try:
                # Get recent trades per volume profile
                trades_df = self.feed.get_recent_trades_df(symbol, minutes=60)
                
                if not trades_df.empty:
                    # Calcola volume profile
                    volume_calculator = VolumeProfileCalculator()
                    volume_profile = volume_calculator.calculate_profile(trades_df)
                    
                    # Genera segnali
                    signals = self.analyzer.analyze_volume_profile_signals(symbol, trades_df)
                    
                    # Get large orders
                    large_orders = self.analyzer.get_recent_large_orders(symbol, minutes=60)
                    
                    # Genera candlestick data (semplificato per demo)
                    candles_df = self._generate_candle_data(trades_df)
                    
                    # Crea grafico
                    fig = self.renderer.create_orderflow_chart(
                        symbol, candles_df, volume_profile, 
                        large_orders, signals
                    )
                    
                    # Salva grafico aggiornato
                    fig.write_html(f"live_{symbol}_orderflow.html")
                    print(f"📊 Updated {symbol} chart")
            
            except Exception as e:
                print(f"❌ Error updating {symbol}: {e}")
    
    def _generate_candle_data(self, trades_df):
        """Genera candlestick data da trades (semplificato)"""
        if trades_df.empty:
            return pd.DataFrame()
        
        # Resample per 5 minuti
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df.set_index('timestamp', inplace=True)
        
        # OHLCV resampling
        ohlc = trades_df['price'].resample('5T').ohlc()
        volume = trades_df['volume'].resample('5T').sum()
        
        candles = pd.DataFrame({
            'timestamp': ohlc.index,
            'open': ohlc['open'].fillna(method='ffill'),
            'high': ohlc['high'].fillna(method='ffill'), 
            'low': ohlc['low'].fillna(method='ffill'),
            'close': ohlc['close'].fillna(method='ffill'),
            'volume': volume.fillna(0)
        }).dropna()
        
        return candles.reset_index(drop=True)

# Esempio di utilizzo
async def main():
    """Main function per test completo"""
    system = LiveOrderflowSystem(['BTCUSDT'])
    
    print("🎯 Sistema Orderflow Real-Time inizializzato")
    print("📊 Componenti attivi:")
    print("   - Volume Profile Calculator")
    print("   - Real-Time Feed (WebSocket)")
    print("   - Order Flow Analyzer") 
    print("   - Chart Renderer")
    print("\n🔄 Per analisi live reale, decommentare:")
    print("   await system.start_live_analysis()")
    
    # Per test, genera un grafico demo
    print("\n🎨 Generando grafico demo...")
    
    # Demo data
    import numpy as np
    dates = pd.date_range(start=datetime.now() - timedelta(hours=2), 
                         end=datetime.now(), freq='5min')
    
    demo_candles = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(len(dates)).cumsum() * 10,
        'high': 50000 + np.random.randn(len(dates)).cumsum() * 10 + 20,
        'low': 50000 + np.random.randn(len(dates)).cumsum() * 10 - 20,
        'close': 50000 + np.random.randn(len(dates)).cumsum() * 10,
        'volume': np.random.exponential(100, len(dates))
    })
    
    print("✅ Sistema completo pronto per utilizzo!")

if __name__ == "__main__":
    asyncio.run(main())