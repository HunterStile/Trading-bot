#!/usr/bin/env python3
"""
Script per ottenere il Chat ID di Telegram
Usa questo script dopo aver creato il bot e inviato almeno un messaggio
"""

import requests
import json

def get_chat_id():
    """Ottiene il Chat ID dal bot Telegram"""
    
    # Inserisci qui il token del tuo bot
    bot_token = input("Inserisci il token del bot Telegram: ").strip()
    
    if not bot_token:
        print("❌ Token non fornito!")
        return
    
    try:
        # Chiama l'API di Telegram
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Errore API: {data.get('description', 'Errore sconosciuto')}")
            return
        
        updates = data.get('result', [])
        
        if not updates:
            print("⚠️ Nessun messaggio trovato!")
            print("💡 Invia almeno un messaggio al bot e riprova")
            return
        
        # Estrae tutti i chat ID unici
        chat_ids = set()
        for update in updates:
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                chat_ids.add(chat_id)
                
                # Mostra info del messaggio
                chat_info = update['message']['chat']
                print(f"📱 Chat trovata:")
                print(f"   Chat ID: {chat_id}")
                print(f"   Tipo: {chat_info.get('type', 'N/A')}")
                if 'username' in chat_info:
                    print(f"   Username: @{chat_info['username']}")
                if 'first_name' in chat_info:
                    print(f"   Nome: {chat_info['first_name']}")
                print()
        
        if chat_ids:
            print("✅ Chat ID trovati:")
            for chat_id in chat_ids:
                print(f"   {chat_id}")
            
            print("\n📝 Aggiungi al file .env:")
            print(f"TELEGRAM_TOKEN={bot_token}")
            print(f"TELEGRAM_CHAT_ID={list(chat_ids)[0]}")
        
    except requests.RequestException as e:
        print(f"❌ Errore di rete: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    print("🔍 Script per ottenere Chat ID Telegram\n")
    print("📋 Passi preliminari:")
    print("1. Crea un bot con @BotFather")
    print("2. Ottieni il token del bot")
    print("3. Invia almeno un messaggio al bot")
    print("4. Esegui questo script\n")
    
    get_chat_id()
