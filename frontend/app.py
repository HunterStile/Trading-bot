from flask import Flask
from flask_socketio import SocketIO
import sys
import os
import logging

# Aggiungi il percorso del trading bot al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import del database e wrapper
from utils.database import trading_db
from utils.trading_wrapper import trading_wrapper

# Import sistema di recovery
try:
    from utils.bot_state import BotStateManager
    from utils.bot_recovery import BotRecoveryManager
    
    # Inizializza recovery system
    state_manager = BotStateManager()
    recovery_manager = BotRecoveryManager(trading_wrapper, state_manager)
    print("✅ Recovery system inizializzato")
except ImportError as e:
    print(f"⚠️ Recovery system non disponibile: {e}")
    state_manager = None
    recovery_manager = None

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

# Inizializza Flask e SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading_bot_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Registra i blueprints
register_blueprints(app)

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
    'STATE_MANAGER': state_manager,
    'RECOVERY_MANAGER': recovery_manager,
    'SOCKETIO': socketio
})

if __name__ == '__main__':
    print("🚀 Avvio Trading Bot Dashboard...")
    
    # Avvia recovery automatico se disponibile
    if recovery_manager:
        print("🔄 Controllo recovery automatico...")
        try:
            recovery_result = recovery_manager.perform_initial_recovery()
            
            if recovery_result.get('success'):
                recovered_strategies = recovery_result.get('recovered_strategies', [])
                recovered_trailing = recovery_result.get('recovered_trailing_stops', [])
                
                if recovered_strategies or recovered_trailing:
                    print(f"✅ Recovery completato: {len(recovered_strategies)} strategie, {len(recovered_trailing)} trailing stops")
                else:
                    print("ℹ️ Nessun recovery necessario")
            else:
                print(f"⚠️ Errore nel recovery: {recovery_result.get('error', 'Unknown')}")
        except Exception as e:
            print(f"⚠️ Errore durante recovery: {e}")
    
    print("📊 Dashboard disponibile su: http://localhost:5000")
    print("🔧 Controllo Bot: http://localhost:5000/control")
    print("🧪 Test API: http://localhost:5000/api-test")
    
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server fermato dall'utente")
        if recovery_manager:
            recovery_manager.stop_recovery_check()
    except Exception as e:
        print(f"❌ Errore nell'avvio del server: {e}")
        if recovery_manager:
            recovery_manager.stop_recovery_check()