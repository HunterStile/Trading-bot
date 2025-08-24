#!/usr/bin/env python3
"""
Script di avvio dedicato per il bot Telegram Trading
Può essere eseguito separatamente dalla dashboard principale
"""

import sys
import os
from pathlib import Path

# Aggiungi il path corretto per gli import
script_dir = Path(__file__).parent
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir))

from config import TELEGRAM_TOKEN, CHAT_ID

def start_telegram_bot():
    """Avvia solo il bot Telegram"""
    
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ ERRORE: TELEGRAM_TOKEN e CHAT_ID devono essere configurati nel file .env")
        print("Crea un file .env nel root del progetto con:")
        print("TELEGRAM_TOKEN=your_bot_token_here")
        print("TELEGRAM_CHAT_ID=your_chat_id_here")
        return
    
    try:
        from utils.telegram_bot import TradingBotTelegram
        
        print("🤖 Avvio bot Telegram per Trading Dashboard...")
        print(f"📱 Chat ID configurato: {CHAT_ID}")
        
        # Crea istanza bot
        telegram_bot = TradingBotTelegram(
            token=TELEGRAM_TOKEN,
            dashboard_url="http://localhost:5000"
        )
        
        # Avvia bot (bloccante)
        print("✅ Bot Telegram avviato! Premi Ctrl+C per fermare.")
        telegram_bot.start_bot()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot Telegram fermato dall'utente")
    except Exception as e:
        print(f"❌ Errore avvio bot Telegram: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_telegram_bot()
