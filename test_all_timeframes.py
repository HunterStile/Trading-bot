import sys
import os

# Aggiungi il path per market_analysis
sys.path.append(os.path.join(os.path.dirname(__file__), 'frontend'))

from market_analysis import MarketAnalyzer

print("🔍 Test completo di tutti i timeframes:")

analyzer = MarketAnalyzer()
test_timeframes = [15, 60, 240, 1440]

for tf in test_timeframes:
    try:
        result = analyzer.analyze_symbol('BTCUSDT', tf)
        if result:
            tf_name = {15: '15m', 60: '1h', 240: '4h', 1440: '1d'}[tf]
            print(f"✅ {tf_name}: Prezzo ${result['current_price']}, Trend: {result['trend']['trend']}, RSI: {result['rsi']:.1f}")
        else:
            print(f"❌ {tf}: Nessun dato")
    except Exception as e:
        print(f"❌ {tf}: Errore - {e}")

print("\n🚀 Test con altri simboli sul giornaliero:")
test_symbols = ['ETHUSDT', 'SOLUSDT', 'DOGEUSDT']

for symbol in test_symbols:
    try:
        result = analyzer.analyze_symbol(symbol, 1440)
        if result:
            print(f"✅ {symbol}: ${result['current_price']}, Trend: {result['trend']['trend']}")
        else:
            print(f"❌ {symbol}: Nessun dato")
    except Exception as e:
        print(f"❌ {symbol}: Errore - {e}")
