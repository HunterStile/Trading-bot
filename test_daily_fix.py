import sys
import os

# Aggiungi il path per market_analysis
sys.path.append(os.path.join(os.path.dirname(__file__), 'frontend'))

from market_analysis import MarketAnalyzer, convert_timeframe_to_bybit

# Test della funzione di conversione
print("🔧 Test conversione timeframes:")
test_timeframes = [15, 60, 240, 1440, 10080]
for tf in test_timeframes:
    converted = convert_timeframe_to_bybit(tf)
    print(f"   {tf} minuti → '{converted}'")

# Test dell'analisi con timeframe giornaliero
print("\n🔍 Test analisi simbolo con timeframe giornaliero:")
analyzer = MarketAnalyzer()

try:
    result = analyzer.analyze_symbol('BTCUSDT', 1440)
    if result:
        print(f"✅ Analisi riuscita per BTCUSDT giornaliero!")
        print(f"   Prezzo: ${result['current_price']}")
        print(f"   Trend: {result['trend']}")
        print(f"   RSI: {result['rsi']:.2f}")
        print(f"   Segnali: {result['reversal_signals']}")
    else:
        print("❌ Analisi fallita - nessun dato restituito")
except Exception as e:
    print(f"❌ Errore nell'analisi: {e}")
