#!/usr/bin/env python3
"""
Trading Bot Frontend Launcher
Avvia il dashboard web per monitorare e controllare il trading bot
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Controlla se le dipendenze sono installate"""
    try:
        import flask
        import flask_socketio
        print("✅ Dipendenze Flask trovate")
        return True
    except ImportError:
        print("❌ Dipendenze mancanti!")
        print("📦 Installazione dipendenze in corso...")
        
        # Installa le dipendenze
        frontend_dir = Path(__file__).parent
        requirements_file = frontend_dir / "requirements.txt"
        
        if requirements_file.exists():
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ])
                print("✅ Dipendenze installate con successo!")
                return True
            except subprocess.CalledProcessError:
                print("❌ Errore nell'installazione delle dipendenze")
                return False
        else:
            print("❌ File requirements.txt non trovato")
            return False

def check_config():
    """Controlla se il file di configurazione esiste"""
    config_file = Path(__file__).parent.parent / ".env"
    
    if not config_file.exists():
        print("⚠️  File .env non trovato!")
        print("📝 Creazione file .env di esempio...")
        
        env_content = """# API Bybit
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here

# Configurazione Telegram
TELEGRAM_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_telegram_chat_id_here

# Configurazione Browser (opzionale)
CHROME_DRIVER_PATH=path_to_chromedriver
CHROME_BINARY_PATH=path_to_chrome_binary
"""
        
        with open(config_file, 'w') as f:
            f.write(env_content)
        
        print(f"📄 File .env creato in: {config_file}")
        print("🔧 Modifica il file .env con le tue credenziali API prima di continuare")
        
        input("Premi Enter quando hai configurato il file .env...")
    
    return True

def start_dashboard():
    """Avvia il dashboard"""
    print("🚀 Avvio Trading Bot Dashboard...")
    print("=" * 50)
    print("📊 Dashboard: http://localhost:5000")
    print("🤖 Controllo Bot: http://localhost:5000/control")
    print("🧪 Test API: http://localhost:5000/api-test")
    print("⚙️  Impostazioni: http://localhost:5000/settings")
    print("=" * 50)
    print("💡 Tip: Usa Ctrl+C per fermare il server")
    print()
    
    # Avvia il browser dopo 2 secondi
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open('http://localhost:5000')
        except:
            pass
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Avvia l'app Flask
    try:
        from app import socketio, app
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Dashboard chiuso dall'utente")
    except Exception as e:
        print(f"❌ Errore nell'avvio del dashboard: {e}")
        print("🔧 Controlla la configurazione e riprova")

def main():
    """Funzione principale"""
    print("🤖 Trading Bot Dashboard")
    print("=" * 30)
    
    # Cambia directory al frontend
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)
    
    # Controlla requisiti
    if not check_requirements():
        print("❌ Impossibile avviare il dashboard")
        input("Premi Enter per uscire...")
        return
    
    # Controlla configurazione
    if not check_config():
        print("❌ Errore nella configurazione")
        input("Premi Enter per uscire...")
        return
    
    # Avvia dashboard
    start_dashboard()

if __name__ == "__main__":
    main()
