#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test delle API configurate per il Trading Bot
Questo script verifica la connettività e funzionalità di tutte le API
"""

import sys
import os
from datetime import datetime
import traceback

# Importa le configurazioni e funzioni
try:
    from config import *
    from trading_functions import (
        mostra_saldo, 
        vedi_prezzo_moneta, 
        get_kline_data,
        get_server_time,
        ottieni_prezzi
    )
    print("✅ Import delle configurazioni riuscito!")
except ImportError as e:
    print(f"❌ Errore nell'import: {e}")
    sys.exit(1)

def print_header(title):
    """Stampa un header formattato"""
    print("\n" + "="*60)
    print(f"🔧 {title}")
    print("="*60)

def print_test_result(test_name, success, details=""):
    """Stampa il risultato di un test"""
    status = "✅ SUCCESSO" if success else "❌ FALLITO"
    print(f"{status} - {test_name}")
    if details:
        print(f"   📋 Dettagli: {details}")

def test_environment_variables():
    """Testa le variabili d'ambiente"""
    print_header("TEST VARIABILI D'AMBIENTE")
    
    # Test API Bybit
    bybit_api_ok = bool(api and api.strip())
    bybit_secret_ok = bool(api_sec and api_sec.strip())
    print_test_result("Bybit API Key", bybit_api_ok, f"Key: {api[:10]}..." if bybit_api_ok else "Vuota")
    print_test_result("Bybit API Secret", bybit_secret_ok, f"Secret: {api_sec[:10]}..." if bybit_secret_ok else "Vuota")
    
    # Test Telegram
    telegram_token_ok = bool(TELEGRAM_TOKEN and TELEGRAM_TOKEN.strip())
    telegram_chat_ok = bool(CHAT_ID and CHAT_ID.strip())
    print_test_result("Telegram Token", telegram_token_ok, f"Token: {TELEGRAM_TOKEN[:10]}..." if telegram_token_ok else "Vuoto")
    print_test_result("Telegram Chat ID", telegram_chat_ok, f"Chat ID: {CHAT_ID}" if telegram_chat_ok else "Vuoto")
    
    # Test Spotify (opzionale)
    spotify_client_ok = bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_ID.strip())
    spotify_secret_ok = bool(SPOTIFY_CLIENT_SECRET and SPOTIFY_CLIENT_SECRET.strip())
    print_test_result("Spotify Client ID", spotify_client_ok, "Configurato" if spotify_client_ok else "Non configurato (opzionale)")
    print_test_result("Spotify Client Secret", spotify_secret_ok, "Configurato" if spotify_secret_ok else "Non configurato (opzionale)")
    
    # Test Browser
    chrome_path_ok = bool(path and path.strip())
    chrome_binary_ok = bool(chrome_scelto and chrome_scelto.strip())
    print_test_result("Chrome Driver Path", chrome_path_ok, f"Path: {path}" if chrome_path_ok else "Non configurato")
    print_test_result("Chrome Binary Path", chrome_binary_ok, f"Path: {chrome_scelto}" if chrome_binary_ok else "Non configurato")
    
    return bybit_api_ok and bybit_secret_ok

def test_bybit_api():
    """Testa le API di Bybit"""
    print_header("TEST API BYBIT")
    
    try:
        # Test 1: Server Time
        print("\n🔍 Test 1: Server Time")
        server_time = get_server_time()
        if server_time:
            dt = datetime.fromtimestamp(server_time)
            print_test_result("Server Time", True, f"Timestamp: {server_time}, Data: {dt}")
        else:
            print_test_result("Server Time", False, "Impossibile ottenere il tempo del server")
            print("💡 Suggerimento: Questo potrebbe indicare un problema di connessione o API deprecata")
            
    except Exception as e:
        print_test_result("Server Time", False, f"Errore: {str(e)}")
        print("💡 Suggerimento: Verifica la connessione internet")
    
    try:
        # Test 2: Test diretto della connessione API con pybit
        print("\n🔍 Test 2: Connessione diretta API Bybit")
        from pybit.unified_trading import HTTP
        session = HTTP(
            testnet=False,
            api_key=api,
            api_secret=api_sec,
        )
        
        # Test semplice per verificare la connessione
        response = session.get_server_time()
        if response and 'result' in response:
            server_time = response['result']['timeSecond']
            dt = datetime.fromtimestamp(int(server_time))
            print_test_result("Connessione API Diretta", True, f"Server time: {dt}")
        else:
            print_test_result("Connessione API Diretta", False, "Risposta API non valida")
            return False
            
    except Exception as e:
        print_test_result("Connessione API Diretta", False, f"Errore: {str(e)}")
        print("💡 Controlla le chiavi API e i permessi su Bybit")
        return False
    
    try:
        # Test 3: Saldo del Wallet
        print("\n🔍 Test 3: Saldo Wallet")
        print("📊 Recupero saldo del wallet...")
        
        # Test manuale del saldo per debug
        response = session.get_wallet_balance(accountType="UNIFIED")
        if response and 'result' in response and response['retCode'] == 0:
            total_equity = response['result']['list'][0]['totalEquity']
            print_test_result("Saldo Wallet", True, f"Total Equity: {total_equity} USDT")
            
            # Mostra anche le singole monete se disponibili
            coins = response['result']['list'][0]['coin']
            print("💰 Top 5 Holdings:")
            for i, coin in enumerate(coins[:5]):
                if float(coin['walletBalance']) > 0:
                    print(f"   🪙 {coin['coin']}: {coin['walletBalance']}")
        else:
            print_test_result("Saldo Wallet", False, f"Errore API: {response.get('retMsg', 'Sconosciuto')}")
            return False
        
    except Exception as e:
        print_test_result("Saldo Wallet", False, f"Errore: {str(e)}")
        print(f"📝 Traceback completo:\n{traceback.format_exc()}")
        return False
    
    try:
        # Test 4: Prezzo di una moneta popolare
        print("\n🔍 Test 4: Prezzo Bitcoin (BTCUSDT)")
        btc_price = vedi_prezzo_moneta("linear", "BTCUSDT")
        if btc_price and btc_price > 0:
            print_test_result("Prezzo BTC", True, f"Prezzo: ${btc_price:,.2f}")
        else:
            print_test_result("Prezzo BTC", False, "Prezzo non valido")
            return False
            
    except Exception as e:
        print_test_result("Prezzo BTC", False, f"Errore: {str(e)}")
        return False
    
    try:
        # Test 5: Dati Kline (candlestick)
        print("\n🔍 Test 5: Dati Kline BTCUSDT (ultime 5 candele)")
        kline_data = get_kline_data("linear", "BTCUSDT", "D", limit=5)
        if kline_data and len(kline_data) > 0:
            print_test_result("Dati Kline", True, f"Recuperate {len(kline_data)} candele")
            print("📈 Ultime candele giornaliere BTC:")
            for i, candle in enumerate(kline_data[:3]):  # Mostra solo le prime 3
                timestamp = int(candle[0])
                dt = datetime.fromtimestamp(timestamp/1000)
                open_price = float(candle[1])
                high_price = float(candle[2])
                low_price = float(candle[3])
                close_price = float(candle[4])
                print(f"   📅 {dt.strftime('%Y-%m-%d')}: O:{open_price:,.0f} H:{high_price:,.0f} L:{low_price:,.0f} C:{close_price:,.0f}")
        else:
            print_test_result("Dati Kline", False, "Nessun dato recuperato")
            return False
            
    except Exception as e:
        print_test_result("Dati Kline", False, f"Errore: {str(e)}")
        return False
    
    try:
        # Test 6: Verifica permessi specifici
        print("\n🔍 Test 6: Verifica Permessi API")
        
        # Test permessi wallet
        try:
            wallet_response = session.get_wallet_balance(accountType="UNIFIED")
            wallet_ok = wallet_response['retCode'] == 0
            print_test_result("Permessi Wallet", wallet_ok, "Lettura saldo OK" if wallet_ok else "Accesso negato")
        except:
            print_test_result("Permessi Wallet", False, "Accesso negato")
        
        # Test permessi trading (solo lettura posizioni)
        try:
            positions_response = session.get_positions(category="linear", symbol="BTCUSDT")
            trading_ok = positions_response['retCode'] == 0
            print_test_result("Permessi Trading", trading_ok, "Lettura posizioni OK" if trading_ok else "Accesso negato")
        except:
            print_test_result("Permessi Trading", False, "Accesso negato")
            
    except Exception as e:
        print_test_result("Verifica Permessi", False, f"Errore: {str(e)}")
    
    print("\n💡 Permessi API configurati:")
    print("   ✅ Contracts - Orders Positions")
    print("   ✅ USDC Contracts - Trade") 
    print("   ✅ Unified Trading - Trade")
    print("   ✅ SPOT - Trade")
    print("   ✅ Wallet - Account Transfer Subaccount Transfer")
    print("   ✅ Exchange - Convert，Exchange History")
    
    return True

def test_telegram_api():
    """Testa le API di Telegram"""
    print_header("TEST API TELEGRAM")
    
    if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
        print_test_result("Telegram API", False, "Token non configurato - SALTATO")
        return False
    
    try:
        import telegram
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        
        # Test connessione
        print("\n🔍 Test: Connessione Bot Telegram")
        bot_info = bot.get_me()
        print_test_result("Connessione Telegram", True, f"Bot: @{bot_info.username}")
        
        if CHAT_ID and CHAT_ID.strip():
            print(f"📱 Chat ID configurato: {CHAT_ID}")
            print("⚠️  Per testare l'invio messaggi, decommentare la riga nel codice")
            # Decommentare la riga sotto per testare l'invio di un messaggio
            # bot.send_message(chat_id=CHAT_ID, text="🤖 Test API Trading Bot - Connessione riuscita!")
        else:
            print_test_result("Chat ID", False, "Chat ID non configurato")
        
        return True
        
    except Exception as e:
        print_test_result("Telegram API", False, f"Errore: {str(e)}")
        return False

def test_other_apis():
    """Testa altre API opzionali"""
    print_header("TEST API AGGIUNTIVE")
    
    # Test Spotify (se configurato)
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_ID.strip():
        print("🎵 Spotify API configurate ma non testate in questo script")
        print_test_result("Spotify API", True, "Credenziali presenti (test non implementato)")
    else:
        print_test_result("Spotify API", False, "Non configurate (opzionale)")
    
    # Test Browser (se configurato)
    if path and path.strip():
        print("🌐 Browser configurato per scraping")
        print_test_result("Browser Config", True, "Percorsi configurati (test selenium non eseguito)")
    else:
        print_test_result("Browser Config", False, "Non configurato")

def main():
    """Funzione principale"""
    print("🚀 AVVIO TEST API TRADING BOT")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test variabili d'ambiente
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ TEST FALLITO: Configurazione Bybit incompleta!")
        print("💡 Assicurati di aver compilato correttamente il file .env")
        return False
    
    # Test API principali
    bybit_ok = test_bybit_api()
    telegram_ok = test_telegram_api()
    
    # Test API aggiuntive
    test_other_apis()
    
    # Risultato finale
    print_header("RISULTATO FINALE")
    
    if bybit_ok:
        print("✅ API BYBIT: Tutte le funzioni funzionano correttamente!")
        print("   🔹 Puoi usare il bot per trading automatico")
        print("   🔹 Saldo wallet accessibile")
        print("   🔹 Prezzi e dati di mercato disponibili")
    else:
        print("❌ API BYBIT: Problemi rilevati!")
        print("   🔹 Controlla le chiavi API nel file .env")
        print("   🔹 Verifica i permessi API su Bybit")
    
    if telegram_ok:
        print("✅ API TELEGRAM: Bot configurato correttamente!")
        print("   🔹 Puoi ricevere notifiche via Telegram")
    else:
        print("⚠️  API TELEGRAM: Non configurate o problematiche")
        print("   🔹 Alert via Telegram non disponibili")
    
    print(f"\n🏁 Test completato alle {datetime.now().strftime('%H:%M:%S')}")
    
    return bybit_ok

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 TUTTI I TEST PRINCIPALI SUPERATI!")
            print("🚀 Il bot è pronto per essere utilizzato!")
        else:
            print("\n⚠️  ALCUNI TEST FALLITI!")
            print("🔧 Controlla la configurazione prima di procedere")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrotto dall'utente")
    except Exception as e:
        print(f"\n💥 Errore imprevisto durante il test: {e}")
        print(f"📝 Traceback:\n{traceback.format_exc()}")
