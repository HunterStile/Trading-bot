#!/usr/bin/env python3
"""
Script per verificare la configurazione Telegram corrente
"""

import sys
import os
from pathlib import Path

# Aggiungi il path per gli import
script_dir = Path(__file__).parent
project_dir = script_dir
sys.path.insert(0, str(project_dir))

try:
    from config import TELEGRAM_TOKEN, CHAT_ID
    
    print("🔍 CONFIGURAZIONE TELEGRAM ATTUALE:")
    print("="*50)
    print(f"📱 Token Bot: {TELEGRAM_TOKEN[:10]}...{TELEGRAM_TOKEN[-5:] if TELEGRAM_TOKEN else 'NON CONFIGURATO'}")
    print(f"💬 Chat ID: {CHAT_ID}")
    
    if CHAT_ID:
        if str(CHAT_ID).startswith('-'):
            print("✅ Chat ID sembra essere un GRUPPO (inizia con -)")
        else:
            print("ℹ️ Chat ID sembra essere una CHAT PRIVATA (non inizia con -)")
    else:
        print("❌ Chat ID non configurato!")
    
    print("\n🧪 Test invio messaggio...")
    
    if TELEGRAM_TOKEN and CHAT_ID:
        # Test invio messaggio
        from utils.telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier(
            token=TELEGRAM_TOKEN,
            chat_id=CHAT_ID,
            dashboard_url="http://localhost:5000"
        )
        
        test_message = f"""
🔧 <b>Test Configurazione Telegram</b>

📊 Chat ID utilizzato: <code>{CHAT_ID}</code>
🤖 Bot Token: <code>{TELEGRAM_TOKEN[:15]}...</code>
⏰ Test eseguito: {os.popen('echo %date% %time%').read().strip()}

✅ Se ricevi questo messaggio, la configurazione è corretta!
"""
        
        success = notifier.send_message_sync(test_message)
        
        if success:
            print("✅ Messaggio di test inviato con successo!")
            if str(CHAT_ID).startswith('-'):
                print("📱 Il messaggio dovrebbe apparire nel GRUPPO")
            else:
                print("📱 Il messaggio dovrebbe apparire nella CHAT PRIVATA")
        else:
            print("❌ Errore nell'invio del messaggio di test")
    else:
        print("⚠️ Configurazione incompleta - impossibile testare")
        
except ImportError as e:
    print(f"❌ Errore import: {e}")
except Exception as e:
    print(f"❌ Errore: {e}")

print("\n" + "="*50)
