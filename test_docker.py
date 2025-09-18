#!/usr/bin/env python3
"""
Script rapido per testare se il Trading Bot funziona dopo il deploy Docker
"""

import requests
import sys
import time

def test_trading_bot():
    """Testa se il Trading Bot risponde correttamente"""
    print("🔍 Test Trading Bot Docker...")
    
    # Test connessione base
    try:
        response = requests.get("http://localhost:5000", timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard accessibile")
        else:
            print(f"⚠️ Dashboard risponde con codice: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard non raggiungibile: {e}")
        return False
    
    # Test health check se disponibile
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check OK")
        else:
            print(f"⚠️ Health check: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Health check non disponibile: {e}")
    
    # Test API test endpoint
    try:
        response = requests.get("http://localhost:5000/api-test", timeout=10)
        if response.status_code == 200:
            print("✅ API test endpoint raggiungibile")
        else:
            print(f"⚠️ API test endpoint: {response.status_code}")
    except Exception as e:
        print(f"⚠️ API test endpoint non disponibile: {e}")
    
    print("✅ Test completato!")
    return True

if __name__ == "__main__":
    # Aspetta un po' per permettere al container di avviarsi
    print("⏳ Attendendo avvio del Trading Bot...")
    time.sleep(5)
    
    success = test_trading_bot()
    sys.exit(0 if success else 1)
