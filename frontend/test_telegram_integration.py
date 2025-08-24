#!/usr/bin/env python3
"""
Test script per verificare l'integrazione Telegram
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Aggiungi il path per gli import
script_dir = Path(__file__).parent
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir))

def test_telegram_notifications():
    """Test delle notifiche Telegram"""
    
    print("🧪 Test delle notifiche Telegram...")
    
    try:
        from utils.telegram_notifier import TelegramNotifier
        from config import TELEGRAM_TOKEN, CHAT_ID
        
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print("⚠️ TELEGRAM_TOKEN e CHAT_ID non configurati")
            print("Configura nel file .env per testare le notifiche")
            return
        
        # Crea notifier con parametri corretti
        notifier = TelegramNotifier(
            token=TELEGRAM_TOKEN,
            chat_id=CHAT_ID,
            dashboard_url="http://localhost:5000"
        )
        
        print("✅ TelegramNotifier creato con successo")
        
        # Test notifica apertura posizione
        print("📱 Test notifica apertura posizione...")
        notifier.notify_position_opened({
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 45000.0,
            'quantity': 0.001,
            'timestamp': datetime.now().isoformat()
        })
        
        # Test notifica chiusura posizione  
        print("📱 Test notifica chiusura posizione...")
        notifier.notify_position_closed({
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'close_price': 46000.0,
            'timestamp': datetime.now().isoformat()
        }, pnl=1.0, reason="EMA_STOP")
        
        # Test notifica crash
        print("📱 Test notifica crash...")
        notifier.notify_crash_detected("Test crash simulation")
        
        # Test notifica recovery
        print("📱 Test notifica recovery...")
        notifier.notify_recovery_completed({
            'action_taken': 'CONTINUE_NORMAL',
            'positions_recovered': 1,
            'final_state': 'MANAGING_POSITIONS'
        })
        
        print("✅ Tutti i test completati!")
        
    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()

def test_telegram_bot():
    """Test del bot Telegram interattivo"""
    
    print("🤖 Test del bot Telegram interattivo...")
    
    try:
        from utils.telegram_bot import TradingBotTelegram
        from config import TELEGRAM_TOKEN, CHAT_ID
        
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print("⚠️ TELEGRAM_TOKEN e CHAT_ID non configurati")
            print("Configura nel file .env per testare il bot interattivo")
            return
        
        # Crea bot (senza chat_id nel costruttore)
        bot = TradingBotTelegram(
            token=TELEGRAM_TOKEN,
            dashboard_url="http://localhost:5000"
        )
        
        print("✅ TradingBotTelegram creato con successo")
        print("💡 Per testare completamente, avvia con: python start_telegram_bot.py")
        
    except Exception as e:
        print(f"❌ Errore test bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Test integrazione Telegram Trading Bot\n")
    
    test_telegram_notifications()
    print()
    test_telegram_bot()
    
    print("\n🎉 Test completati!")
    print("📖 Leggi TELEGRAM_BOT_README.md per la configurazione completa")
