# Sistema di Analisi Automatica del Mercato Crypto

## Panoramica

Il nuovo sistema di **Analisi Automatica** è un modulo avanzato che monitora continuamente le crypto e invia segnali di mercato in modo autonomo. A differenza del sistema di Alert che richiede la configurazione manuale di soglie specifiche, questo sistema analizza il mercato in tempo reale e fornisce insights automatici.

## Caratteristiche Principali

### 🤖 Analisi Automatica
- **Monitoraggio Continuo**: Analizza tutte le crypto configurate ogni 30 minuti (configurabile)
- **Multi-Timeframe**: Analizza su 15m, 1h, 4h, 1d simultaneamente
- **Zero Configurazione**: Funziona out-of-the-box senza setup manuale

### 📊 Indicatori Tecnici
- **EMA (20, 50)**: Media esponenziale per trend detection
- **RSI**: Relative Strength Index per identificare ipercomprato/ipervenduto
- **Trend Analysis**: Rileva direzione e forza del trend
- **Forza Relativa vs BTC**: Confronta performance di ogni crypto vs Bitcoin

### 🔄 Segnali di Inversione
- **EMA Crossover**: Rileva attraversamenti bullish/bearish
- **RSI Estremi**: Identifica zone di ipercomprato (>70) e ipervenduto (<30)
- **Divergenze**: Rileva divergenze tra prezzo e indicatori
- **Breakout Detection**: Identifica possibili breakout da consolidamenti

### 📱 Notifiche Telegram Automatiche
- **Segnali Periodici**: Report completo ogni ora (configurabile)
- **Alert Immediati**: Notifiche istantanee per eventi importanti
- **Performance Extreme**: Alert per movimenti >10% nell'ultima ora
- **Crossover Alerts**: Notifiche immediate per crossover EMA significativi

## Come Funziona

### 1. Simboli Analizzati
Il sistema analizza automaticamente:
- **Simboli Default**: BTC, ETH, BNB, ADA, XRP, SOL, DOT, DOGE, AVAX, LINK, etc.
- **Simboli Custom**: Aggiunge automaticamente i simboli custom configurati nel sistema Alert
- **Auto-Discovery**: Si aggiorna automaticamente quando aggiungi nuovi simboli custom

### 2. Processo di Analisi

```
Ogni 30 minuti (default):
├── Scarica dati OHLC per tutti i simboli
├── Calcola indicatori tecnici (EMA, RSI)
├── Analizza trend e forza relativa vs BTC
├── Rileva segnali di inversione
├── Genera sommario mercato
└── Salva risultati per dashboard

Ogni 60 minuti (default):
├── Prende ultima analisi
├── Genera report mercato
├── Invia segnali via Telegram
└── Invia alert specifici per eventi importanti
```

### 3. Tipi di Segnali Automatici

#### **Report Mercato Completo** (ogni ora)
```
🤖 ANALISI AUTOMATICA MERCATO

📊 Sommario Mercato
🔍 Simboli analizzati: 20
⏰ 14:30:25

💪 TOP PERFORMERS (1h)
🚀 SOLUSDT: +8.45%
📈 AVAXUSDT: +5.23%
📈 DOGEUSDT: +3.12%

📉 WEAK PERFORMERS (1h)
🔻 XRPUSDT: -6.78%
📉 ADAUSDT: -4.56%

🔄 POSSIBILI INVERSIONI
🟢 BTCUSDT - RSI: 28.5
    └ RSI_OVERSOLD, BULLISH_DIVERGENCE
```

#### **Alert Performance Estrema**
```
🚨 PERFORMANCE ESTREMA! 🚀

💰 SOLUSDT ha guadagnato +12.45% nell'ultima ora!

📊 RSI: 78.5
📈 Trend: BULLISH

⚠️ Monitora per possibili prese di profitto!
```

#### **Alert Crossover EMA**
```
🔄 CROSSOVER BULLISH! 📈

💰 AVAXUSDT ha attraversato al rialzo l'EMA(20)!

💲 Prezzo: $34.567
📊 RSI: 65.2
🎯 EMA(20): $34.234

🚀 Possibile inizio trend rialzista!
```

## Dashboard e Controlli

### 🖥️ Interfaccia Web
Accedi a: `http://localhost:5000/market-analysis`

#### **Controlli Principali**
- **Avvia/Ferma Sistema**: Controllo completo del sistema automatico
- **Analisi Immediata**: Esegui analisi on-demand
- **Invia Segnali**: Forza invio segnali Telegram
- **Test Telegram**: Verifica funzionamento notifiche

#### **Visualizzazioni**
- **Sommario Mercato**: Top/worst performers, inversioni, trend forti
- **Analisi Dettagliata**: Grid con tutti i simboli e metriche
- **Filtri Timeframe**: Visualizza analisi per 1h, 4h, 1d
- **Cronologia**: Storico delle analisi eseguite

### ⚙️ Configurazione

#### **Intervalli**
- **Analisi**: 5-180 minuti (default: 30)
- **Segnali**: 15-360 minuti (default: 60)

#### **Soglie**
- **Forza vs BTC**: 1-20% (default: 5%)
- **RSI**: Periods e soglie per ipercomprato/ipervenduto
- **Trend**: Candele minime per conferma trend

#### **Timeframes**
- Configurabili: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d
- Default: 15m, 1h, 4h, 1d

## Integrazione con Sistema Esistente

### 🔗 Compatibilità con Alert Manuali
- **Simboli Condivisi**: Usa automaticamente i simboli custom degli Alert
- **Telegram Condiviso**: Utilizza lo stesso bot Telegram configurato
- **Database Separato**: Non interferisce con alert manuali esistenti

### 📊 API Endpoints
```
GET  /market-analysis/api/status          # Stato sistema
POST /market-analysis/api/start           # Avvia analisi automatica
POST /market-analysis/api/stop            # Ferma analisi automatica
POST /market-analysis/api/analyze-now     # Analisi immediata
GET  /market-analysis/api/last-analysis   # Ultima analisi
GET  /market-analysis/api/market-summary  # Sommario mercato
POST /market-analysis/api/config          # Aggiorna configurazione
```

## Esempi d'Uso

### 1. Monitoraggio Passivo
```
1. Vai su http://localhost:5000/market-analysis
2. Clicca "Avvia Sistema"
3. Il sistema inizia analisi automatiche ogni 30 min
4. Ricevi report Telegram ogni ora
5. Alert immediati per eventi importanti
```

### 2. Analisi On-Demand
```
1. Clicca "Analisi Immediata" 
2. Visualizza risultati in tempo reale
3. Clicca su simboli per dettagli
4. Invia segnali manualmente se necessario
```

### 3. Configurazione Personalizzata
```
1. Modifica intervalli nella sidebar
2. Imposta soglie personalizzate
3. Clicca "Salva Config"
4. Il sistema si adatta automaticamente
```

## Differenze con Sistema Alert Manuale

| Caratteristica | Alert Manuali | Analisi Automatica |
|---|---|---|
| **Setup** | Manuale per ogni simbolo | Automatico per tutti |
| **Trigger** | Soglie fisse configurate | Algoritmi di analisi |
| **Simboli** | Singoli alert configurati | Tutti i simboli disponibili |
| **Analisi** | Prezzo/EMA specifici | Multi-indicatore completo |
| **Frequenza** | Controllo continuo | Analisi periodiche |
| **Segnali** | Solo al trigger | Report periodici + trigger |
| **Uso** | Alert specifici | Overview mercato completo |

## Best Practices

### 🎯 Uso Ottimale
1. **Analisi Automatica** per overview generale del mercato
2. **Alert Manuali** per soglie specifiche su simboli di interesse
3. **Combinazione** per copertura completa

### 📱 Notifiche Telegram
- Configura gruppi diversi per Alert vs Analisi se necessario
- Usa analisi automatica per sentiment generale
- Usa alert manuali per entry/exit specifici

### ⚡ Performance
- Sistema ottimizzato per 20-50 simboli simultanei
- Analisi distribuite nel tempo per non sovraccaricare API
- Cache intelligente per evitare richieste duplicate

## Risoluzione Problemi

### ❌ Sistema Non Si Avvia
```
1. Verifica configurazione Telegram in config.py
2. Controlla log per errori API
3. Testa connettività con "Test Telegram"
4. Riavvia applicazione se necessario
```

### 📡 Notifiche Non Arrivano
```
1. Verifica TELEGRAM_TOKEN e CHAT_ID
2. Controlla bot Telegram autorizzato
3. Testa con "Test Telegram" button
4. Verifica stato sistema in dashboard
```

### 🐌 Analisi Lente
```
1. Riduci numero simboli custom se troppi
2. Aumenta intervallo analisi (es. 60 min)
3. Riduci timeframes analizzati
4. Monitora log per errori API rate limiting
```

## Roadmap Futuri Sviluppi

### 🔮 Features Pianificate
- **Machine Learning**: Predizioni basate su pattern storici
- **Sentiment Analysis**: Integrazione news e social sentiment
- **Correlation Analysis**: Analisi correlazioni cross-crypto
- **Advanced Patterns**: Riconoscimento pattern candlestick
- **Portfolio Optimization**: Suggerimenti allocazione

### 🚀 Miglioramenti Tecnici
- **Real-time WebSocket**: Aggiornamenti live in dashboard
- **Multiple Exchange**: Supporto Coinbase, Kraken, etc.
- **Advanced Backtesting**: Test strategie su dati storici
- **Custom Strategies**: Framework per strategie personalizzate

---

Il sistema di **Analisi Automatica** trasforma il tuo trading bot da un semplice executor di strategie a un vero **assistente di trading intelligente** che monitora il mercato 24/7 e ti tiene informato sui movimenti più importanti!



📊 Guida al Sistema di Indicatori e Segnali
🎯 Indicatori Tecnici Principali
1. RSI (Relative Strength Index)

Valore: 0-100

Periodo standard: 14

Zone operative:

< 30 → Oversold (Ipervenduto)

> 70 → Overbought (Ipercomprato)

30-70 → Zona Neutrale

2. EMA (Exponential Moving Average)

EMA(20): Media veloce, utile per trend e crossover.

EMA(50): Media lenta, conferma il trend.

Utilizzo:

Individuazione del trend.

Identificazione di supporti e resistenze dinamici.

3. Trend Analysis

Direzione: BULLISH, BEARISH, NEUTRAL

Forza: Percentuale di movimento del trend

Durata: Numero di candele consecutive nel trend

Logica: Trend determinato dalla posizione del prezzo rispetto a EMA(20)

4. Forza Relativa vs BTC

VERY_STRONG: > +5% (configurabile)

STRONG: +2% → +5%

NEUTRAL: -2% → +2%

WEAK: -5% → -2%

VERY_WEAK: < -5%

🚨 Segnali di Inversione

EMA Crossover Signals

RSI Extreme Signals

Divergence Signals

📈 Metriche Aggiuntive
Performance Metrics

Variazione 24h: Percentuale di cambio prezzo.

Prezzo Corrente: Valore attuale del simbolo.

Distance from EMA: Distanza del prezzo dalle medie.

Multi-Timeframe Analysis

15 minuti: Segnali a breve termine.

1 ora: Trend intermedio.

4 ore: Movimento medio-lungo.

1 giorno: Analisi macro.

🎪 Esempi Completi di Segnali

Scenario Bullish Perfetto

Scenario Bearish Warning

Scenario Neutral / Accumulation

🔧 Configurazioni Soglie

RSI Thresholds

Strength vs BTC Thresholds

Trend Detection

🎯 Interpretazione dei Segnali
Segnali di Entrata (Buy)

BULLISH_EMA_CROSSOVER + RSI_OVERSOLD

BULLISH_DIVERGENCE su timeframe alti

Trend BEARISH → BULLISH con forza STRONG

Segnali di Uscita (Sell)

BEARISH_EMA_CROSSOVER + RSI_OVERBOUGHT

BEARISH_DIVERGENCE su trend forte

Forza vs BTC da STRONG → WEAK

Segnali di Attenzione

RSI_OVERBOUGHT durante trend bullish forte

BEARISH_DIVERGENCE dopo un rally

Durata trend molto lunga (> 50 candele)

🚀 Combinazioni Potenti

Il sistema è potente perché combina più segnali tra loro:

Analisi tecnica classica

Analisi della forza relativa

Il risultato è un quadro completo della situazione di mercato, utile per individuare entrate, uscite e momenti di attenzione.