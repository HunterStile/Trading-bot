# 📋 INVENTARIO FUNZIONI TRADING - API Transformation

## 🔍 Analisi Funzioni in `core/trading_functions.py`

### 🏷️ CATEGORIZZAZIONE FUNZIONI (923 righe totali)

---

## 🌐 **WEB SCRAPING & NEWS** (7 funzioni)
❌ Non necessarie per SaaS - Rimuovere o sostituire con API

```python
def configurazione_browser()         # ❌ Selenium setup
def Scraping_binance(query,driver)   # ❌ Web scraping
def scrape_cryptopanic()             # ❌ News scraping  
def save_to_txt(news_items, ...)     # ❌ File operations
def scroll_to_bottom(driver)         # ❌ Browser automation
def is_string_in_title(title, query) # ❌ Scraping helper
def is_duplicate_title(file_path, title) # ❌ File helper
```

**Sostituzione SaaS**: API di news integrate (CoinGecko, NewsAPI, etc.)

---

## 📁 **FILE OPERATIONS** (5 funzioni)  
⚠️ Da sostituire con database operations

```python
def leggi_txt(nome_file)              # ⚠️ -> Database read
def save_list_to_file(lst, filename)  # ⚠️ -> Database save  
def is_name_in_string(name, string)   # ✅ Utility - Mantieni
def leggi_simboli_da_file(nome_file)  # ⚠️ -> Database/Config
def save_to_txt(news_items, ...)      # ⚠️ -> Database
```

**Trasformazione SaaS**: User settings/watchlists in database

---

## ⚡ **CORE TRADING ENGINE** (18 funzioni)
✅ **FONDAMENTALI** - Trasformare in API endpoints

### 🔄 Trading Operations
```python
def compra_moneta_bybit_by_quantita(categoria,pair,quantita)  # ✅ API: POST /trade/buy
def vendi_moneta_bybit_by_quantita(categoria,pair,quantita)  # ✅ API: POST /trade/sell
def compra_moneta_bybit_by_token(categoria,pair,token)       # ✅ API: POST /trade/buy-tokens
def vendi_moneta_bybit_by_token(categoria,pair,token)        # ✅ API: POST /trade/sell-tokens
def chiudi_operazione_long(categoria,pair,token)             # ✅ API: POST /trade/close-long
def chiudi_operazione_short(categoria,pair,token)            # ✅ API: POST /trade/close-short
def compra_moneta_bybit2(categoria, pair, quantita)          # ⚠️ Duplicate?
```

### 📊 Market Data & Analysis  
```python
def vedi_prezzo_moneta(categoria,pair)                       # ✅ API: GET /market/price/{symbol}
def mostra_saldo()                                          # ✅ API: GET /account/balance
def ottieni_prezzi(categoria,simbolo)                       # ✅ API: GET /market/prices
def get_kline_data(categoria, simbolo, intervallo, limit)   # ✅ API: GET /market/klines
def get_kline_data_with_dates(categoria, simbolo, ...)      # ✅ API: GET /market/klines/range
def get_kline_printato(categoria, simbolo, intervallo, limit) # ⚠️ Debug version?
```

### 📈 Technical Analysis
```python  
def media_esponenziale(prices, period)                      # ✅ API: GET /analysis/ema
def calculate_simple_moving_average(prices, period)         # ✅ API: GET /analysis/sma
def analizza_prezzo_sopra_media(categoria, simbolo, ...)    # ✅ API: GET /analysis/price-above-ema
def controlla_candele_sopra_ema(categoria, coppia, ...)     # ✅ API: GET /analysis/candles-above-ema
def controlla_candele_sotto_ema(categoria, coppia, ...)     # ✅ API: GET /analysis/candles-below-ema
def candele_sopra_ema(categoria, simbolo, ...)              # ✅ Helper function
```

---

## 🤖 **AUTOMATED TRADING STRATEGIES** (6 funzioni)
✅ **CORE BUSINESS LOGIC** - Principale valore aggiunto SaaS

```python
def bot_open_position(categoria,simbolo,periodo_ema,intervallo,quantita,candele,lunghezza,operazione)
# ✅ API: POST /strategy/open-position
# Logica: Apre posizione basata su EMA strategy

def bot_trailing_stop(categoria,simbolo,periodo_ema,intervallo,token,candele,operazione)  
# ✅ API: POST /strategy/trailing-stop
# Logica: Gestisce trailing stop automatico

def bot_analisi(categoria,periodo_ema)
# ✅ API: GET /strategy/market-scan  
# Logica: Scansiona mercato per opportunità

def nuova_candela(kline_data, ultimo_timestamp_precedente)
# ✅ Utility: Detecta nuove candele

def estrai_ultimo_timestamp(kline_data)  
# ✅ Utility: Timestamp operations

def estrai_prezzo_ultima_candela(kline_data)
# ✅ Utility: Price extraction
```

---

## 🔧 **UTILITY & HELPERS** (8 funzioni)
✅ Funzioni di supporto - Mantieni e ottimizza

```python
def execute_thread(func, args)           # ✅ Threading utility
def get_server_time()                    # ✅ Time sync utility  
def check_timestamp(recv_window, timestamp) # ✅ Validation
def totale_pnl(quantita_acquistata, prezzo_acquisto, prezzo_attuale) # ✅ P&L calc
def scelta_moneta_operazione()           # ⚠️ User interaction - Rimuovi
```

---

## 🎯 **TRASFORMAZIONE API ENDPOINTS**

### 🔥 **HIGH PRIORITY APIs** (Core Business)

#### 1. **Trading Operations**
```javascript
POST /v1/trade/buy
POST /v1/trade/sell  
POST /v1/trade/close-position
GET  /v1/trade/positions
GET  /v1/trade/history
```

#### 2. **Market Data**
```javascript
GET /v1/market/price/{symbol}
GET /v1/market/klines/{symbol}
GET /v1/market/symbols
GET /v1/account/balance
```

#### 3. **Technical Analysis**
```javascript  
GET /v1/analysis/ema/{symbol}
GET /v1/analysis/candles-analysis/{symbol}
GET /v1/analysis/price-signals/{symbol}
POST /v1/analysis/custom-indicator
```

#### 4. **Automated Strategies** 
```javascript
POST /v1/strategy/start
POST /v1/strategy/stop  
GET  /v1/strategy/status
POST /v1/strategy/configure
GET  /v1/strategy/performance
```

### 🔥 **MEDIUM PRIORITY APIs**

#### 5. **Portfolio Management**
```javascript
GET /v1/portfolio/overview
GET /v1/portfolio/performance
GET /v1/portfolio/risk-metrics
POST /v1/portfolio/rebalance
```

#### 6. **User Management**
```javascript
GET /v1/user/profile
PUT /v1/user/settings
GET /v1/user/api-usage
GET /v1/user/subscription
```

### 🔥 **ADVANCED FEATURES**

#### 7. **Backtesting**
```javascript
POST /v1/backtest/start
GET  /v1/backtest/results/{id}
GET  /v1/backtest/history
```

#### 8. **AI Features**
```javascript
POST /v1/ai/analyze-market
GET  /v1/ai/predictions/{symbol}  
POST /v1/ai/optimize-strategy
```

---

## 📊 **REFACTORING PLAN**

### Phase 1: Core API Extraction
- [ ] **Extract trading functions** → Separate service classes
- [ ] **Remove web scraping** → Replace with external APIs
- [ ] **Database integration** → Replace file operations
- [ ] **User context** → Add user_id to all operations

### Phase 2: API Wrapper Creation
```python
# Esempio trasformazione:
# DA: def vedi_prezzo_moneta(categoria, pair)
# A:  
class TradingService:
    def __init__(self, user_id: int):
        self.user_id = user_id
        
    async def get_price(self, symbol: str) -> dict:
        # Multi-tenant price service
        # Rate limiting per user
        # Usage tracking
        return {"symbol": symbol, "price": price}
```

### Phase 3: Strategy Engine
```python
class StrategyEngine:
    def __init__(self, user_id: int):
        self.user_id = user_id
        
    async def start_strategy(self, config: dict) -> str:
        # User-specific strategy execution
        # Risk management per subscription tier
        # Performance tracking
        return strategy_id
```

---

## 💎 **CORE VALUE PROPOSITIONS per SaaS**

### 🏆 **Unique Selling Points**
1. **EMA-Based Strategies** - Algoritmi proprietari ottimizzati
2. **Multi-Timeframe Analysis** - Analisi su più timeframe
3. **Automated Trailing Stops** - Gestione risk automatica
4. **Market Scanning** - Ricerca opportunità automatica
5. **Real-time Execution** - Esecuzione ordini in tempo reale

### 🎯 **Differentiation da Concorrenti**  
- ✅ **Specializzazione EMA strategies**
- ✅ **Integration Bybit ottimizzata**  
- ✅ **Risk management avanzato**
- ✅ **User-friendly configuration**
- ✅ **Telegram integration**

---

## 📈 **BUSINESS METRICS per Funzioni**

### 📊 **Usage Tracking per API**
```python
# Esempio implementazione
@track_usage
@rate_limit_by_tier
async def execute_trade(user_id: int, trade_data: dict):
    # Traccia usage
    # Applica rate limits
    # Log per billing
    pass
```

### 💰 **Monetization per Feature**
- **FREE**: Basic price data, limited trades
- **PREMIUM**: Advanced analysis, more trades, alerts  
- **PRO**: Unlimited trades, custom strategies, API access

---

**Prossimo Step**: Iniziare refactoring con extraction delle funzioni core