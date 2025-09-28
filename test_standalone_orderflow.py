"""
TEST STANDALONE - Sistema Orderflow
Test completo con dati simulati realistici
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.chart_system import (
    VolumeProfileCalculator,
    OrderFlowAnalyzer, 
    ChartRenderer
)

def generate_realistic_market_data(symbol='BTCUSDT', hours=2):
    """Genera dati di mercato realistici per test"""
    print(f"📊 Generando dati realistici per {symbol}...")
    
    # Timeframe 
    start_time = datetime.now() - timedelta(hours=hours)
    timestamps = pd.date_range(start=start_time, end=datetime.now(), freq='1min')
    
    # Parametri mercato
    base_price = 67000  # BTC price realistic
    volatility = 0.001  # 0.1% per minuto
    
    # Generate price data con random walk + trend
    price_changes = np.random.normal(0, volatility, len(timestamps))
    price_changes[50:70] += 0.002  # Simula pump
    price_changes[100:120] -= 0.003  # Simula dump
    
    prices = [base_price]
    for change in price_changes[:-1]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Generate realistic trades
    trades_data = []
    large_order_probability = 0.05  # 5% chance di ordine grosso
    
    for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
        # Numero trades per minuto (variabile)
        num_trades = np.random.poisson(8)  # Media 8 trades/minuto
        
        for _ in range(num_trades):
            # Volume normale vs ordini grossi
            if np.random.random() < large_order_probability:
                volume = np.random.uniform(3.0, 15.0)  # Large order
            else:
                volume = np.random.exponential(0.5)  # Normal retail
            
            # Side bias (più vendite durante dump)
            if 100 <= i <= 120:  # Durante dump
                side = np.random.choice(['buy', 'sell'], p=[0.3, 0.7])
            elif 50 <= i <= 70:  # Durante pump  
                side = np.random.choice(['buy', 'sell'], p=[0.7, 0.3])
            else:
                side = np.random.choice(['buy', 'sell'], p=[0.5, 0.5])
            
            # Aggiungi noise al prezzo per ogni trade
            trade_price = price + np.random.normal(0, price * 0.0001)
            
            trades_data.append({
                'timestamp': timestamp + timedelta(seconds=np.random.randint(0, 60)),
                'price': trade_price,
                'volume': volume,
                'side': side,
                'symbol': symbol
            })
    
    print(f"✅ Generati {len(trades_data)} trades in {hours}h")
    return pd.DataFrame(trades_data)

def generate_candle_data(trades_df, timeframe='5T'):
    """Converte trades in candlestick data"""
    if trades_df.empty:
        return pd.DataFrame()
    
    # Set timestamp as index
    df = trades_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Resample per timeframe
    ohlc = df['price'].resample(timeframe).ohlc()
    volume = df['volume'].resample(timeframe).sum()
    
    # Combina
    candles = pd.DataFrame({
        'timestamp': ohlc.index,
        'open': ohlc['open'].fillna(method='ffill'),
        'high': ohlc['high'].fillna(method='ffill'),
        'low': ohlc['low'].fillna(method='ffill'), 
        'close': ohlc['close'].fillna(method='ffill'),
        'volume': volume.fillna(0)
    }).dropna()
    
    return candles.reset_index(drop=True)

def run_complete_test():
    """Test completo del sistema"""
    print("🚀 AVVIO TEST COMPLETO SISTEMA ORDERFLOW")
    print("=" * 50)
    
    # 1. Genera dati realistici
    symbol = 'BTCUSDT'
    trades_df = generate_realistic_market_data(symbol, hours=3)
    candles_df = generate_candle_data(trades_df)
    
    print(f"📊 Dati generati:")
    print(f"   - Trades: {len(trades_df)}")
    print(f"   - Candles: {len(candles_df)} (5min)")
    print(f"   - Timespan: {trades_df['timestamp'].min()} to {trades_df['timestamp'].max()}")
    
    # 2. Setup componenti
    print("\n🔧 Inizializzando componenti...")
    volume_calculator = VolumeProfileCalculator(tick_size=5.0)  # $5 tick size
    analyzer = OrderFlowAnalyzer(large_order_threshold_btc=3.0)  # 3 BTC threshold
    renderer = ChartRenderer()
    
    # 3. Calcola Volume Profile
    print("📈 Calcolando Volume Profile...")
    volume_profile = volume_calculator.calculate_profile(trades_df)
    
    print(f"   POC: ${volume_profile.poc_price:.2f} (Vol: {volume_profile.poc_volume:.2f})")
    print(f"   VAH: ${volume_profile.vah_price:.2f}")
    print(f"   VAL: ${volume_profile.val_price:.2f}")
    print(f"   Total Volume: {volume_profile.total_volume:.2f} BTC")
    
    # 4. Analizza Order Flow
    print("🔍 Analizzando Order Flow...")
    
    # Simula analisi trades per large orders
    large_orders = []
    for _, trade in trades_df.iterrows():
        orders = analyzer.analyze_trade(type('Trade', (), {
            'symbol': trade['symbol'],
            'price': trade['price'],
            'volume': trade['volume'], 
            'side': trade['side'],
            'timestamp': trade['timestamp'],
            'trade_id': f"sim_{len(large_orders)}"
        })())
        large_orders.extend(orders)
    
    print(f"   🐋 Large Orders: {len(large_orders)}")
    if large_orders:
        total_whale_volume = sum(o.volume for o in large_orders)
        whale_buy = sum(o.volume for o in large_orders if o.side == 'buy')
        whale_sell = sum(o.volume for o in large_orders if o.side == 'sell')
        print(f"   📊 Total Whale Volume: {total_whale_volume:.2f} BTC")
        print(f"   📈 Buy Pressure: {whale_buy:.2f} BTC ({whale_buy/total_whale_volume*100:.1f}%)")
        print(f"   📉 Sell Pressure: {whale_sell:.2f} BTC ({whale_sell/total_whale_volume*100:.1f}%)")
    
    # 5. Genera Segnali
    print("🎯 Generando segnali...")
    signals = analyzer.analyze_volume_profile_signals(symbol, trades_df)
    
    print(f"   🚨 Signals: {len(signals)}")
    for signal in signals:
        print(f"      {signal.signal_type}: {signal.strength:.1f}% @ ${signal.price_level:.2f}")
        print(f"         {signal.description}")
    
    # 6. Crea Grafici
    print("\n🎨 Generando grafici...")
    
    # Grafico principale
    main_fig = renderer.create_orderflow_chart(
        symbol, candles_df, volume_profile, large_orders, signals
    )
    main_filename = f"STANDALONE_TEST_{symbol}_orderflow.html"
    main_fig.write_html(main_filename)
    print(f"   ✅ Grafico principale: {main_filename}")
    
    # Heatmap
    heatmap_fig = renderer.create_heatmap_chart(volume_profile, symbol)
    heatmap_filename = f"STANDALONE_TEST_{symbol}_heatmap.html"
    heatmap_fig.write_html(heatmap_filename)
    print(f"   ✅ Heatmap: {heatmap_filename}")
    
    # 7. Statistics Summary
    stats = analyzer.get_summary_stats(symbol)
    
    print("\n📊 SUMMARY STATISTICS")
    print("=" * 30)
    print(f"Symbol: {stats['symbol']}")
    print(f"Large Orders Count: {stats.get('large_orders_count', 0)}")
    print(f"Total Large Order Volume: {stats.get('total_volume', 0):.2f} BTC")
    print(f"Total Large Order Value: ${stats.get('total_value', 0):,.2f}")
    print(f"Average Impact Score: {stats.get('avg_impact_score', 0):.1f}/100")
    print(f"Buy/Sell Ratio: {stats.get('buy_sell_ratio', 0):.2f}")
    
    # 8. Price Levels Analysis
    support_resistance = volume_calculator.get_support_resistance_levels(
        volume_profile, min_volume_threshold=0.03
    )
    print(f"\n🎯 KEY LEVELS ({len(support_resistance)} levels)")
    print("=" * 20)
    for level in support_resistance[:5]:  # Top 5
        print(f"${level:.2f}")
    
    print(f"\n✅ TEST COMPLETATO!")
    print(f"📁 File generati:")
    print(f"   - {main_filename}")
    print(f"   - {heatmap_filename}")
    print(f"\n💡 Apri i file .html nel browser per vedere i grafici!")

if __name__ == "__main__":
    run_complete_test()