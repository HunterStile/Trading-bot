"""
Script per testare rapidamente il sistema di backtesting avanzato
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Aggiungi il percorso del trading bot al sys.path
current_dir = Path(__file__).parent
trading_bot_dir = current_dir.parent
sys.path.append(str(trading_bot_dir))

from advanced_backtest import AdvancedBacktestEngine

def test_basic_backtest():
    """Test base del backtesting engine"""
    print("🔄 Test Base Backtest Engine...")
    
    # Crea engine
    engine = AdvancedBacktestEngine("BTCUSDT", initial_capital=1000)
    
    # Configura risk management
    engine.set_risk_management(
        stop_loss_pct=2.0,
        take_profit_pct=4.0,
        max_risk_per_trade=0.05
    )
    
    # Esegui test
    try:
        results = engine.test_triple_confirmation_strategy(
            ema_period=10,
            required_candles=3,
            max_distance=1.0,
            timeframe='30',
            days_back=7,  # Solo 7 giorni per test veloce
            use_risk_management=True
        )
        
        print("✅ Test completato con successo!")
        print(f"📈 Ritorno totale: {results['total_return_pct']:.2f}%")
        print(f"💰 Valore finale: ${results['final_value']:.2f}")
        print(f"📊 Totale trade: {results['total_trades']}")
        print(f"🎯 Win rate: {results['win_rate']:.1f}%")
        print(f"📉 Max drawdown: {results['max_drawdown']:.2f}%")
        print(f"📈 Sharpe ratio: {results['sharpe_ratio']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_optimization():
    """Test ottimizzazione parametri (versione veloce)"""
    print("\n🔍 Test Ottimizzazione Parametri...")
    
    engine = AdvancedBacktestEngine("BTCUSDT", initial_capital=1000)
    
    # Parametri ridotti per test veloce
    ema_periods = [5, 10, 15]
    candle_counts = [2, 3]
    distances = [0.5, 1.0]
    
    best_result = {'total_return_pct': -999999}
    total_tests = len(ema_periods) * len(candle_counts) * len(distances)
    current_test = 0
    
    print(f"Eseguendo {total_tests} test di ottimizzazione...")
    
    try:
        for ema in ema_periods:
            for candles in candle_counts:
                for distance in distances:
                    current_test += 1
                    print(f"Test {current_test}/{total_tests}: EMA={ema}, Candele={candles}, Distanza={distance}")
                    
                    engine.set_risk_management(stop_loss_pct=2.0, take_profit_pct=4.0, max_risk_per_trade=0.05)
                    
                    result = engine.test_triple_confirmation_strategy(
                        ema_period=ema,
                        required_candles=candles,
                        max_distance=distance,
                        timeframe='30',
                        days_back=7,  # Solo 7 giorni per test veloce
                        use_risk_management=True
                    )
                    
                    if result['total_return_pct'] > best_result['total_return_pct']:
                        best_result = result
                        best_result['ema_period'] = ema
                        best_result['required_candles'] = candles
                        best_result['max_distance'] = distance
        
        print("✅ Ottimizzazione completata!")
        print(f"🏆 Miglior configurazione:")
        print(f"  - EMA Period: {best_result['ema_period']}")
        print(f"  - Candele richieste: {best_result['required_candles']}")
        print(f"  - Max distance: {best_result['max_distance']}%")
        print(f"  - Ritorno: {best_result['total_return_pct']:.2f}%")
        print(f"  - Win rate: {best_result['win_rate']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'ottimizzazione: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_timeframe_comparison():
    """Test confronto timeframe"""
    print("\n⚖️ Test Confronto Timeframe...")
    
    timeframes = [
        {'code': '5', 'name': '5 minutes', 'days': 3},
        {'code': '15', 'name': '15 minutes', 'days': 5},
        {'code': '30', 'name': '30 minutes', 'days': 7}
    ]
    
    results = []
    
    try:
        for tf in timeframes:
            print(f"Testando timeframe {tf['name']}...")
            
            engine = AdvancedBacktestEngine("BTCUSDT", initial_capital=1000)
            engine.set_risk_management(stop_loss_pct=2.0, take_profit_pct=4.0, max_risk_per_trade=0.05)
            
            result = engine.test_triple_confirmation_strategy(
                ema_period=10,
                required_candles=3,
                max_distance=1.0,
                timeframe=tf['code'],
                days_back=tf['days'],
                use_risk_management=True
            )
            
            result['timeframe_name'] = tf['name']
            results.append(result)
        
        # Ordina per performance
        results.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        print("✅ Confronto completato!")
        print("🏆 Ranking timeframe per performance:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['timeframe_name']}: {result['total_return_pct']:.2f}% (Win rate: {result['win_rate']:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel confronto: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_test_results():
    """Salva risultati test completi"""
    print("\n💾 Salvataggio risultati test completo...")
    
    try:
        engine = AdvancedBacktestEngine("BTCUSDT", initial_capital=1000)
        engine.set_risk_management(stop_loss_pct=2.0, take_profit_pct=4.0, max_risk_per_trade=0.05)
        
        results = engine.test_triple_confirmation_strategy(
            ema_period=10,
            required_candles=3,
            max_distance=1.0,
            timeframe='30',
            days_back=30,  # Test più completo
            use_risk_management=True,
            save_results=True  # Salva automaticamente
        )
        
        print("✅ Risultati salvati con successo!")
        print(f"📁 File salvato nella cartella backtest_results/")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel salvataggio: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Esegue tutti i test del sistema di backtesting"""
    print("🚀 Test Sistema Backtesting Avanzato")
    print("=" * 50)
    
    # Verifica dipendenze
    try:
        from advanced_backtest import AdvancedBacktestEngine
        print("✅ Advanced Backtest Engine importato correttamente")
    except ImportError as e:
        print(f"❌ Errore importazione: {e}")
        return
    
    # Esegui tutti i test
    tests = [
        ("Test Base", test_basic_backtest),
        ("Ottimizzazione Parametri", test_parameter_optimization),
        ("Confronto Timeframe", test_timeframe_comparison),
        ("Salvataggio Risultati", save_test_results)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    # Riepilogo
    print(f"\n{'='*50}")
    print("📋 RIEPILOGO TEST:")
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n🎯 Test completati: {total_passed}/{total_tests}")
    
    if total_passed == total_tests:
        print("🎉 Tutti i test sono passati! Il sistema di backtesting è pronto.")
    else:
        print("⚠️ Alcuni test sono falliti. Controlla i log per i dettagli.")

if __name__ == "__main__":
    main()
