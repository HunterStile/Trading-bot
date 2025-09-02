#!/usr/bin/env python3
"""
Script per ottenere il Chat ID di un gruppo Telegram
Utilizzalo per configurare le notifiche del trading bot in un gruppo
"""

import requests
import json

def get_telegram_group_chat_id():
    """
    Script per ottenere il Chat ID di un gruppo Telegram
    """
    
    # Inserisci qui il token del tuo bot
    BOT_TOKEN = input("Inserisci il token del tuo bot Telegram: ").strip()
    
    if not BOT_TOKEN:
        print("❌ Token del bot è richiesto!")
        return
    
    try:
        # Ottieni gli aggiornamenti dal bot
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Errore API Telegram: {data.get('description', 'Errore sconosciuto')}")
            return
        
        print("\n📱 ISTRUZIONI:")
        print("1. Aggiungi il bot al gruppo")
        print("2. Scrivi un messaggio nel gruppo (es: /start)")
        print("3. Esegui di nuovo questo script")
        print("\n" + "="*50)
        
        if not data.get('result'):
            print("⚠️  Nessun messaggio trovato.")
            print("   Assicurati di aver scritto almeno un messaggio nel gruppo dopo aver aggiunto il bot.")
            return
        
        print("\n🔍 Chat trovate:")
        print("-" * 50)
        
        found_groups = []
        
        for update in data['result']:
            if 'message' in update:
                message = update['message']
                chat = message['chat']
                chat_id = chat['id']
                chat_type = chat['type']
                
                if chat_type in ['group', 'supergroup']:
                    chat_title = chat.get('title', 'Gruppo senza nome')
                    
                    print(f"📊 Gruppo: {chat_title}")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   Tipo: {chat_type}")
                    
                    if 'from' in message:
                        user = message['from']
                        print(f"   Ultimo messaggio da: {user.get('first_name', '')} {user.get('last_name', '')}")
                    
                    print(f"   Data: {message.get('date', 'N/A')}")
                    print("-" * 30)
                    
                    found_groups.append({
                        'title': chat_title,
                        'chat_id': chat_id,
                        'type': chat_type
                    })
                
                elif chat_type == 'private':
                    user = message['from']
                    print(f"👤 Chat privata: {user.get('first_name', '')} {user.get('last_name', '')}")
                    print(f"   Chat ID: {chat_id}")
                    print("-" * 30)
        
        if found_groups:
            print(f"\n✅ Trovati {len(found_groups)} gruppi!")
            print("\n📝 Per configurare il trading bot:")
            print("1. Copia il Chat ID del gruppo che vuoi usare")
            print("2. Aggiornalo nel file .env:")
            print("   TELEGRAM_CHAT_ID=il_chat_id_del_gruppo")
            print("\n🔧 Esempio configurazione .env:")
            print("TELEGRAM_TOKEN=your_bot_token")
            print(f"TELEGRAM_CHAT_ID={found_groups[0]['chat_id']}")
        else:
            print("⚠️  Nessun gruppo trovato.")
            print("   Aggiungi il bot a un gruppo e scrivi un messaggio.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore di connessione: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    print("🤖 Telegram Group Chat ID Finder")
    print("="*40)
    get_telegram_group_chat_id()
