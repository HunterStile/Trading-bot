from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import sys
import os
import logging
import threading
import time
import requests

# Aggiungi il percorso del trading bot al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import del database e wrapper
from utils.database import trading_db
from utils.trading_wrapper import trading_wrapper

# Import sistema avanzato di crash recovery
try:
    from utils.simple_bot_state import EnhancedBotState
    from utils.crash_recovery import create_crash_recovery_system
    
    # Inizializza enhanced state manager
    bot_state_manager = EnhancedBotState()
    print("✅ Enhanced Bot State Manager inizializzato")
except ImportError as e:
    print(f"⚠️ Enhanced State Manager non disponibile: {e}")
    bot_state_manager = None

# Import delle funzioni del trading bot
try:
    from config import api, api_sec, TELEGRAM_TOKEN, CHAT_ID
    from trading_functions import (
        mostra_saldo, vedi_prezzo_moneta, get_kline_data, 
        analizza_prezzo_sopra_media, controlla_candele_sopra_ema,
        controlla_candele_sotto_ema, bot_open_position, bot_trailing_stop,
        media_esponenziale
    )
except ImportError as e:
    print(f"Errore nell'importazione delle funzioni del trading bot: {e}")

# Import dei blueprints
from routes import register_blueprints
from routes.websocket import register_websocket_events

# Import sistema notifiche Telegram
from utils.telegram_notifier import init_telegram_notifier

# Inizializza Flask e SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading_bot_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Registra i blueprints
register_blueprints(app)

# Route per servire i grafici di backtest
@app.route('/static/charts/<filename>')
def serve_chart(filename):
    """Serve i grafici di backtest dalla directory backtest_charts"""
    import os
    charts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backtest_charts')
    return send_from_directory(charts_dir, filename)

# Registra eventi WebSocket
register_websocket_events(socketio, trading_wrapper, trading_db)

# Variabili globali condivise
bot_status = {
    'running': False,
    'symbol': 'AVAXUSDT',
    'quantity': 50,
    'operation': True,  # True = Long, False = Short
    'ema_period': 10,
    'interval': 30,
    'open_candles': 3,
    'stop_candles': 3,
    'distance': 1,
    'category': 'linear',
    'last_update': None,
    'current_session_id': None,
    'session_start_time': None,
    'total_trades': 0,
    'session_pnl': 0
}

# Condividi le variabili globali con i blueprints
app.config.update({
    'BOT_STATUS': bot_status,
    'TRADING_WRAPPER': trading_wrapper,
    'TRADING_DB': trading_db,
    'BOT_STATE_MANAGER': bot_state_manager,
    'SOCKETIO': socketio
})

# Inizializza sistema notifiche Telegram
telegram_bot_instance = None
if TELEGRAM_TOKEN and CHAT_ID:
    telegram_notifier = init_telegram_notifier(TELEGRAM_TOKEN, CHAT_ID, "http://localhost:5000")
    app.config['TELEGRAM_NOTIFIER'] = telegram_notifier
    print("✅ Sistema notifiche Telegram inizializzato")
    
    # Inizializza bot Telegram interattivo
    try:
        from utils.telegram_bot import TradingBotTelegram
        telegram_bot_instance = TradingBotTelegram(
            token=TELEGRAM_TOKEN,
            dashboard_url="http://localhost:5000"
        )
        # Avvia il bot in thread separato
        import threading
        bot_thread = threading.Thread(target=telegram_bot_instance.start_bot, daemon=True)
        bot_thread.start()
        app.config['TELEGRAM_BOT'] = telegram_bot_instance
        print("✅ Bot Telegram interattivo avviato")
    except Exception as e:
        print(f"⚠️ Errore avvio bot Telegram interattivo: {e}")
        app.config['TELEGRAM_BOT'] = None
else:
    print("⚠️ Notifiche Telegram disabilitate (token/chat_id mancanti)")
    app.config['TELEGRAM_NOTIFIER'] = None
    app.config['TELEGRAM_BOT'] = None

if __name__ == '__main__':
    print("🚀 Avvio Trading Bot Dashboard...")
    
    # Controlla se il bot dovrebbe riavviarsi automaticamente
    if bot_state_manager:
        print("🔄 Controllo stato precedente...")
        
        if bot_state_manager.should_auto_restart():
            recovery_config = bot_state_manager.get_recovery_config()
            
            if recovery_config:
                print(f"✅ Bot era in esecuzione prima del crash - configurazione trovata:")
                print(f"   Simbolo: {recovery_config['symbol']}")
                print(f"   Quantità: {recovery_config['quantity']}")
                print(f"   Operazione: {'LONG' if recovery_config['operation'] else 'SHORT'}")
                print(f"   Trades precedenti: {recovery_config['previous_trades']}")
                
                # Aggiorna bot_status con la configurazione precedente
                bot_status.update({
                    'symbol': recovery_config['symbol'],
                    'quantity': recovery_config['quantity'],
                    'operation': recovery_config['operation'],
                    'ema_period': recovery_config['ema_period'],
                    'interval': recovery_config['interval'],
                    'open_candles': recovery_config['open_candles'],
                    'stop_candles': recovery_config['stop_candles'],
                    'distance': recovery_config['distance'],
                    'category': recovery_config['category']
                })
                
                # Programma auto-restart dopo che il server è avviato
                def auto_restart_bot():
                    time.sleep(5)  # Aspetta che il server sia completamente avviato
                    
                    try:
                        print("🔄 Tentativo auto-restart del bot...")
                        
                        response = requests.post(
                            'http://localhost:5000/api/bot/start',
                            json={
                                'symbol': recovery_config['symbol'],
                                'quantity': recovery_config['quantity'],
                                'operation': 'true' if recovery_config['operation'] else 'false',
                                'ema_period': recovery_config['ema_period'],
                                'interval': recovery_config['interval'],
                                'open_candles': recovery_config['open_candles'],
                                'stop_candles': recovery_config['stop_candles'],
                                'distance': recovery_config['distance']
                            },
                            timeout=15
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('success'):
                                print(f"✅ Bot riavviato automaticamente: {recovery_config['symbol']}")
                            else:
                                print(f"❌ Errore nel riavvio: {result.get('error')}")
                        else:
                            print(f"❌ Errore HTTP nel riavvio: {response.status_code}")
                            
                    except Exception as e:
                        print(f"❌ Errore nell'auto-restart: {e}")
                
                # Avvia auto-restart in thread separato
                restart_thread = threading.Thread(target=auto_restart_bot, daemon=True)
                restart_thread.start()
        else:
            print("ℹ️ Nessun auto-restart necessario")
    
    print("📊 Dashboard disponibile su: http://localhost:5000")
    print("🔧 Controllo Bot: http://localhost:5000/control")
    print("🧪 Test API: http://localhost:5000/api-test")
    
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server fermato dall'utente")
        # Salva che il bot è stato fermato manualmente
        if bot_state_manager:
            bot_state_manager.save_bot_stopped_state()
    except Exception as e:
        print(f"❌ Errore nell'avvio del servDr: {e}")
        # Non salviamo nulla in caso di errore di startup