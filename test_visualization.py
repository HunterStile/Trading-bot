#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script per la visualizzazione grafica del backtest
"""

# Installa le librerie necessarie se non disponibili
try:
    import matplotlib.pyplot as plt
    print("✅ Matplotlib disponibile")
except ImportError:
    print("⚠️  Installando matplotlib...")
    import subprocess
    subprocess.check_call(["pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt

try:
    import plotly.graph_objects as go
    print("✅ Plotly disponibile")
except ImportError:
    print("⚠️  Installando plotly...")
    import subprocess
    subprocess.check_call(["pip", "install", "plotly"])
    import plotly.graph_objects as go

from backtest_advanced import *

def test_visualization():
    """
    Test rapido della visualizzazione
    """
    print("🎯 TEST VISUALIZZAZIONE BACKTEST")
    print("="*50)
    
    # Parametri fissi per test rapido
    simbolo = "BTCUSDT"
    timeframe = "D" 
    giorni = 90  # 3 mesi per test veloce
    capitale = 10000
    
    print(f"📊 Test con: {simbolo} - {timeframe} - {giorni} giorni")
    
    # Crea strategia Triple Confirmation
    strategy = TripleConfirmationStrategy(timeframe)
    print("✅ Strategia creata")
    
    # Esegui backtest
    engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
    print("🔄 Avvio backtest...")
    results = engine.run_backtest(timeframe, giorni, 100)
    
    if results['success']:
        print("✅ Backtest completato!")
        print(f"📈 Rendimento: {results['total_return_percent']:.2f}%")
        print(f"🎯 Win Rate: {results['win_rate']:.1f}%")
        print(f"📊 Trades: {results['total_trades']}")
        
        # Crea grafici
        print("\n📊 Creazione grafici...")
        
        # Grafico completo con indicatori
        print("1. Grafico completo con indicatori...")
        engine.plot_backtest_results(results['indicators'], results, show_indicators=True)
        
        # Grafico semplificato
        print("2. Grafico semplificato...")
        engine.plot_backtest_results(results['indicators'], results, show_indicators=False)
        
        print("✅ Grafici creati con successo!")
        print("📁 I file sono stati salvati nella directory corrente")
        
    else:
        print(f"❌ Backtest fallito: {results.get('error', 'Errore sconosciuto')}")

if __name__ == "__main__":
    test_visualization()
