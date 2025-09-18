#!/usr/bin/env python3
"""
Test rapido per verificare che il bot sia configurato correttamente
"""

import sys
import os

def test_imports():
    """Testa gli import principali"""
    print("🔧 Test import moduli...")
    
    try:
        import requests
        print("✅ requests")
    except ImportError:
        print("❌ requests mancante")
        return False
    
    try:
        import flask
        print("✅ flask")
    except ImportError:
        print("❌ flask mancante")
        return False
    
    try:
        import pybit
        print("✅ pybit")
    except ImportError:
        print("❌ pybit mancante")
        return False
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError:
        print("❌ pandas mancante")
        return False
    
    # Test opzionali
    try:
        import selenium
        print("✅ selenium (opzionale)")
    except ImportError:
        print("⚠️ selenium non installato (funzioni scraping disabilitate)")
    
    return True

def test_env_file():
    """Testa file .env"""
    print("\n🔧 Test file .env...")
    
    if not os.path.exists('.env'):
        print("❌ File .env mancante!")
        print("   Copia .env.example come .env e configura le chiavi API")
        return False
    
    print("✅ File .env trovato")
    
    # Leggi variabili
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # Check variabili essenziali
    required_vars = ['BYBIT_API_KEY', 'BYBIT_API_SECRET', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    
    for var in required_vars:
        if var in env_vars and env_vars[var] and env_vars[var] != '':
            print(f"✅ {var}")
        else:
            print(f"❌ {var} mancante o vuoto")
            return False
    
    return True

def test_api_connection():
    """Testa connessione API Bybit"""
    print("\n🔧 Test connessione API Bybit...")
    
    try:
        # Carica variabili ambiente
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        
        if not api_key or not api_secret:
            print("❌ Chiavi API mancanti nel file .env")
            return False
        
        from pybit.unified_trading import HTTP
        session = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
        )
        
        # Test semplice
        result = session.get_server_time()
        
        if result and 'retCode' in result and result['retCode'] == 0:
            print("✅ Connessione API Bybit funzionante")
            return True
        else:
            print(f"❌ Errore API: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Errore connessione API: {e}")
        return False

def test_telegram():
    """Testa bot Telegram"""
    print("\n🔧 Test bot Telegram...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            print("❌ Token/Chat ID Telegram mancanti")
            return False
        
        import requests
        
        # Test semplice
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Bot Telegram funzionante: @{data['result']['username']}")
                return True
        
        print(f"❌ Errore bot Telegram: {response.text}")
        return False
        
    except Exception as e:
        print(f"❌ Errore test Telegram: {e}")
        return False

def main():
    """Test principale"""
    print("🚀 TEST CONFIGURAZIONE TRADING BOT")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Import
    if test_imports():
        tests_passed += 1
    
    # Test 2: File .env
    if test_env_file():
        tests_passed += 1
    
    # Test 3: API Bybit
    if test_api_connection():
        tests_passed += 1
    
    # Test 4: Telegram
    if test_telegram():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RISULTATI: {tests_passed}/{total_tests} test superati")
    
    if tests_passed == total_tests:
        print("🎉 CONFIGURAZIONE COMPLETA! Il bot è pronto per l'uso.")
        return 0
    elif tests_passed >= 2:
        print("⚠️ CONFIGURAZIONE PARZIALE. Il bot funzionerà con limitazioni.")
        return 0
    else:
        print("❌ CONFIGURAZIONE INCOMPLETA. Risolvi gli errori prima di continuare.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
