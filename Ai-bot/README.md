# AI Scalping Bot for Bybit USDT Perpetual Futures

Un bot di scalping avanzato che utilizza intelligenza artificiale per il trading automatico su Bybit USDT Perpetual Futures.

## 🚀 Caratteristiche Principali

### Strategie di Trading
- **Mean Reversion**: Entra quando il prezzo devia significativamente dal VWAP con conferma dell'order book
- **Breakout**: Sfrutta le rotture di prezzo con spike di volume e momentum
- **Microstructural Analysis**: Analizza VWAP, volatilità, order book imbalance e volume profile

### Risk Management Avanzato
- **Position Sizing**: Calcolo automatico della size basato sul rischio (1% del capitale)
- **Stop Loss**: Stop loss dinamici e trailing stop
- **Kill Switch**: Interruzione automatica per perdite giornaliere > 2%
- **Portfolio Limits**: Controllo dell'esposizione totale e del drawdown

### Esecuzione Real-time
- **WebSocket**: Dati di mercato in tempo reale da Bybit
- **Low Latency**: Esecuzione ordini ottimizzata per lo scalping
- **Order Management**: Gestione intelligente degli ordini limit/market

### Monitoring e Logging
- **Trade Logging**: Salvataggio di tutti i trade in CSV
- **Performance Tracking**: Metriche di performance in tempo reale
- **Risk Monitoring**: Monitoraggio continuo del rischio

## 📁 Struttura del Progetto

```
Ai-bot/
├── __init__.py              # Inizializzazione modulo
├── main.py                  # Entry point principale
├── config.py                # Configurazioni del bot
├── data_feed.py             # WebSocket per dati di mercato
├── signals.py               # Generazione segnali di trading
├── strategy.py              # Implementazione strategie
├── risk.py                  # Gestione del rischio
├── execution.py             # Esecuzione ordini
├── engine.py                # Motore principale di trading
├── backtester.py            # Backtesting e analisi
└── README.md                # Questo file
```

## ⚙️ Installazione

### Requisiti
```bash
pip install numpy pandas asyncio websockets pybit beautifulsoup4 matplotlib seaborn
```

### Configurazione API
1. Crea un account su Bybit (testnet per i test)
2. Genera le API key con permessi di trading
3. Configura le chiavi nel file `.env` nella root del progetto:

```env
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
```

## 🎯 Utilizzo

### 1. Trading Live
```bash
# Testnet (raccomandato per iniziare)
python main.py trade --testnet

# Live trading (dopo aver testato)
python main.py trade --live --config my_config.json
```

### 2. Backtesting
```bash
# Backtest di default
python main.py backtest --symbol BTCUSDT --start-date 2024-01-01 --end-date 2024-02-01

# Backtest con configurazione personalizzata
python main.py backtest --config aggressive_config.json --symbol ETHUSDT
```

### 3. Generazione Configurazione
```bash
# Crea configurazione di default
python main.py config --output my_config.json

# Usa preset predefiniti
python main.py config --preset conservative --output conservative_config.json
```

## 📊 Configurazione

### Preset Disponibili
- **default**: Configurazione bilanciata
- **conservative**: Basso rischio, rendimenti stabili
- **aggressive**: Alto rischio, potenziali rendimenti maggiori

### Parametri Principali

#### Trading
```python
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Coppie da tradare
initial_capital = 10000.0                    # Capitale iniziale
use_testnet = True                           # Usa testnet
```

#### Mean Reversion Strategy
```python
mean_reversion_threshold = 2.0               # Deviazione standard dal VWAP
risk_per_trade = 0.01                        # 1% del capitale per trade
max_holding_time = 60                        # Massimo 60 secondi
```

#### Breakout Strategy
```python
breakout_threshold = 1.5                     # Soglia per breakout
volume_spike_threshold = 2.0                 # Spike di volume richiesto
trailing_stop_distance = 0.5                # Trailing stop %
```

#### Risk Management
```python
max_daily_loss = -0.02                       # -2% perdita giornaliera (kill switch)
max_positions = 5                            # Massimo 5 posizioni concorrenti
max_drawdown = -0.05                         # -5% drawdown massimo
```

## 📈 Strategia Mean Reversion

### Logica di Entrata
1. **Deviazione dal VWAP**: Prezzo > 2σ dal VWAP
2. **Order Book Imbalance**: Conferma dello squilibrio
3. **Volume**: Volume sufficiente per l'esecuzione

### Logica di Uscita
- **Take Profit**: Ritorno verso il VWAP (50%)
- **Stop Loss**: 1.2x la deviazione iniziale
- **Timeout**: Chiusura dopo 60 secondi

## ⚡ Strategia Breakout

### Logica di Entrata
1. **Rottura VWAP**: Prezzo rompe VWAP ± 1.5σ
2. **Volume Spike**: Volume > 2x la media
3. **Momentum**: Momentum allineato con la direzione

### Logica di Uscita
- **Trailing Stop**: Stop dinamico a 0.5%
- **Take Profit**: 2:1 risk/reward ratio
- **Timeout**: Chiusura dopo 15 secondi

## 🛡️ Risk Management

### Position Level
- **Position Sizing**: 1% del capitale per trade
- **Stop Loss**: Dinamico basato su ATR
- **Max Position**: 10% del capitale

### Portfolio Level
- **Daily Loss Limit**: -2% (kill switch)
- **Max Drawdown**: -5%
- **Max Positions**: 5 contemporanee
- **Correlation Limit**: Max 30% in posizioni correlate

## 📊 Backtesting

### Esempio di Backtest
```python
# Risultati esempio per BTCUSDT (Gen 2024)
Initial Capital: $10,000.00
Final Capital: $11,245.50
Total Return: $1,245.50 (12.46%)
Max Drawdown: -2.1%
Sharpe Ratio: 1.85
Win Rate: 65.4%
Total Trades: 156
```

### Metriche Analizzate
- **Return**: Rendimento totale e percentuale
- **Sharpe Ratio**: Rendimento aggiustato per il rischio
- **Max Drawdown**: Massima perdita dal picco
- **Win Rate**: Percentuale di trade vincenti
- **Profit Factor**: Rapporto profitti/perdite

## 📋 Logging e Monitoring

### Trade Log (CSV)
```csv
timestamp,symbol,side,size,entry_price,exit_price,pnl,strategy,signal_strength,exit_reason,duration_seconds
2024-01-15 10:30:15,BTCUSDT,long,0.001,45000.5,45125.2,124.7,MeanReversion,0.75,Take Profit,45.2
```

### Real-time Monitoring
- **Portfolio Value**: Valore in tempo reale
- **Open Positions**: Posizioni aperte
- **Risk Level**: Livello di rischio corrente
- **Daily PnL**: Profitti/perdite giornaliere

## ⚠️ Avvertenze Importanti

### Rischi del Trading
- **Perdite**: Il trading comporta rischi di perdite
- **Volatilità**: I mercati crypto sono altamente volatili
- **Slippage**: Possibili differenze tra prezzo atteso e eseguito

### Raccomandazioni
1. **Testa sempre in testnet** prima del live trading
2. **Inizia con capitale limitato**
3. **Monitora costantemente** le performance
4. **Usa lo stop loss** e rispetta i limiti di rischio
5. **Non investire** più di quanto puoi permetterti di perdere

### Test Raccomandati
```bash
# 1. Test configurazione
python main.py config --preset conservative

# 2. Backtest storico
python main.py backtest --symbol BTCUSDT --start-date 2024-01-01 --end-date 2024-01-31

# 3. Test su testnet
python main.py trade --testnet

# 4. Solo dopo successo: live trading
python main.py trade --live
```

## 🔧 Personalizzazione

### Creazione Strategia Custom
```python
# Aggiungere in strategy.py
class CustomStrategy(BaseStrategy):
    def should_enter(self, signal):
        # Logica di entrata personalizzata
        return custom_logic
    
    def should_exit(self, position, current_price):
        # Logica di uscita personalizzata
        return custom_exit_logic
```

### Indicatori Custom
```python
# Aggiungere in signals.py
def custom_indicator(self, data):
    # Calcolo indicatore personalizzato
    return indicator_value
```

## 📞 Supporto

Per domande, bug o suggerimenti:
1. Leggi la documentazione completa
2. Controlla i log per errori
3. Testa sempre in modalità sicura
4. Verifica la configurazione API

## 📄 Licenza

Questo software è fornito "as is" senza garanzie. L'autore non è responsabile per eventuali perdite derivanti dall'uso del bot.

---

**⚡ Happy Scalping! ⚡**

*Ricorda: Il trading automatico richiede costante supervisione e comprensione dei rischi coinvolti.*
