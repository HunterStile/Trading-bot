import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any

class TradingDatabase:
    """Gestisce il database SQLite per lo storico trading"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Salva il database nella cartella principale del trading bot
            db_path = Path(__file__).parent.parent / "trading_data.db"
        
        self.db_path = str(db_path)
        
        # Setup logging PRIMA di init_database
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.init_database()
    
    def init_database(self):
        """Inizializza il database con tutte le tabelle necessarie"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabella sessioni di trading
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    symbol TEXT NOT NULL,
                    strategy_config TEXT NOT NULL,
                    initial_balance REAL,
                    final_balance REAL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabella trades individuali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    pnl REAL,
                    fee REAL DEFAULT 0,
                    status TEXT DEFAULT 'OPEN',
                    strategy_signal TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES trading_sessions (session_id)
                )
            ''')
            
            # Tabella analisi di mercato
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    ema_value REAL,
                    ema_period INTEGER,
                    candles_above_ema INTEGER,
                    distance_from_ema REAL,
                    trend_direction TEXT,
                    volume REAL,
                    analysis_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabella eventi di sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    event_type TEXT NOT NULL,
                    event_category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    severity TEXT DEFAULT 'INFO',
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabella performance giornaliera
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    starting_balance REAL NOT NULL,
                    ending_balance REAL NOT NULL,
                    daily_pnl REAL NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabella configurazioni bot
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            self.logger.info("Database inizializzato con successo")
    
    def start_session(self, symbol: str, strategy_config: Dict, initial_balance: float = None) -> str:
        """Avvia una nuova sessione di trading"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trading_sessions 
                (session_id, start_time, symbol, strategy_config, initial_balance)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.now(timezone.utc),
                symbol,
                json.dumps(strategy_config),
                initial_balance
            ))
            conn.commit()
        
        self.log_event("SESSION_START", "TRADING", f"Sessione {session_id} avviata per {symbol}", 
                      {"session_id": session_id, "symbol": symbol}, session_id=session_id)
        
        return session_id
    
    def end_session(self, session_id: str, final_balance: float = None):
        """Termina una sessione di trading"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Calcola statistiche sessione
            cursor.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning,
                       SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing,
                       SUM(pnl) as total_pnl
                FROM trades WHERE session_id = ? AND status = 'CLOSED'
            ''', (session_id,))
            
            stats = cursor.fetchone()
            total_trades, winning_trades, losing_trades, total_pnl = stats or (0, 0, 0, 0)
            
            # Aggiorna sessione
            cursor.execute('''
                UPDATE trading_sessions 
                SET end_time = ?, final_balance = ?, total_trades = ?, 
                    winning_trades = ?, losing_trades = ?, total_pnl = ?, status = 'COMPLETED'
                WHERE session_id = ?
            ''', (
                datetime.now(timezone.utc),
                final_balance,
                total_trades,
                winning_trades,
                losing_trades,
                total_pnl or 0,
                session_id
            ))
            conn.commit()
        
        self.log_event("SESSION_END", "TRADING", f"Sessione {session_id} terminata", 
                      {"total_trades": total_trades, "total_pnl": total_pnl}, session_id=session_id)
    
    def add_trade(self, session_id: str, symbol: str, side: str, entry_price: float, 
                  quantity: float, strategy_signal: str = None) -> str:
        """Aggiunge un nuovo trade"""
        trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades 
                (trade_id, session_id, symbol, side, entry_time, entry_price, quantity, strategy_signal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_id,
                session_id,
                symbol,
                side,
                datetime.now(timezone.utc),
                entry_price,
                quantity,
                strategy_signal
            ))
            conn.commit()
        
        self.log_event("TRADE_OPEN", "TRADING", 
                      f"Trade aperto: {side} {quantity} {symbol} @ {entry_price}", 
                      {"trade_id": trade_id, "side": side, "quantity": quantity}, 
                      session_id=session_id)
        
        return trade_id
    
    def close_trade(self, trade_id: str, exit_price: float, fee: float = 0):
        """Chiude un trade esistente"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Ottieni dati del trade
            cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
            trade = cursor.fetchone()
            
            if not trade:
                self.logger.error(f"Trade {trade_id} non trovato")
                return
            
            # Calcola PnL
            entry_price = trade[7]  # entry_price column
            quantity = trade[9]     # quantity column
            side = trade[4]         # side column
            
            if side.upper() == 'BUY':
                pnl = (exit_price - entry_price) * quantity - fee
            else:  # SELL/SHORT
                pnl = (entry_price - exit_price) * quantity - fee
            
            # Aggiorna trade
            cursor.execute('''
                UPDATE trades 
                SET exit_time = ?, exit_price = ?, pnl = ?, fee = ?, status = 'CLOSED'
                WHERE trade_id = ?
            ''', (
                datetime.now(timezone.utc),
                exit_price,
                pnl,
                fee,
                trade_id
            ))
            conn.commit()
        
        self.log_event("TRADE_CLOSE", "TRADING", 
                      f"Trade chiuso: {trade_id} PnL: {pnl:.2f}", 
                      {"trade_id": trade_id, "pnl": pnl, "exit_price": exit_price})
    
    def add_market_analysis(self, symbol: str, price: float, ema_data: Dict):
        """Salva analisi di mercato"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO market_analysis 
                (timestamp, symbol, price, ema_value, ema_period, candles_above_ema, 
                 distance_from_ema, trend_direction, analysis_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc),
                symbol,
                price,
                ema_data.get('ema_value'),
                ema_data.get('ema_period'),
                ema_data.get('candles_above_ema'),
                ema_data.get('distance_from_ema'),
                ema_data.get('trend_direction'),
                json.dumps(ema_data)
            ))
            conn.commit()
    
    def log_event(self, event_type: str, category: str, message: str, 
                  data: Dict = None, severity: str = "INFO", session_id: str = None):
        """Registra un evento di sistema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_events 
                (timestamp, event_type, event_category, message, data, severity, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc),
                event_type,
                category,
                message,
                json.dumps(data) if data else None,
                severity,
                session_id
            ))
            conn.commit()
    
    def get_session_history(self, limit: int = 50) -> List[Dict]:
        """Ottieni storico sessioni"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trading_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            ''', (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session = dict(row)
                session['strategy_config'] = json.loads(session['strategy_config'] or '{}')
                sessions.append(session)
            
            return sessions
    
    def get_trade_history(self, session_id: str = None, limit: int = 100, days: int = None) -> List[Dict]:
        """Ottieni storico trades con filtri migliorati"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Costruisci query dinamica
            query = "SELECT * FROM trades"
            params = []
            conditions = []
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            if days:
                conditions.append("entry_time >= datetime('now', '-{} days')".format(days))
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY entry_time DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            self.logger.info(f"Eseguendo query: {query} con parametri: {params}")
            
            cursor.execute(query, params)
            trades = [dict(row) for row in cursor.fetchall()]
            
            self.logger.info(f"Trovati {len(trades)} trades nel database")
            return trades
    
    # AGGIUNTI METODI DI DEBUG
    def debug_database_content(self):
        """Metodo per debug - mostra tutto il contenuto del database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            print("=== DEBUG DATABASE CONTENT ===")
            
            # Sessioni
            cursor.execute("SELECT COUNT(*) as count FROM trading_sessions")
            session_count = cursor.fetchone()[0]
            print(f"Sessioni totali: {session_count}")
            
            if session_count > 0:
                cursor.execute("SELECT session_id, symbol, start_time, status FROM trading_sessions ORDER BY start_time DESC LIMIT 5")
                print("Ultime 5 sessioni:")
                for row in cursor.fetchall():
                    print(f"  - {dict(row)}")
            
            # Trades
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            trade_count = cursor.fetchone()[0]
            print(f"Trades totali: {trade_count}")
            
            if trade_count > 0:
                cursor.execute("SELECT trade_id, session_id, symbol, side, entry_price, status FROM trades ORDER BY entry_time DESC LIMIT 5")
                print("Ultimi 5 trades:")
                for row in cursor.fetchall():
                    print(f"  - {dict(row)}")
            
            # Verifica connessioni session-trade
            cursor.execute('''
                SELECT ts.session_id, ts.symbol, COUNT(t.trade_id) as trade_count
                FROM trading_sessions ts
                LEFT JOIN trades t ON ts.session_id = t.session_id
                GROUP BY ts.session_id
            ''')
            print("Sessioni e relativi trades:")
            for row in cursor.fetchall():
                print(f"  - {dict(row)}")
    
    def verify_data_integrity(self):
        """Verifica integrità dei dati"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            print("=== VERIFICA INTEGRITÀ DATI ===")
            
            # Trades orfani (senza sessione)
            cursor.execute('''
                SELECT COUNT(*) as orphaned_trades
                FROM trades t
                LEFT JOIN trading_sessions ts ON t.session_id = ts.session_id
                WHERE ts.session_id IS NULL
            ''')
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                print(f"⚠️  Trovati {orphaned} trades orfani (senza sessione)")
                cursor.execute('''
                    SELECT trade_id, session_id FROM trades t
                    LEFT JOIN trading_sessions ts ON t.session_id = ts.session_id
                    WHERE ts.session_id IS NULL
                    LIMIT 5
                ''')
                for row in cursor.fetchall():
                    print(f"    Trade orfano: {dict(row)}")
            else:
                print("✅ Nessun trade orfano trovato")
            
            # Sessioni senza trades
            cursor.execute('''
                SELECT COUNT(*) as empty_sessions
                FROM trading_sessions ts
                LEFT JOIN trades t ON ts.session_id = t.session_id
                WHERE t.session_id IS NULL
            ''')
            empty = cursor.fetchone()[0]
            if empty > 0:
                print(f"ℹ️  Trovate {empty} sessioni senza trades")
            else:
                print("✅ Tutte le sessioni hanno trades")
    
    def fix_database_issues(self):
        """Corregge problemi comuni del database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            print("=== CORREZIONE PROBLEMI DATABASE ===")
            
            # Aggiorna contatori sessioni
            cursor.execute('''
                UPDATE trading_sessions 
                SET total_trades = (
                    SELECT COUNT(*) FROM trades 
                    WHERE trades.session_id = trading_sessions.session_id
                ),
                winning_trades = (
                    SELECT COUNT(*) FROM trades 
                    WHERE trades.session_id = trading_sessions.session_id 
                    AND trades.pnl > 0
                ),
                losing_trades = (
                    SELECT COUNT(*) FROM trades 
                    WHERE trades.session_id = trading_sessions.session_id 
                    AND trades.pnl < 0
                ),
                total_pnl = (
                    SELECT COALESCE(SUM(pnl), 0) FROM trades 
                    WHERE trades.session_id = trading_sessions.session_id
                )
            ''')
            
            updated = cursor.rowcount
            conn.commit()
            print(f"✅ Aggiornate {updated} sessioni con statistiche corrette")
    
    def get_performance_stats(self, days: int = 30) -> Dict:
        """Ottieni statistiche performance"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Statistiche generali
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss
                FROM trades 
                WHERE status = 'CLOSED' 
                AND entry_time >= datetime('now', '-{} days')
            '''.format(days))
            
            stats = cursor.fetchone()
            
            if stats and stats[0] > 0:  # total_trades > 0
                win_rate = (stats[1] / stats[0]) * 100 if stats[0] > 0 else 0
                
                return {
                    'total_trades': stats[0],
                    'winning_trades': stats[1],
                    'losing_trades': stats[2],
                    'total_pnl': stats[3] or 0,
                    'avg_pnl': stats[4] or 0,
                    'max_win': stats[5] or 0,
                    'max_loss': stats[6] or 0,
                    'win_rate': win_rate,
                    'period_days': days
                }
            else:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'max_win': 0,
                    'max_loss': 0,
                    'win_rate': 0,
                    'period_days': days
                }
    
    def get_daily_performance(self, days: int = 30) -> List[Dict]:
        """Ottieni performance giornaliera"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    DATE(entry_time) as date,
                    COUNT(*) as trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as daily_pnl
                FROM trades 
                WHERE status = 'CLOSED' 
                AND entry_time >= datetime('now', '-{} days')
                GROUP BY DATE(entry_time)
                ORDER BY date DESC
            '''.format(days))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Ottieni eventi recenti"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM system_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event['data']:
                    try:
                        event['data'] = json.loads(event['data'])
                    except:
                        pass
                events.append(event)
            
            return events
    
    def save_bot_config(self, config_name: str, config_data: Dict, set_active: bool = False):
        """Salva configurazione bot"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if set_active:
                # Disattiva tutte le altre configurazioni
                cursor.execute('UPDATE bot_configurations SET is_active = 0')
            
            cursor.execute('''
                INSERT OR REPLACE INTO bot_configurations 
                (config_name, config_data, is_active, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (
                config_name,
                json.dumps(config_data),
                1 if set_active else 0,
                datetime.now(timezone.utc)
            ))
            conn.commit()
    
    def get_bot_configs(self) -> List[Dict]:
        """Ottieni configurazioni bot salvate"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bot_configurations 
                ORDER BY updated_at DESC
            ''')
            
            configs = []
            for row in cursor.fetchall():
                config = dict(row)
                config['config_data'] = json.loads(config['config_data'])
                configs.append(config)
            
            return configs
    
    def export_data(self, output_file: str, start_date: str = None, end_date: str = None):
        """Esporta dati in formato JSON"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'sessions': [],
                'trades': [],
                'events': []
            }
            
            # Esporta sessioni
            sessions_query = "SELECT * FROM trading_sessions"
            if start_date:
                sessions_query += f" WHERE start_time >= '{start_date}'"
            cursor.execute(sessions_query)
            export_data['sessions'] = [dict(row) for row in cursor.fetchall()]
            
            # Esporta trades
            trades_query = "SELECT * FROM trades"
            if start_date:
                trades_query += f" WHERE entry_time >= '{start_date}'"
            cursor.execute(trades_query)
            export_data['trades'] = [dict(row) for row in cursor.fetchall()]
            
            # Esporta eventi
            events_query = "SELECT * FROM system_events"
            if start_date:
                events_query += f" WHERE timestamp >= '{start_date}'"
            cursor.execute(events_query)
            export_data['events'] = [dict(row) for row in cursor.fetchall()]
            
            # Salva file
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Dati esportati in {output_file}")
    
    def cleanup_old_data(self, days: int = 90):
        """Pulisce dati vecchi"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Elimina analisi di mercato vecchie
            cursor.execute('''
                DELETE FROM market_analysis 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            # Elimina eventi vecchi
            cursor.execute('''
                DELETE FROM system_events 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            conn.commit()
            self.logger.info(f"Dati più vecchi di {days} giorni rimossi")


# Script di test/debug
if __name__ == "__main__":
    # Crea istanza database
    db = TradingDatabase()
    
    # Debug contenuto database
    db.debug_database_content()
    
    # Verifica integrità
    db.verify_data_integrity()
    
    # Correggi problemi
    db.fix_database_issues()

# Istanza globale del database
trading_db = TradingDatabase()