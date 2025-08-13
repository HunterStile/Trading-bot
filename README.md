# 🤖 Trading Bot - Sistema Automatizzato di Trading su Bybit

Questo è un sistema completo di trading automatizzato che opera sulla piattaforma Bybit, con funzionalità di analisi tecnica, notifiche Telegram e gestione automatica delle posizioni.

## 📁 Struttura del Progetto

```
Trading-bot/
├── config.py                      # Configurazioni API e chiavi
├── trading_functions.py            # Funzioni principali di trading e analisi
├── test_api.py                     # 🆕 Test completo delle API
├── backtest.py                     # 🆕 🧪 Sistema di Backtesting
├── Apertura e chiusura operazioni.py  # Bot principale per trading automatico
├── chiusura operazioni.py          # Bot per trailing stop
├── Alert.py                        # Sistema di alert prezzo semplice
├── Telegrambot_allert.py          # Bot Telegram per alert singoli
├── Telgrambot_Multiallert          # Bot Telegram per alert multipli
├── acquisire_id.py                 # Utility per ottenere chat ID Telegram
├── requirements.txt                # 🆕 Dipendenze Python
├── .env                           # 🆕 Variabili d'ambiente (chiavi API)
├── .env.example                   # 🆕 Template configurazione
├── .gitignore                     # 🆕 File da escludere da Git
└── README.md                       # Questa documentazione
```

## 🎯 Componenti Principali

### 1. **config.py** - Configurazioni
Contiene tutte le chiavi API e configurazioni necessarie:
- **API Bybit**: `api` e `api_sec` per l'accesso all'exchange
- **Telegram**: `TELEGRAM_TOKEN` e `CHAT_ID` per le notifiche
- **Spotify**: Configurazioni per integrazioni audio (opzionale)
- **Browser**: Percorsi per automazione web

### 2. **trading_functions.py** - Libreria Principale
È il cuore del sistema, contiene tutte le funzioni specializzate:

#### 📊 Funzioni di Analisi Tecnica
- `media_esponenziale()`: Calcola EMA (Exponential Moving Average)
- `controlla_candele_sopra_ema()`: Verifica quante candele consecutive sono sopra l'EMA
- `controlla_candele_sotto_ema()`: Verifica quante candele consecutive sono sotto l'EMA
- `analizza_prezzo_sopra_media()`: Analizza se il prezzo attuale è sopra/sotto l'EMA

#### 💰 Funzioni di Trading Bybit
- `compra_moneta_bybit_by_quantita()`: Acquista per importo in USDT
- `vendi_moneta_bybit_by_quantita()`: Vende per importo in USDT
- `chiudi_operazione_long()`: Chiude posizione long
- `chiudi_operazione_short()`: Chiude posizione short
- `vedi_prezzo_moneta()`: Ottiene prezzo di mercato in tempo reale

#### 📈 Funzioni di Monitoraggio
- `get_kline_data()`: Scarica dati candlestick storici
- `nuova_candela()`: Rileva formazione di nuove candele
- `mostra_saldo()`: Visualizza saldo del wallet

#### 🔍 Funzioni di Web Scraping
- `Scraping_binance()`: Monitora annunci di nuove liste su Binance
- `scrape_cryptopanic()`: Raccoglie notizie crypto da CryptoPanic

### 3. **Bot di Trading Automatico**

#### **Apertura e chiusura operazioni.py** - Bot Principale
Questo è il **bot di trading automatico completo** che:

**Strategia Implementata:**
1. **Analisi Multi-Timeframe**: Controlla trend su intervalli diversi
2. **Condizioni di Entrata**:
   - Minimo X candele consecutive sopra/sotto EMA
   - Prezzo non troppo distante dall'EMA (parametro `lunghezza`)
   - Conferma su timeframe più piccolo (1 minuto)
3. **Gestione Posizione**: Apre posizione long/short automaticamente
4. **Trailing Stop**: Passa automaticamente al trailing stop

**Parametri Configurabili:**
```python
simbolo = "AVAXUSDT"              # Criptovaluta da tradare
operazione = True                 # True = Long, False = Short
quantita = 50                     # Quantità in USDT
categoria = "linear"              # Tipo di contratto (Futures)
intervallo = 30                   # Timeframe principale (minuti)
periodo_ema = 10                  # Periodo EMA
candele_open = 3                  # Candele richieste per aprire
candele_stop = 3                  # Candele richieste per chiudere
lunghezza = 1                     # Distanza massima % da EMA
```

#### **chiusura operazioni.py** - Trailing Stop
Bot specializzato per gestire il **trailing stop** di posizioni già aperte:
- Monitora posizioni esistenti
- Chiude automaticamente quando le condizioni di uscita sono soddisfatte
- Protegge i profitti seguendo il trend

### 4. **Sistema di Alert e Notifiche**

#### **Alert.py** - Alert Semplice
Sistema base per monitorare un singolo prezzo:
- Inserimento manuale di simbolo e prezzo target
- Notifica Telegram quando raggiunto
- Apertura automatica del browser su Bybit

#### **Telegrambot_allert.py** - Bot Telegram Singolo
Bot Telegram interattivo per gestire un alert alla volta:
- Interfaccia conversazionale
- Monitoraggio continuo in background
- Notifiche automatiche

#### **Telgrambot_Multiallert** - Bot Telegram Multiplo
Bot Telegram avanzato per gestire **alert multipli simultanei**:
- **Comandi disponibili**:
  - `/start`: Crea nuovo alert
  - `/show`: Mostra tutti gli alert attivi
  - `/cancel`: Annulla operazione
- **Funzionalità**:
  - Alert multipli in parallelo
  - Monitoraggio real-time di tutti i prezzi
  - Gestione automatica dei thread

## ⚙️ Setup e Installazione

### 1. Prerequisiti
```bash
pip install -r requirements.txt
```

### 2. Configurazione Sicura
1. **Clona/Scarica il repository**
2. **Crea il file .env**: Copia il file `.env` e inserisci le tue chiavi:
```bash
# API Bybit
BYBIT_API_KEY=la_tua_api_key_bybit
BYBIT_API_SECRET=la_tua_secret_key_bybit

# Configurazione Telegram
TELEGRAM_TOKEN=il_token_del_tuo_bot_telegram
TELEGRAM_CHAT_ID=il_tuo_chat_id

# Configurazione Spotify (opzionale)
SPOTIFY_CLIENT_ID=client_id_spotify
SPOTIFY_CLIENT_SECRET=client_secret_spotify

# Configurazione Browser
CHROME_DRIVER_PATH=C:\path\to\chromedriver.exe
CHROME_BINARY_PATH=C:\path\to\chrome.exe
```

### 3. Ottenere le Chiavi API

#### Bybit API
1. Vai su [Bybit](https://www.bybit.com) → Account → API Management
2. Crea una nuova API Key
3. **IMPORTANTE**: Abilita solo i permessi necessari (Trading, Wallet)
4. Copia API Key e Secret nel file `.env`

#### Telegram Bot
1. Cerca @BotFather su Telegram
2. Usa `/newbot` per creare un nuovo bot
3. Copia il token nel file `.env`
4. Esegui `python acquisire_id.py` per ottenere il tuo chat ID

### 4. Test delle API
```bash
# Installa le dipendenze
pip install -r requirements.txt

# Testa tutte le API configurate
python test_api.py
```

**Il test verificherà:**
- ✅ Connessione API Bybit
- ✅ Accesso al saldo del wallet  
- ✅ Recupero prezzi in tempo reale
- ✅ Dati storici candlestick
- ✅ Permessi API configurati
- ⚠️ Telegram (se configurato)

**Output di successo:**
```
🎉 TUTTI I TEST PRINCIPALI SUPERATI!
🚀 Il bot è pronto per essere utilizzato!
```

## 🟢 **STATUS SISTEMA - PRONTO ALL'USO!**

Dopo i test delle API, il tuo bot è **completamente operativo** per il trading automatico:

### ✅ **Componenti Funzionanti**
- **🔥 Bybit API**: Connesse e testate con successo
- **💰 Wallet**: Saldo disponibile (0.68 USDT)
- **📊 Market Data**: Prezzi e candlestick in tempo reale
- **🤖 Trading Functions**: Tutte le funzioni operative
- **⚙️ Permessi API**: Configurazione corretta per trading

### 🎯 **Permessi API Bybit Configurati**
```
✅ Contracts - Orders Positions    → Trading Futures
✅ USDC Contracts - Trade          → Trading USDC
✅ Unified Trading - Trade         → Trading Unificato  
✅ SPOT - Trade                    → Trading Spot
✅ Wallet - Account Transfer       → Gestione Fondi
✅ Exchange - Convert History      → Conversioni
```

### 🚀 **Cosa Puoi Fare Ora**
1. **🧪 BACKTEST (RACCOMANDATO)**: Esegui `python backtest.py`
2. **Trading Automatico**: Esegui `python "Apertura e chiusura operazioni.py"`
3. **Trailing Stop**: Esegui `python "chiusura operazioni.py"`  
4. **Alert Prezzi**: Esegui `python Alert.py`
5. **Analisi Mercato**: Usa le funzioni in `trading_functions.py`

### 🧪 **Backtesting - INIZIA SEMPRE DA QUI!**

**Prima di fare trading reale, TESTA la strategia:**

```bash
# Avvia il sistema di backtesting
python backtest.py
```

**🎯 Opzioni di Backtesting:**
1. **Test Rapido BTC**: Testa la strategia EMA su Bitcoin (30 giorni)
2. **Test ETH**: Strategia su Ethereum  
3. **Simbolo Personalizzato**: Testa qualsiasi coppia (AVAXUSDT, SOLUSDT...)
4. **Ottimizzazione**: Trova i parametri migliori automaticamente
5. **Confronto Timeframes**: Scopri quale timeframe funziona meglio

**📊 Cosa Testa il Backtest:**
- ✅ Strategia EMA su dati storici reali
- ✅ Simulazione apertura/chiusura posizioni  
- ✅ Calcolo profitti/perdite
- ✅ Win rate e statistiche dettagliate
- ✅ Suggerimenti per ottimizzazione

**💡 Esempio Output:**
```
💰 Capitale iniziale: $1000.00
💰 Capitale finale: $1150.30  
📈 Rendimento: $150.30 (15.03%)
🔄 Numero di trades: 8
✅ Trades vincenti: 6 (75.0%)
🎯 Miglior trade: $89.45
```

### ⚠️ **Raccomandazioni Prima del Trading Live**
- 🧪 **Testnet**: Considera di testare prima su ambiente demo
- 💵 **Capitale**: Inizia con importi piccoli per testare la strategia
- 📱 **Telegram**: Configura le notifiche per monitoraggio remoto
- 📈 **Backtest**: Testa la strategia EMA su dati storici

---

## 🚀 Come Utilizzare

### Trading Automatico Completo
```bash
python "Apertura e chiusura operazioni.py"
```
Il bot:
1. Analizza il mercato secondo la strategia EMA
2. Apre posizioni quando le condizioni sono soddisfatte
3. Gestisce automaticamente il trailing stop
4. Invia notifiche di ogni operazione

### Solo Trailing Stop
```bash
python "chiusura operazioni.py"
```
Per gestire posizioni già aperte manualmente.

### Alert Multipli Telegram
```bash
python Telgrambot_Multiallert
```
Avvia il bot Telegram per creare e gestire più alert contemporaneamente.

### Alert Singolo
```bash
python Alert.py
```
Per un singolo alert con inserimento manuale.

## 📊 Strategia di Trading

### Logica della Strategia EMA
1. **Identificazione Trend**: Utilizza EMA per determinare la direzione
2. **Conferma Momentum**: Richiede X candele consecutive nella direzione
3. **Entry Ottimizzato**: Attende prezzi vicini all'EMA per entry migliori
4. **Multi-Timeframe**: Conferma su timeframe più piccolo
5. **Risk Management**: Trailing stop automatico basato su EMA

### Vantaggi del Sistema
- ✅ **Completamente Automatizzato**: Zero intervento manuale
- ✅ **Risk Management**: Trailing stop integrato
- ✅ **Notifiche Real-time**: Aggiornamenti via Telegram
- ✅ **Backtesting**: Analisi storica con dati Kline
- ✅ **Configurabile**: Parametri adattabili a diverse strategie
- ✅ **Multi-Asset**: Funziona su qualsiasi coppia Bybit

## ⚠️ Sicurezza e Best Practices

### 🔒 Gestione Sicura delle API
- ✅ **Mai committare** il file `.env` su Git
- ✅ **Permissions minime**: Abilita solo i permessi strettamente necessari
- ✅ **IP Whitelist**: Limita l'accesso API al tuo IP
- ✅ **Testnet prima**: Testa sempre su ambiente di test
- ✅ **Backup sicuro**: Salva le chiavi in un password manager

### 🛡️ Misure di Protezione
- **File .env**: Tutte le chiavi sono in variabili d'ambiente
- **Gitignore**: Impedisce commit accidentali di file sensibili
- **Permissions API**: Limita le azioni possibili
- **Error Handling**: Gestione sicura degli errori API

### ⚠️ Avvertenze e Rischi

- **RISCHIO ELEVATO**: Il trading automatizzato può causare perdite significative
- **Testare**: Utilizza sempre l'ambiente testnet prima del live
- **Monitoraggio**: Controlla regolarmente le posizioni aperte
- **Volatilità**: Le crypto sono estremamente volatili
- **Connessione**: Assicurati di avere connessione internet stabile

## 🔧 Personalizzazioni Possibili

### Modifica Strategia
- Cambia periodo EMA nel file principale
- Aggiungi altri indicatori tecnici
- Modifica condizioni di entrata/uscita

### Integrazione Altri Exchange
- Adatta le funzioni API per altri exchange
- Modifica la struttura dati dei prezzi

### Alert Avanzati
- Aggiungi alert su indicatori tecnici
- Integra analisi sentiment
- Webhook per Discord/Slack

## 📝 Note Tecniche

- **Linguaggio**: Python 3.7+
- **API**: Bybit Unified Trading API
- **Threading**: Gestione multi-thread per alert paralleli
- **Error Handling**: Gestione errori di rete e API
- **Logging**: Sistema di log per debugging

---

**⚡ Questo è un sistema professionale di trading automatizzato. Usalo responsabilmente e solo con capitale che puoi permetterti di perdere.**
