#!/usr/bin/env python3
"""
Script per aggiornare lo schema del database con le nuove colonne e tabelle
per la gestione migliorata degli ID Bybit
"""

import sqlite3
from pathlib import Path

def update_database_schema():
    """Aggiorna lo schema del database con le nuove funzionalità"""
    
    # Percorso del database
    db_path = Path(__file__).parent / "trading_data.db"
    
    print(f"🔧 Aggiornamento schema database: {db_path}")
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 1. Aggiungi colonne alla tabella trades se non esistono
            print("📝 Aggiornamento tabella trades...")
            
            # Controlla se le colonne esistono già
            cursor.execute("PRAGMA table_info(trades)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'bybit_order_id' not in columns:
                cursor.execute("ALTER TABLE trades ADD COLUMN bybit_order_id TEXT")
                print("   ✅ Aggiunta colonna bybit_order_id")
            else:
                print("   ✅ Colonna bybit_order_id già presente")
                
            if 'external_trade_id' not in columns:
                cursor.execute("ALTER TABLE trades ADD COLUMN external_trade_id TEXT")
                print("   ✅ Aggiunta colonna external_trade_id")
            else:
                print("   ✅ Colonna external_trade_id già presente")
            
            # 2. Crea tabella trade_id_mapping se non esiste
            print("📝 Creazione tabella trade_id_mapping...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_id_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    internal_trade_id TEXT NOT NULL,
                    external_trade_id TEXT NOT NULL,
                    bybit_order_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(external_trade_id),
                    FOREIGN KEY (internal_trade_id) REFERENCES trades (trade_id)
                )
            ''')
            print("   ✅ Tabella trade_id_mapping creata/verificata")
            
            # 3. Crea indici per performance
            print("📝 Creazione indici...")
            
            indices = [
                ("idx_trade_mapping_external", "CREATE INDEX IF NOT EXISTS idx_trade_mapping_external ON trade_id_mapping(external_trade_id)"),
                ("idx_trade_mapping_internal", "CREATE INDEX IF NOT EXISTS idx_trade_mapping_internal ON trade_id_mapping(internal_trade_id)"),
                ("idx_trades_symbol_side", "CREATE INDEX IF NOT EXISTS idx_trades_symbol_side ON trades(symbol, side, status)"),
                ("idx_trades_session", "CREATE INDEX IF NOT EXISTS idx_trades_session ON trades(session_id, status)")
            ]
            
            for idx_name, idx_sql in indices:
                cursor.execute(idx_sql)
                print(f"   ✅ Indice {idx_name} creato/verificato")
            
            conn.commit()
            print("✅ Aggiornamento schema completato con successo!")
            
            # 4. Verifica finale
            print("\n📊 Verifica schema aggiornato:")
            cursor.execute("PRAGMA table_info(trades)")
            trades_columns = cursor.fetchall()
            print(f"   Colonne tabella trades: {len(trades_columns)}")
            for col in trades_columns:
                print(f"     - {col[1]} ({col[2]})")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_id_mapping'")
            mapping_exists = cursor.fetchone()
            print(f"   Tabella trade_id_mapping: {'✅ Presente' if mapping_exists else '❌ Mancante'}")
            
    except Exception as e:
        print(f"❌ Errore durante aggiornamento schema: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("\n🎉 Database aggiornato correttamente!")
        print("📋 Il sistema ora supporta:")
        print("   - Mappatura ID Bybit <-> ID interni")
        print("   - Recupero posizioni migliorate")
        print("   - Tracking ordini Bybit")
    else:
        print("\n❌ Aggiornamento fallito - controllare i log")
