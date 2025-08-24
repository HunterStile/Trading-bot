# Sistema di Backtesting Avanzato - Guida Completa

## 📈 Panoramica

Il sistema di backtesting avanzato ti permette di testare la strategia Triple Confirmation su dati storici per valutare le performance prima di utilizzarla in trading reale.

## 🚀 Caratteristiche Principali

### ✅ Backtesting Completo
- Test su dati storici di qualsiasi simbolo supportato da Bybit
- Supporto per tutti i timeframe (5m, 15m, 30m, 1h, 4h, 1d)
- Analisi dettagliata delle performance con metriche avanzate

### 📊 Metriche Avanzate
- **Ritorno Totale**: Percentuale di guadagno/perdita totale
- **Sharpe Ratio**: Rapporto rischio/rendimento
- **Sortino Ratio**: Versione migliorata dello Sharpe che considera solo la volatilità negativa
- **Maximum Drawdown**: Massima perdita dal picco più alto
- **Win Rate**: Percentuale di trade vincenti
- **Profit Factor**: Rapporto tra profitti e perdite totali
- **Average Trade**: Durata media dei trade

### 🛡️ Risk Management Integrato
- **Stop Loss**: Protezione automatica dalle perdite eccessive
- **Take Profit**: Chiusura automatica al raggiungimento del target
- **Position Sizing**: Calcolo automatico della dimensione della posizione
- **Max Risk per Trade**: Limitazione del rischio per singolo trade

### 🔍 Ottimizzazione Parametri
- Test automatico di multiple combinazioni di parametri
- Grid search per trovare la configurazione ottimale
- Ranking dei risultati per performance

### ⚖️ Confronto Timeframe
- Test simultaneo su diversi timeframe
- Analisi comparativa delle performance
- Identificazione del timeframe più profittevole

## 🎯 Come Utilizzare il Sistema

### 1. Interfaccia Web (Raccomandato)

Accedi alla dashboard di backtesting tramite:
```
http://localhost:5000/backtest/
```

#### Tab "Test Singolo":
1. **Configura Mercato**:
   - Symbol: es. BTCUSDT, ETHUSDT
   - Timeframe: scegli tra 5m, 15m, 30m, 1h, 4h, 1d
   - Giorni indietro: periodo di test (7-365 giorni)

2. **Configura Strategia**:
   - Periodo EMA: periodo per la media mobile (5-200)
   - Candele richieste: numero di candele consecutive (1-10)
   - Distanza max: distanza massima dal prezzo EMA (0.1-5.0%)

3. **Configura Risk Management**:
   - Capitale iniziale: budget di partenza
   - Stop Loss: percentuale di perdita massima per trade
   - Take Profit: percentuale di guadagno target per trade

4. **Esegui Test**: Clicca "Esegui Backtest" e analizza i risultati

#### Tab "Ottimizzazione":
1. Configura i range di parametri da testare
2. Avvia l'ottimizzazione automatica
3. Analizza i risultati ordinati per performance
4. Usa la migliore configurazione trovata

#### Tab "Confronto Timeframe":
1. Inserisci symbol e capitale
2. Il sistema testerà automaticamente tutti i timeframe
3. Confronta i risultati per scegliere il timeframe ottimale

#### Tab "Risultati Salvati":
1. Visualizza tutti i backtest precedenti
2. Ricarica risultati specifici per analisi
3. Elimina risultati obsoleti

### 2. Script Python Diretto

```python
from advanced_backtest import AdvancedBacktestEngine

# Crea engine
engine = AdvancedBacktestEngine("BTCUSDT", initial_capital=1000)

# Configura risk management
engine.set_risk_management(
    stop_loss_pct=2.0,
    take_profit_pct=4.0,
    max_risk_per_trade=0.05
)

# Esegui backtest
results = engine.test_triple_confirmation_strategy(
    ema_period=10,
    required_candles=3,
    max_distance=1.0,
    timeframe='30',
    days_back=30,
    use_risk_management=True
)

print(f"Ritorno totale: {results['total_return_pct']:.2f}%")
```

### 3. Test Rapido del Sistema

Esegui il test completo del sistema:
```bash
python test_backtest_system.py
```

Questo script verificherà:
- ✅ Funzionamento base del backtesting
- ✅ Ottimizzazione parametri
- ✅ Confronto timeframe
- ✅ Salvataggio risultati

## 📋 Interpretazione dei Risultati

### 🎯 Metriche Chiave da Monitorare

1. **Ritorno Totale > 0%**: La strategia è profittevole
2. **Win Rate > 50%**: Più trade vincenti che perdenti
3. **Sharpe Ratio > 1**: Buon rapporto rischio/rendimento
4. **Max Drawdown < 20%**: Rischio controllato
5. **Profit Factor > 1.2**: Profitti superano significativamente le perdite

### 🚨 Segnali di Allarme

- **Win Rate < 30%**: Strategia poco efficace
- **Max Drawdown > 50%**: Rischio eccessivo
- **Sharpe Ratio < 0**: Performance peggiore del mercato
- **Pochi Trade (< 10)**: Dati insufficienti per valutazione

### 📈 Ottimizzazione Continua

1. **Testa Periodicamente**: Ricontrolla la strategia ogni mese
2. **Diversifica Timeframe**: Non affidarti a un solo timeframe
3. **Monitora Drawdown**: Ferma il bot se il drawdown supera i livelli testati
4. **Adatta i Parametri**: Usa l'ottimizzazione per migliorare i parametri

## ⚙️ Configurazioni Consigliate

### 📊 Per Principianti
```
- Timeframe: 30m o 1h
- Stop Loss: 2-3%
- Take Profit: 4-6%
- EMA Period: 10-15
- Test Period: 30-60 giorni
```

### 🚀 Per Trader Esperti
```
- Timeframe: 5m o 15m (più opportunità)
- Stop Loss: 1-2%
- Take Profit: 2-4%
- EMA Period: 5-10
- Test Period: 90-180 giorni
```

### 🛡️ Per Trading Conservativo
```
- Timeframe: 4h o 1d
- Stop Loss: 3-5%
- Take Profit: 6-10%
- EMA Period: 20-50
- Test Period: 180-365 giorni
```

## 📁 File e Directory

```
Trading-bot/
├── advanced_backtest.py          # Engine di backtesting principale
├── test_backtest_system.py       # Script di test del sistema
├── backtest_results/              # Risultati salvati (auto-creata)
├── frontend/
│   ├── routes/backtest.py         # API routes per interfaccia web
│   └── templates/backtest.html    # Interfaccia web
```

## 🔧 Risoluzione Problemi

### ❌ Errore "No data available"
- Verifica la connessione internet
- Controlla che il symbol sia corretto (es. BTCUSDT)
- Riduci il periodo di test se troppo lungo

### ❌ Errore "Advanced backtest engine not available"
- Verifica che il file `advanced_backtest.py` esista
- Controlla che tutte le dipendenze siano installate
- Riavvia l'applicazione

### ❌ Performance molto negative
- Verifica i parametri della strategia
- Testa su periodi diversi (mercati volatili possono dare risultati estremi)
- Considera di aggiustare stop loss e take profit

### ❌ Pochi trade generati
- Riduci la distanza massima dall'EMA
- Riduci il numero di candele richieste
- Testa su timeframe più bassi

## 📞 Supporto

Se incontri problemi:
1. Esegui `test_backtest_system.py` per diagnosticare il problema
2. Controlla i log nel terminale
3. Verifica che tutti i file siano presenti
4. Riavvia il sistema se necessario

---

**⚠️ Importante**: I risultati del backtesting sono basati su dati storici e non garantiscono performance future. Usa sempre un capitale che puoi permetterti di perdere e testa sempre la strategia in paper trading prima di usare capitale reale.
