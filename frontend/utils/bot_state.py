#!/usr/bin/env python3
"""
Bot State Manager
Gestisce il salvataggio e recovery dello stato del bot
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class BotStateManager:
    """Gestisce lo stato persistente del bot"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "bot_state.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Inizializza il database dello stato"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    state_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    strategy_type TEXT NOT NULL,
                    strategy_params TEXT NOT NULL,
                    position_size REAL NOT NULL,
                    target_profit REAL,
                    stop_loss REAL,
                    trailing_stop REAL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trailing_stops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    current_stop_price REAL NOT NULL,
                    trail_amount REAL NOT NULL,
                    best_price REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            conn.commit()
    
    def save_bot_state(self, state_type: str, data: Dict[str, Any]):
        """Salva lo stato del bot"""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Disabilita stati precedenti dello stesso tipo
            conn.execute("""
                UPDATE bot_state 
                SET is_active = 0 
                WHERE state_type = ? AND is_active = 1
            """, (state_type,))
            
            # Inserisci nuovo stato
            conn.execute("""
                INSERT INTO bot_state (timestamp, state_type, data, is_active)
                VALUES (?, ?, ?, 1)
            """, (timestamp, state_type, json.dumps(data)))
            
            conn.commit()
    
    def get_bot_state(self, state_type: str) -> Optional[Dict[str, Any]]:
        """Recupera lo stato del bot"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT data FROM bot_state 
                WHERE state_type = ? AND is_active = 1 
                ORDER BY timestamp DESC LIMIT 1
            """, (state_type,))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
    
    def save_active_strategy(self, symbol: str, side: str, entry_price: float, 
                           strategy_type: str, strategy_params: Dict[str, Any],
                           position_size: float, **kwargs):
        """Salva una strategia attiva"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO active_strategies 
                (symbol, side, entry_price, entry_time, strategy_type, strategy_params,
                 position_size, target_profit, stop_loss, trailing_stop, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, side, entry_price, now, strategy_type, 
                json.dumps(strategy_params), position_size,
                kwargs.get('target_profit'), kwargs.get('stop_loss'), 
                kwargs.get('trailing_stop'), now, now
            ))
            conn.commit()
    
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Recupera tutte le strategie attive"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM active_strategies WHERE is_active = 1
            """)
            
            columns = [description[0] for description in cursor.description]
            strategies = []
            
            for row in cursor.fetchall():
                strategy = dict(zip(columns, row))
                strategy['strategy_params'] = json.loads(strategy['strategy_params'])
                strategies.append(strategy)
            
            return strategies
    
    def deactivate_strategy(self, symbol: str, side: str):
        """Disattiva una strategia"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE active_strategies 
                SET is_active = 0, updated_at = ?
                WHERE symbol = ? AND side = ? AND is_active = 1
            """, (datetime.now().isoformat(), symbol, side))
            conn.commit()
    
    def save_trailing_stop(self, symbol: str, side: str, stop_price: float, 
                          trail_amount: float, best_price: float):
        """Salva o aggiorna trailing stop"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Controlla se esiste già
            cursor = conn.execute("""
                SELECT id FROM trailing_stops 
                WHERE symbol = ? AND side = ? AND is_active = 1
            """, (symbol, side))
            
            if cursor.fetchone():
                # Aggiorna esistente
                conn.execute("""
                    UPDATE trailing_stops 
                    SET current_stop_price = ?, trail_amount = ?, 
                        best_price = ?, updated_at = ?
                    WHERE symbol = ? AND side = ? AND is_active = 1
                """, (stop_price, trail_amount, best_price, now, symbol, side))
            else:
                # Inserisci nuovo
                conn.execute("""
                    INSERT INTO trailing_stops 
                    (symbol, side, current_stop_price, trail_amount, best_price, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (symbol, side, stop_price, trail_amount, best_price, now, now))
            
            conn.commit()
    
    def get_trailing_stops(self) -> List[Dict[str, Any]]:
        """Recupera tutti i trailing stop attivi"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM trailing_stops WHERE is_active = 1
            """)
            
            columns = [description[0] for description in cursor.description]
            trailing_stops = []
            
            for row in cursor.fetchall():
                trailing_stop = dict(zip(columns, row))
                trailing_stops.append(trailing_stop)
            
            return trailing_stops
    
    def remove_trailing_stop(self, symbol: str, side: str):
        """Rimuove trailing stop"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE trailing_stops 
                SET is_active = 0, updated_at = ?
                WHERE symbol = ? AND side = ? AND is_active = 1
            """, (datetime.now().isoformat(), symbol, side))
            conn.commit()
    
    def cleanup_closed_positions(self, active_positions: List[Dict[str, Any]]):
        """Pulisci strategie per posizioni che non esistono più"""
        if not active_positions:
            # Se non ci sono posizioni attive, disattiva tutto
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE active_strategies 
                    SET is_active = 0, updated_at = ?
                    WHERE is_active = 1
                """, (now,))
                
                conn.execute("""
                    UPDATE trailing_stops 
                    SET is_active = 0, updated_at = ?
                    WHERE is_active = 1
                """, (now,))
                
                conn.commit()
            return
        
        # Crea set di posizioni attive
        active_keys = {(pos['symbol'], pos['side']) for pos in active_positions}
        
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().isoformat()
            
            # Disattiva strategie per posizioni chiuse
            cursor = conn.execute("""
                SELECT symbol, side FROM active_strategies WHERE is_active = 1
            """)
            
            for symbol, side in cursor.fetchall():
                if (symbol, side) not in active_keys:
                    conn.execute("""
                        UPDATE active_strategies 
                        SET is_active = 0, updated_at = ?
                        WHERE symbol = ? AND side = ? AND is_active = 1
                    """, (now, symbol, side))
            
            # Disattiva trailing stops per posizioni chiuse
            cursor = conn.execute("""
                SELECT symbol, side FROM trailing_stops WHERE is_active = 1
            """)
            
            for symbol, side in cursor.fetchall():
                if (symbol, side) not in active_keys:
                    conn.execute("""
                        UPDATE trailing_stops 
                        SET is_active = 0, updated_at = ?
                        WHERE symbol = ? AND side = ? AND is_active = 1
                    """, (now, symbol, side))
            
            conn.commit()
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """Ottieni summary per recovery"""
        strategies = self.get_active_strategies()
        trailing_stops = self.get_trailing_stops()
        bot_state = self.get_bot_state('main_config')
        
        return {
            'active_strategies_count': len(strategies),
            'active_strategies': strategies,
            'trailing_stops_count': len(trailing_stops),
            'trailing_stops': trailing_stops,
            'last_bot_config': bot_state,
            'needs_recovery': len(strategies) > 0 or len(trailing_stops) > 0
        }
