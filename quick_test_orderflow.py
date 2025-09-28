"""
QUICK TEST - Test rapido con parametri modificabili
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_standalone_orderflow import run_complete_test, generate_realistic_market_data
from core.chart_system import OrderFlowAnalyzer, ChartRenderer

def quick_test_different_scenarios():
    """Test scenari diversi"""
    
    print("🧪 QUICK TESTS - Scenari Diversi")
    print("=" * 40)
    
    scenarios = [
        {
            'name': 'Bear Market (Vendite Aggressive)',
            'hours': 1,
            'whale_threshold': 2.0,
            'symbol': 'BTCUSDT'
        },
        {
            'name': 'Bull Market (Acquisti Whales)',
            'hours': 1, 
            'whale_threshold': 5.0,
            'symbol': 'ETHUSDT'
        },
        {
            'name': 'Sideways (Accumulation)',
            'hours': 0.5,
            'whale_threshold': 1.0,
            'symbol': 'BTCUSDT'
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\n🎭 Scenario {i+1}: {scenario['name']}")
        print("-" * 30)
        
        # Modifica analyzer per scenario
        analyzer = OrderFlowAnalyzer(large_order_threshold_btc=scenario['whale_threshold'])
        
        print(f"⚙️ Whale threshold: {scenario['whale_threshold']} BTC")
        print(f"⏱️ Timespan: {scenario['hours']} ore")
        
        # Per ora solo print config, potresti espandere per generare grafici
        print("✅ Scenario configurato")

def print_usage_guide():
    """Guida utilizzo"""
    print("""
🚀 GUIDA UTILIZZO SISTEMA ORDERFLOW
===================================

📊 PER TESTARE:
1. python test_standalone_orderflow.py    # Test completo
2. start STANDALONE_TEST_BTCUSDT_orderflow.html  # Apri grafico

🔧 PER PERSONALIZZARE:
- Modifica whale_threshold nel codice (default: 3.0 BTC)
- Cambia timespan (default: 3 ore)
- Modifica tick_size per granularità volume profile

🎯 NEI GRAFICI VEDRAI:
- 🕯️ Candlesticks con prezzi
- 🔵 Bolle verdi = Large BUY orders
- 🔴 Bolle rosse = Large SELL orders  
- 🟠 Linea POC = Point of Control
- 🔵 Linee VAH/VAL = Value Area
- 📊 Volume Profile laterale con colori delta
- 📈 Volume bars in basso

💡 INTERPRETAZIONE:
- Molte bolle verdi = Accumulation whales
- Molte bolle rosse = Distribution whales
- POC = Livello più traddato (supporto/resistenza)
- VAH/VAL = Range di valore principale (70% volume)

🔗 INTEGRAZIONE CON BOT:
- Usa come segnali per entry/exit
- Monitora whales per confermare trend
- POC/VAH/VAL come target/stop levels
""")

if __name__ == "__main__":
    print_usage_guide()
    quick_test_different_scenarios()