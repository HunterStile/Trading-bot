#!/usr/bin/env python3
"""
Setup iniziale per il sistema di storico trading
Inizializza il database e verifica che tutto funzioni correttamente
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Aggiungi percorsi necessari
frontend_dir = Path(__file__).parent
bot_dir = frontend_dir.parent
sys.path.append(str(bot_dir))
sys.path.append(str(frontend_dir))

def main():
    """Setup iniziale del sistema"""
    print("🔧 Setup Trading Bot con Sistema di Storico")
    print("=" * 50)
    
    try:
        # Test import database
        print("📊 Inizializzazione database...")
        from utils.database import trading_db
        print("✅ Database SQLite inizializzato")
        
        # Test import wrapper
        print("🔄 Inizializzazione wrapper trading...")
        from utils.trading_wrapper import trading_wrapper
        print("✅ Wrapper trading inizializzato")
        
        # Crea cartelle necessarie
        print("📁 Creazione cartelle...")
        exports_dir = frontend_dir / "exports"
        exports_dir.mkdir(exist_ok=True)
        print(f"✅ Cartella exports: {exports_dir}")
        
        # Verifica database
        print("🔍 Verifica struttura database...")
        stats = trading_db.get_performance_stats(30)
        print(f"✅ Database funzionante - Trade totali: {stats['total_trades']}")
        
        # Test salvataggio configurazione
        print("💾 Test salvataggio configurazione...")
        test_config = {
            'symbol': 'AVAXUSDT',
            'ema_period': 10,
            'test_mode': True
        }
        trading_db.save_bot_config('Test Setup', test_config)
        print("✅ Configurazione salvata")
        
        # Log evento di setup
        trading_db.log_event(
            "SYSTEM_SETUP",
            "SYSTEM",
            "Sistema di storico trading inizializzato con successo",
            {
                'setup_time': datetime.now().isoformat(),
                'version': '1.0.0'
            }
        )
        
        print("\n" + "=" * 50)
        print("🎉 Setup completato con successo!")
        print("\n📋 Riepilogo:")
        print(f"  • Database: {bot_dir / 'trading_data.db'}")
        print(f"  • Frontend: {frontend_dir}")
        print(f"  • Exports: {exports_dir}")
        print("\n🚀 Ora puoi avviare il dashboard con:")
        print(f"  python {frontend_dir / 'start_dashboard.py'}")
        print("\n📖 Funzionalità disponibili:")
        print("  • Dashboard con metriche in tempo reale")
        print("  • Storico completo di sessioni e trade")
        print("  • Analisi performance e grafici")
        print("  • Export dati in formato JSON")
        print("  • Sistema di eventi e log")
        print("  • Salvataggio configurazioni bot")
        
        return True
        
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        print("🔧 Assicurati di aver installato le dipendenze:")
        print("   pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Errore durante setup: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n💡 Suggerimenti per risolvere problemi:")
        print("1. Verifica che tutte le dipendenze siano installate")
        print("2. Controlla che il file .env sia configurato correttamente")
        print("3. Assicurati di essere nella cartella corretta")
        
        input("\nPremi Enter per uscire...")
        sys.exit(1)
    else:
        input("\nPremi Enter per continuare...")
