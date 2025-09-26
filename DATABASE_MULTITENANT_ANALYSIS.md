# 📊 ANALISI DATABASE ESISTENTE - Multi-Tenant Schema Design

## 🔍 Schema Attuale (Single-Tenant)

### Tabelle Esistenti
```sql
-- ✅ CORE TABLES
trading_sessions (id, session_id, start_time, end_time, symbol, strategy_config, ...)
trades (id, session_id, trade_id, symbol, side, entry_time, exit_time, ...)
trade_id_mapping (id, internal_trade_id, external_trade_id, bybit_order_id, ...)

-- ✅ ANALYSIS & MONITORING  
market_analysis (id, timestamp, symbol, price, ema_value, trend_direction, ...)
system_events (id, timestamp, event_type, event_category, message, ...)
daily_performance (id, date, starting_balance, ending_balance, daily_pnl, ...)

-- ✅ CONFIGURATION
bot_configurations (id, config_name, config_data, is_active, ...)
```

---

## 🏗️ Schema Multi-Tenant Proposto

### 🆔 USERS & AUTHENTICATION
```sql
-- Tabella utenti principale
users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL, 
    username TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    subscription_tier TEXT DEFAULT 'FREE',
    api_key TEXT UNIQUE,
    api_secret_hash TEXT,
    bybit_api_key_hash TEXT,
    bybit_api_secret_hash TEXT,
    telegram_chat_id TEXT,
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    is_active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Campi SaaS
    trial_end_date TIMESTAMP,
    subscription_start_date TIMESTAMP,
    subscription_end_date TIMESTAMP,
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0
);

-- Tabella sessioni utente
user_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    refresh_token TEXT UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### 💳 SUBSCRIPTION & BILLING
```sql
-- Piani di abbonamento
subscription_plans (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    
    -- Limiti del piano
    max_trades_per_month INTEGER,
    max_active_strategies INTEGER,
    max_symbols INTEGER,
    has_advanced_ai BOOLEAN DEFAULT 0,
    has_api_access BOOLEAN DEFAULT 0,
    has_backtesting BOOLEAN DEFAULT 0,
    has_telegram_alerts BOOLEAN DEFAULT 0,
    has_priority_support BOOLEAN DEFAULT 0,
    
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sottoscrizioni utenti
user_subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, CANCELLED, EXPIRED, TRIAL
    
    -- Stripe/Payment info
    stripe_subscription_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    
    -- Date e billing
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    next_billing_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    
    -- Usage tracking
    current_period_trades INTEGER DEFAULT 0,
    current_period_start TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans (id)
);
```

### 🤖 MULTI-TENANT TRADING TABLES
```sql
-- ✨ Sessioni trading (con user_id)
user_trading_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    symbol TEXT NOT NULL,
    strategy_config TEXT NOT NULL,
    
    -- Performance metrics
    initial_balance REAL,
    final_balance REAL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    
    -- Status e metadata
    status TEXT DEFAULT 'ACTIVE',
    notes TEXT,
    is_paper_trading BOOLEAN DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, session_id)
);

-- ✨ Trades per utente 
user_trades (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    
    -- Trade details
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    
    -- P&L e fees
    pnl REAL,
    fee REAL DEFAULT 0,
    pnl_percentage REAL,
    
    -- Metadata
    status TEXT DEFAULT 'OPEN',
    strategy_signal TEXT,
    notes TEXT,
    
    -- Exchange integration
    bybit_order_id TEXT,
    external_trade_id TEXT,
    
    -- Paper trading
    is_paper_trade BOOLEAN DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (user_id, session_id) REFERENCES user_trading_sessions (user_id, session_id),
    UNIQUE(user_id, trade_id)
);
```

### 📊 USER ANALYTICS & PERFORMANCE
```sql
-- Performance giornaliera per utente
user_daily_performance (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    
    -- Balance tracking
    starting_balance REAL NOT NULL,
    ending_balance REAL NOT NULL,
    daily_pnl REAL NOT NULL,
    daily_pnl_percentage REAL,
    
    -- Trade stats
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    
    -- Risk metrics
    max_drawdown REAL DEFAULT 0,
    sharpe_ratio REAL,
    volatility REAL,
    
    -- Additional data
    data TEXT, -- JSON per metriche custom
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, date)
);

-- Analisi mercato per utente (cache personalizzata)
user_market_analysis (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    
    -- Market data
    price REAL NOT NULL,
    ema_value REAL,
    ema_period INTEGER,
    candles_above_ema INTEGER,
    distance_from_ema REAL,
    trend_direction TEXT,
    volume REAL,
    
    -- User-specific analysis
    analysis_data TEXT, -- JSON
    user_notes TEXT,
    is_watchlist BOOLEAN DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### 🔧 USER CONFIGURATIONS & STRATEGIES
```sql
-- Configurazioni bot per utente
user_bot_configurations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config_name TEXT NOT NULL,
    
    -- Configuration data
    config_data TEXT NOT NULL, -- JSON
    is_active BOOLEAN DEFAULT 0,
    is_default BOOLEAN DEFAULT 0,
    
    -- Strategy details
    strategy_type TEXT,
    risk_level TEXT DEFAULT 'MEDIUM',
    max_position_size REAL,
    stop_loss_percentage REAL,
    take_profit_percentage REAL,
    
    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, config_name)
);

-- Strategie personalizzate utente
user_strategies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_description TEXT,
    
    -- Strategy logic (JSON)
    strategy_config TEXT NOT NULL,
    entry_conditions TEXT, -- JSON
    exit_conditions TEXT,  -- JSON
    risk_management TEXT,  -- JSON
    
    -- Performance tracking
    total_uses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_pnl REAL DEFAULT 0,
    
    -- Metadata
    is_public BOOLEAN DEFAULT 0, -- Per marketplace futuro
    is_active BOOLEAN DEFAULT 1,
    version INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, strategy_name)
);
```

### 📱 USER ALERTS & NOTIFICATIONS
```sql
-- Alert personalizzati utente
user_alerts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    alert_name TEXT NOT NULL,
    
    -- Alert configuration
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL, -- PRICE, EMA_CROSS, VOLUME, CUSTOM
    condition_data TEXT NOT NULL, -- JSON
    
    -- Notification preferences
    notify_telegram BOOLEAN DEFAULT 0,
    notify_email BOOLEAN DEFAULT 0,
    notify_dashboard BOOLEAN DEFAULT 1,
    
    -- Status
    is_active BOOLEAN DEFAULT 1,
    triggered_count INTEGER DEFAULT 0,
    last_triggered TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, alert_name)
);

-- Sistema eventi per utente
user_system_events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Event details
    event_type TEXT NOT NULL,
    event_category TEXT NOT NULL,
    message TEXT NOT NULL,
    data TEXT, -- JSON
    
    -- Classification
    severity TEXT DEFAULT 'INFO', -- INFO, WARNING, ERROR, CRITICAL
    is_read BOOLEAN DEFAULT 0,
    
    -- Context
    session_id TEXT,
    trade_id TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### 📈 USAGE TRACKING & ANALYTICS
```sql
-- Tracking utilizzo API per utente
user_api_usage (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    
    -- API calls tracking
    total_requests INTEGER DEFAULT 0,
    trading_requests INTEGER DEFAULT 0,
    analysis_requests INTEGER DEFAULT 0,
    backtest_requests INTEGER DEFAULT 0,
    
    -- Limits
    daily_limit INTEGER,
    requests_remaining INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, date)
);

-- Log accessi utente
user_activity_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Activity details
    activity_type TEXT NOT NULL, -- LOGIN, LOGOUT, TRADE, CONFIG_CHANGE, etc.
    ip_address TEXT,
    user_agent TEXT,
    endpoint TEXT,
    
    -- Context data
    data TEXT, -- JSON per dati aggiuntivi
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

---

## 🔄 Migrazione da Single-Tenant a Multi-Tenant

### Step 1: Aggiungere user_id alle tabelle esistenti
```sql
-- Backup tabelle esistenti
CREATE TABLE trading_sessions_backup AS SELECT * FROM trading_sessions;
CREATE TABLE trades_backup AS SELECT * FROM trades;

-- Aggiungere colonna user_id 
ALTER TABLE trading_sessions ADD COLUMN user_id INTEGER DEFAULT 1;
ALTER TABLE trades ADD COLUMN user_id INTEGER DEFAULT 1;
ALTER TABLE market_analysis ADD COLUMN user_id INTEGER DEFAULT 1;
ALTER TABLE system_events ADD COLUMN user_id INTEGER DEFAULT 1;
ALTER TABLE daily_performance ADD COLUMN user_id INTEGER DEFAULT 1;
ALTER TABLE bot_configurations ADD COLUMN user_id INTEGER DEFAULT 1;

-- Creare utente "admin" per dati esistenti
INSERT INTO users (id, email, username, subscription_tier) 
VALUES (1, 'admin@localhost', 'admin', 'PRO');
```

### Step 2: Creare indici per performance
```sql
-- Indici per query multi-tenant efficienti
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_api_key ON users (api_key);
CREATE INDEX idx_trading_sessions_user_id ON user_trading_sessions (user_id);
CREATE INDEX idx_trades_user_id ON user_trades (user_id);
CREATE INDEX idx_trades_user_session ON user_trades (user_id, session_id);
CREATE INDEX idx_daily_performance_user_date ON user_daily_performance (user_id, date);
CREATE INDEX idx_api_usage_user_date ON user_api_usage (user_id, date);
```

---

## 🎯 Benefici Schema Multi-Tenant

### ✅ Scalabilità
- Supporto illimitato utenti
- Isolamento dati per utente
- Performance ottimizzate con indici

### ✅ Funzionalità SaaS
- Sistema subscription completo
- Usage tracking e limits
- User activity monitoring  

### ✅ Sicurezza
- Isolamento dati totale
- API key per utente
- Session management sicuro

### ✅ Business Features
- Diversi piani abbonamento
- Analytics per revenue
- User behavior tracking

---

**Prossimo Step**: Implementare tabelle users e subscription_plans come base