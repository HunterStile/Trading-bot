from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import sys
import os
import threading
import time
import logging
from datetime import datetime, timedelta
import json

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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading_bot_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Coppie di trading default e personalizzate
DEFAULT_SYMBOLS = [
    {'symbol': 'AVAXUSDT', 'name': 'AVAX/USDT'},
    {'symbol': 'BTCUSDT', 'name': 'BTC/USDT'},
    {'symbol': 'ETHUSDT', 'name': 'ETH/USDT'},
    {'symbol': 'SOLUSDT', 'name': 'SOL/USDT'},
    {'symbol': 'ADAUSDT', 'name': 'ADA/USDT'},
    {'symbol': 'DOTUSDT', 'name': 'DOT/USDT'}
]

# File per salvare coppie personalizzate
CUSTOM_SYMBOLS_FILE = 'custom_symbols.json'

def load_custom_symbols():
    """Carica le coppie personalizzate dal file"""
    try:
        if os.path.exists(CUSTOM_SYMBOLS_FILE):
            with open(CUSTOM_SYMBOLS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento coppie personalizzate: {e}")
    return []

def save_custom_symbols(symbols):
    """Salva le coppie personalizzate nel file"""
    try:
        with open(CUSTOM_SYMBOLS_FILE, 'w') as f:
            json.dump(symbols, f, indent=2)
        return True
    except Exception as e:
        print(f"Errore nel salvataggio coppie personalizzate: {e}")
        return False

def get_all_symbols():
    """Restituisce tutte le coppie (default + personalizzate)"""
    custom_symbols = load_custom_symbols()
    return DEFAULT_SYMBOLS + custom_symbols

# Variabili globali per lo stato del bot
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

bot_thread = None
stop_bot_flag = False

@app.route('/')
def dashboard():
    """Dashboard principale"""
    return render_template('dashboard.html')

@app.route('/control')
def bot_control():
    """Pagina di controllo del bot"""
    return render_template('bot_control.html', bot_status=bot_status)

@app.route('/api-test')
def api_test():
    """Pagina per testare le API"""
    return render_template('api_test.html')

@app.route('/settings')
def settings():
    """Pagina delle impostazioni"""
    return render_template('settings.html', bot_status=bot_status)

# API Routes
@app.route('/api/balance')
def get_balance():
    """Ottieni il saldo del wallet"""
    try:
        from pybit.unified_trading import HTTP
        session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
        response = session.get_wallet_balance(accountType="UNIFIED")
        
        if response and 'result' in response:
            balance_data = response['result']['list'][0]
            return jsonify({
                'success': True,
                'data': {
                    'total_equity': float(balance_data.get('totalEquity', 0)),
                    'total_wallet_balance': float(balance_data.get('totalWalletBalance', 0)),
                    'total_margin_balance': float(balance_data.get('totalMarginBalance', 0)),
                    'total_available_balance': float(balance_data.get('totalAvailableBalance', 0))
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/price/<symbol>')
def get_price(symbol):
    """Ottieni il prezzo di un simbolo"""
    try:
        price = vedi_prezzo_moneta('linear', symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'price': price,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/market-data/<symbol>')
def get_market_data(symbol):
    """Ottieni dati di mercato per un simbolo"""
    try:
        # Ottieni dati delle candele
        kline_data = get_kline_data('linear', symbol, '30', 50)
        
        if kline_data:
            # Prepara i dati per il grafico
            chart_data = []
            for candle in reversed(kline_data):
                chart_data.append({
                    'timestamp': int(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            # Analisi EMA
            analysis = analizza_prezzo_sopra_media('linear', symbol, '30', 10)
            
            return jsonify({
                'success': True,
                'symbol': symbol,
                'chart_data': chart_data[-20:],  # Ultimi 20 punti
                'analysis': {
                    'above_ema': analysis[0],
                    'percentage_diff': analysis[1],
                    'current_price': analysis[2]
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-connection')
def test_connection():
    """Testa la connessione alle API"""
    try:
        from pybit.unified_trading import HTTP
        session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
        
        # Test con una richiesta semplice
        response = session.get_server_time()
        
        if response:
            return jsonify({
                'success': True,
                'message': 'Connessione API Bybit riuscita',
                'server_time': response.get('time', 0)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Avvia il bot di trading"""
    global bot_thread, stop_bot_flag, bot_status
    
    if bot_status['running']:
        return jsonify({'success': False, 'error': 'Il bot è già in esecuzione'})
    
    try:
        # Aggiorna i parametri del bot
        data = request.get_json()
        if data:
            bot_status.update(data)
        
        # Salva configurazione bot per recovery
        if state_manager:
            bot_config = {
                'symbol': data.get('symbol'),
                'quantity': data.get('quantity'),
                'operation': data.get('operation'),
                'ema_period': data.get('ema_period'),
                'interval': data.get('interval'),
                'open_candles': data.get('open_candles'),
                'stop_candles': data.get('stop_candles'),
                'distance': data.get('distance'),
                'timestamp': datetime.now().isoformat(),
                'auto_restart': True,
                'was_running': True
            }
            state_manager.save_bot_state('bot_config', bot_config)
            print("💾 Configurazione bot salvata per recovery")
        
        bot_status['running'] = True
        bot_status['last_update'] = datetime.now().isoformat()
        stop_bot_flag = False
        
        # Avvia il bot in un thread separato
        bot_thread = threading.Thread(target=run_trading_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        return jsonify({'success': True, 'message': 'Bot avviato con successo'})
    except Exception as e:
        bot_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Ferma il bot di trading"""
    global stop_bot_flag, bot_status
    
    stop_bot_flag = True
    bot_status['running'] = False
    bot_status['last_update'] = datetime.now().isoformat()
    
    # Aggiorna stato nel recovery (bot fermato manualmente)
    if state_manager:
        bot_config = state_manager.get_bot_state('bot_config')
        if bot_config:
            bot_config['was_running'] = False
            bot_config['stopped_manually'] = True
            bot_config['stop_timestamp'] = datetime.now().isoformat()
            state_manager.save_bot_state('bot_config', bot_config)
            print("💾 Stato bot aggiornato: fermato manualmente")
    
    # Chiudi la sessione corrente se attiva
    if bot_status.get('current_session_id'):
        try:
            # Ottieni saldo finale
            try:
                balance_response = mostra_saldo()
                final_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except:
                final_balance = 0
            
            trading_db.end_session(bot_status['current_session_id'], final_balance)
            trading_db.log_event(
                "BOT_STOP", 
                "SYSTEM", 
                f"Bot fermato. Sessione {bot_status['current_session_id']} terminata",
                {
                    'total_trades': bot_status['total_trades'],
                    'session_pnl': bot_status['session_pnl'],
                    'final_balance': final_balance
                },
                session_id=bot_status['current_session_id']
            )
            
            # Reset session data
            bot_status['current_session_id'] = None
            bot_status['session_start_time'] = None
            bot_status['total_trades'] = 0
            bot_status['session_pnl'] = 0
            
        except Exception as e:
            print(f"Errore nella chiusura della sessione: {e}")
    
    return jsonify({'success': True, 'message': 'Bot fermato'})

@app.route('/api/bot/status')
def get_bot_status():
    """Ottieni lo stato del bot"""
    return jsonify(bot_status)

@app.route('/api/bot/settings', methods=['POST'])
def update_bot_settings():
    """Aggiorna le impostazioni del bot"""
    global bot_status
    
    try:
        data = request.get_json()
        bot_status.update(data)
        bot_status['last_update'] = datetime.now().isoformat()
        
        return jsonify({'success': True, 'message': 'Impostazioni aggiornate'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/recovery/status')
def get_recovery_status():
    """Ottieni stato del recovery system"""
    try:
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        summary = state_manager.get_recovery_summary()
        
        return jsonify({
            'success': True,
            'recovery_summary': summary,
            'recovery_active': recovery_manager.recovery_active
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/recovery/start', methods=['POST'])
def start_recovery():
    """Avvia recovery del bot"""
    try:
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        result = recovery_manager.perform_initial_recovery()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/trailing-stop/add', methods=['POST'])
def add_trailing_stop():
    """Aggiungi trailing stop a una posizione"""
    try:
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        data = request.get_json()
        symbol = data.get('symbol')
        side = data.get('side')
        trail_percentage = float(data.get('trail_percentage', 0.5))
        
        if not symbol or not side:
            return jsonify({'success': False, 'error': 'Symbol e side sono richiesti'})
        
        result = recovery_manager.add_trailing_stop_to_position(symbol, side, trail_percentage)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/trailing-stops')
def get_trailing_stops():
    """Ottieni tutti i trailing stops attivi"""
    try:
        if not state_manager:
            return jsonify({'success': False, 'error': 'State manager non disponibile'})
        
        trailing_stops = state_manager.get_trailing_stops()
        active_strategies = state_manager.get_active_strategies()
        
        return jsonify({
            'success': True,
            'trailing_stops': trailing_stops,
            'active_strategies': active_strategies
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/strategy/remove', methods=['POST'])
def remove_strategy():
    """Rimuovi una strategia attiva"""
    try:
        if not state_manager:
            return jsonify({'success': False, 'error': 'State manager non disponibile'})
        
        data = request.get_json()
        symbol = data.get('symbol')
        side = data.get('side')
        
        if not symbol or not side:
            return jsonify({'success': False, 'error': 'Symbol e side sono richiesti'})
        
        # Rimuovi strategia e trailing stop
        state_manager.deactivate_strategy(symbol, side)
        state_manager.remove_trailing_stop(symbol, side)
        
        return jsonify({
            'success': True,
            'message': f'Strategia rimossa per {symbol} {side}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/recovery/auto-restart', methods=['POST'])
def auto_restart_bot():
    """Auto-riavvia il bot se necessario"""
    try:
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        # Controlla se il bot dovrebbe essere riavviato
        bot_config = state_manager.get_bot_state('bot_config')
        
        if not bot_config:
            return jsonify({'success': False, 'error': 'Nessuna configurazione bot salvata'})
        
        was_running = bot_config.get('was_running', False)
        stopped_manually = bot_config.get('stopped_manually', False)
        auto_restart = bot_config.get('auto_restart', True)
        
        if not (was_running and not stopped_manually and auto_restart):
            return jsonify({
                'success': False, 
                'error': 'Bot non dovrebbe essere riavviato automaticamente',
                'was_running': was_running,
                'stopped_manually': stopped_manually,
                'auto_restart': auto_restart
            })
        
        # Riavvia il bot
        restarted = recovery_manager._auto_restart_bot(bot_config)
        
        if restarted:
            return jsonify({
                'success': True,
                'message': f'Bot riavviato automaticamente con simbolo {bot_config.get("symbol")}',
                'config': bot_config
            })
        else:
            return jsonify({'success': False, 'error': 'Errore nel riavvio automatico del bot'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/config/last')
def get_last_bot_config():
    """Ottieni l'ultima configurazione del bot"""
    try:
        if not state_manager:
            return jsonify({'success': False, 'error': 'State manager non disponibile'})
        
        bot_config = state_manager.get_bot_state('bot_config')
        
        if bot_config:
            return jsonify({
                'success': True,
                'config': bot_config,
                'should_auto_restart': (
                    bot_config.get('was_running', False) and 
                    not bot_config.get('stopped_manually', False) and 
                    bot_config.get('auto_restart', True)
                )
            })
        else:
            return jsonify({'success': False, 'error': 'Nessuna configurazione salvata'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== BOT CONTROL ====================

@app.route('/api/history/sessions')
def get_session_history():
    """Ottieni storico sessioni"""
    try:
        limit = request.args.get('limit', 50, type=int)
        sessions = trading_db.get_session_history(limit)
        return jsonify({'success': True, 'data': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/trades')
def get_trade_history():
    """Ottieni storico trades"""
    try:
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', 100, type=int)
        trades = trading_db.get_trade_history(session_id, limit)
        return jsonify({'success': True, 'data': trades})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/performance')
def get_performance_stats():
    """Ottieni statistiche performance"""
    try:
        days = request.args.get('days', 30, type=int)
        stats = trading_db.get_performance_stats(days)
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/daily-performance')
def get_daily_performance():
    """Ottieni performance giornaliera"""
    try:
        days = request.args.get('days', 30, type=int)
        daily_data = trading_db.get_daily_performance(days)
        return jsonify({'success': True, 'data': daily_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/events')
def get_recent_events():
    """Ottieni eventi recenti"""
    try:
        limit = request.args.get('limit', 50, type=int)
        events = trading_db.get_recent_events(limit)
        return jsonify({'success': True, 'data': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/save', methods=['POST'])
def save_bot_config():
    """Salva configurazione bot"""
    try:
        data = request.get_json()
        config_name = data.get('name', f"Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        config_data = data.get('config', {})
        set_active = data.get('set_active', False)
        
        trading_db.save_bot_config(config_name, config_data, set_active)
        return jsonify({'success': True, 'message': 'Configurazione salvata'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/list')
def get_bot_configs():
    """Ottieni configurazioni salvate"""
    try:
        configs = trading_db.get_bot_configs()
        return jsonify({'success': True, 'data': configs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/export/data')
def export_trading_data():
    """Esporta dati di trading"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        export_filename = f"trading_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = os.path.join(os.path.dirname(__file__), 'exports', export_filename)
        
        # Crea cartella exports se non esiste
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        
        trading_db.export_data(export_path, start_date, end_date)
        
        return jsonify({
            'success': True, 
            'message': 'Dati esportati con successo',
            'filename': export_filename,
            'path': export_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/history')
def history_page():
    """Pagina storico trading"""
    return render_template('history.html')

@app.route('/api/history/sessions')
def get_trading_sessions():
    """Ottieni storico delle sessioni di trading"""
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        sessions = trading_db.get_sessions_history(days, limit)
        
        return jsonify({
            'success': True,
            'sessions': sessions,
            'total': len(sessions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/trades')
def get_trades_history():
    """Ottieni storico dei trade"""
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        symbol = request.args.get('symbol')
        
        trades = trading_db.get_trades_history(days, limit, symbol)
        
        return jsonify({
            'success': True,
            'trades': trades,
            'total': len(trades)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/analytics')
def get_trading_analytics():
    """Ottieni analytics del trading"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # Combina varie statistiche per analytics
        performance = trading_db.get_performance_stats(days)
        daily_perf = trading_db.get_daily_performance(days)
        recent_trades = trading_db.get_trade_history(limit=10)
        
        analytics = {
            'performance': performance,
            'daily_performance': daily_perf,
            'recent_trades': recent_trades,
            'total_sessions': len(trading_db.get_session_history(limit=1000))
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history/performance')
def get_performance_data():
    """Ottieni dati di performance per grafici"""
    try:
        days = request.args.get('days', 30, type=int)
        
        performance = trading_db.get_performance_stats(days)
        
        return jsonify({
            'success': True,
            'performance': performance
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def get_analytics_data():
    """Funzione helper per ottenere dati analitici"""
    try:
        # Combina varie statistiche
        performance = trading_db.get_performance_stats(30)
        daily_perf = trading_db.get_daily_performance(30)
        recent_trades = trading_db.get_trade_history(limit=10)
        
        return {
            'performance': performance,
            'daily_performance': daily_perf,
            'recent_trades': recent_trades,
            'total_sessions': len(trading_db.get_session_history(limit=1000))
        }
    except Exception as e:
        logger.error(f"Errore nel recupero analytics: {e}")
        return {}

@app.route('/api/trading/open-position', methods=['POST'])
def api_open_position():
    """API per aprire una posizione manualmente"""
    try:
        data = request.get_json()
        
        symbol = data.get('symbol', 'AVAXUSDT')
        side = data.get('side', 'Buy')  # 'Buy' o 'Sell'
        quantity = data.get('quantity', 10)
        price = data.get('price')  # None per market order
        
        # Assicurati che ci sia una sessione attiva
        if not bot_status.get('current_session_id'):
            # Crea una sessione manuale
            strategy_config = {
                'symbol': symbol,
                'mode': 'MANUAL',
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                balance_response = mostra_saldo()
                initial_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except:
                initial_balance = 0
            
            session_id = trading_db.start_session(symbol, strategy_config, initial_balance)
            bot_status['current_session_id'] = session_id
            trading_wrapper.set_session(session_id)
        
        # Apri posizione usando il wrapper
        result = trading_wrapper.open_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            strategy_signal='MANUAL_API'
        )
        
        if result['success']:
            bot_status['total_trades'] += 1
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore apertura posizione: {str(e)}'
        })

@app.route('/api/trading/close-position', methods=['POST'])
def api_close_position():
    """API per chiudere una posizione"""
    try:
        data = request.get_json()
        
        trade_id = data.get('trade_id')
        symbol = data.get('symbol')
        side = data.get('side')
        price = data.get('price')  # None per market price
        reason = data.get('reason', 'MANUAL_CLOSE')
        
        # Se non abbiamo trade_id ma abbiamo symbol e side, prova a trovarlo
        if not trade_id and symbol and side:
            active_trades = trading_wrapper.get_active_trades()
            for tid, trade_info in active_trades.items():
                if (trade_info.get('symbol') == symbol and 
                    trade_info.get('side') == side):
                    trade_id = tid
                    break
        
        # Se ancora non abbiamo trade_id, prova a cercare nel database
        if not trade_id and symbol and side:
            try:
                if trading_wrapper.current_session_id:
                    trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
                    open_trades = [t for t in trades if t['status'] == 'OPEN' 
                                 and t['symbol'] == symbol and t['side'] == side]
                    if open_trades:
                        trade_id = open_trades[0]['trade_id']
            except Exception as e:
                print(f"Errore ricerca trade nel database: {e}")
        
        if not trade_id:
            return jsonify({
                'success': False,
                'error': f'Trade non trovato per {symbol} {side}. Verifica che ci sia una posizione aperta.'
            })
        
        result = trading_wrapper.close_position(
            trade_id=trade_id,
            price=price,
            reason=reason
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore chiusura posizione: {str(e)}'
        })

@app.route('/api/trading/active-trades')
def get_active_trades():
    """Ottieni trade attualmente attivi"""
    try:
        active_trades = trading_wrapper.get_active_trades()
        return jsonify({
            'success': True,
            'data': active_trades
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trading/positions')
def get_bybit_positions():
    """Ottiene le posizioni attive direttamente da Bybit con PnL"""
    try:
        # Import della sessione Bybit
        from pybit.unified_trading import HTTP
        
        session = HTTP(
            testnet=False,
            api_key=api,
            api_secret=api_sec,
        )
        
        # Prova diverse categorie di posizioni
        debug_info = {
            'linear_positions': [],
            'spot_positions': [],
            'inverse_positions': [],
            'option_positions': []
        }
        
        # Testa categoria linear con settleCoin USDT (principale)
        try:
            linear_response = session.get_positions(category="linear", settleCoin="USDT")
            debug_info['linear_response'] = linear_response
            if linear_response['retCode'] == 0:
                debug_info['linear_positions'] = linear_response['result']['list']
        except Exception as e:
            debug_info['linear_exception'] = str(e)
        
        # Testa categoria linear con settleCoin BTC
        try:
            linear_btc_response = session.get_positions(category="linear", settleCoin="BTC")
            debug_info['linear_btc_response'] = linear_btc_response
            if linear_btc_response['retCode'] == 0:
                debug_info['linear_btc_positions'] = linear_btc_response['result']['list']
                # Aggiungi a linear_positions se presente
                if 'linear_positions' not in debug_info:
                    debug_info['linear_positions'] = []
                debug_info['linear_positions'].extend(linear_btc_response['result']['list'])
        except Exception as e:
            debug_info['linear_btc_exception'] = str(e)
        
        # Testa categoria linear con settleCoin ETH
        try:
            linear_eth_response = session.get_positions(category="linear", settleCoin="ETH")
            debug_info['linear_eth_response'] = linear_eth_response
            if linear_eth_response['retCode'] == 0:
                debug_info['linear_eth_positions'] = linear_eth_response['result']['list']
                # Aggiungi a linear_positions se presente
                if 'linear_positions' not in debug_info:
                    debug_info['linear_positions'] = []
                debug_info['linear_positions'].extend(linear_eth_response['result']['list'])
        except Exception as e:
            debug_info['linear_eth_exception'] = str(e)
        
        # Testa categoria spot - RIMOSSO (non supporta posizioni)
        # Le posizioni spot non esistono in Bybit, sono solo bilanci
        debug_info['spot_positions'] = []
        debug_info['spot_note'] = "Spot non supporta posizioni, solo bilanci wallet"
        
        # Testa categoria inverse
        try:
            inverse_response = session.get_positions(category="inverse")
            debug_info['inverse_response'] = inverse_response
            if inverse_response['retCode'] == 0:
                debug_info['inverse_positions'] = inverse_response['result']['list']
        except Exception as e:
            debug_info['inverse_exception'] = str(e)
        
        # Testa categoria option
        try:
            option_response = session.get_positions(category="option")
            debug_info['option_response'] = option_response
            if option_response['retCode'] == 0:
                debug_info['option_positions'] = option_response['result']['list']
        except Exception as e:
            debug_info['option_exception'] = str(e)
        
        # Prova anche senza categoria (tutte) - RIMOSSO perché non supportato
        debug_info['all_note'] = "API get_positions() senza categoria non supportata"
        
        # Combina tutte le posizioni attive
        active_positions = []
        all_positions = debug_info.get('linear_positions', []) + debug_info.get('inverse_positions', []) + debug_info.get('option_positions', [])
        
        for position in all_positions:
            # Filtra solo posizioni con size > 0
            if float(position.get('size', 0)) > 0:
                try:
                    current_price = float(vedi_prezzo_moneta('linear', position['symbol']))
                    entry_price = float(position.get('avgPrice', 0)) if position.get('avgPrice') else 0
                    size = float(position['size'])
                    
                    # Calcola PnL
                    unrealized_pnl = float(position.get('unrealisedPnl', 0))
                    pnl_percentage = (unrealized_pnl / (entry_price * size)) * 100 if entry_price > 0 and size > 0 else 0
                    
                    active_positions.append({
                        'symbol': position['symbol'],
                        'side': position.get('side', 'Unknown'),
                        'size': size,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_percentage': round(pnl_percentage, 2),
                        'leverage': position.get('leverage', 'N/A'),
                        'created_time': position.get('createdTime', 'N/A'),
                        'category': position.get('category', 'linear')
                    })
                except Exception as e:
                    print(f"Errore nel processing della posizione {position.get('symbol', 'Unknown')}: {e}")
        
        return jsonify({
            'success': True,
            'positions': active_positions,
            'total_positions': len(active_positions),
            'debug_info': debug_info  # Include info di debug per troubleshooting
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trading/sync-trades', methods=['POST'])
def sync_trades():
    """Sincronizza trade con il database e Bybit"""
    try:
        # Prima sincronizza con il database
        trading_wrapper.sync_with_database()
        
        # Poi sincronizza con Bybit
        bybit_result = trading_wrapper.sync_with_bybit()
        
        active_trades = trading_wrapper.get_active_trades()
        
        # Poi verifica se ci sono trade che il database conosce ma il wrapper no
        if trading_wrapper.current_session_id:
            db_trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
            open_db_trades = [t for t in db_trades if t['status'] == 'OPEN']
            
            # Aggiungi trade mancanti al wrapper
            for db_trade in open_db_trades:
                trade_id = db_trade['trade_id']
                if trade_id not in active_trades:
                    trading_wrapper.active_trades[trade_id] = {
                        'symbol': db_trade['symbol'],
                        'side': db_trade['side'],
                        'quantity': db_trade['quantity'],
                        'entry_price': db_trade['entry_price'],
                        'timestamp': db_trade['entry_time']
                    }
                    print(f"✅ Trade ricaricato dal DB: {trade_id} - {db_trade['side']} {db_trade['symbol']}")
        
        # Ricarica dopo tutte le sincronizzazioni
        active_trades = trading_wrapper.get_active_trades()
        
        return jsonify({
            'success': True,
            'message': f'Sincronizzazione completata: {len(active_trades)} trade attivi',
            'active_trades': len(active_trades),
            'trade_details': active_trades,
            'bybit_sync': bybit_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trading/debug-trades')
def debug_trades():
    """Debug per verificare tutti i trade"""
    try:
        # Trade nel wrapper
        wrapper_trades = trading_wrapper.get_active_trades()
        
        # Trade nel database
        db_trades = []
        if trading_wrapper.current_session_id:
            all_trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
            db_trades = [t for t in all_trades if t['status'] == 'OPEN']
        
        return jsonify({
            'success': True,
            'current_session_id': trading_wrapper.current_session_id,
            'wrapper_trades_count': len(wrapper_trades),
            'wrapper_trades': wrapper_trades,
            'db_trades_count': len(db_trades),
            'db_trades': db_trades
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trading/positions/debug')
def debug_bybit_positions():
    """Debug API per controllare tutte le posizioni Bybit"""
    try:
        from pybit.unified_trading import HTTP
        
        session = HTTP(
            testnet=False,
            api_key=api,
            api_secret=api_sec,
        )
        
        debug_data = {}
        
        # Test diverse categorie
        categories = ['linear', 'spot', 'inverse', 'option']
        
        for category in categories:
            try:
                response = session.get_positions(category=category)
                debug_data[f'{category}_response'] = response
                
                if response['retCode'] == 0:
                    positions = response['result']['list']
                    debug_data[f'{category}_count'] = len(positions)
                    debug_data[f'{category}_positions'] = positions
                    
                    # Filtra solo posizioni non vuote
                    active = [p for p in positions if float(p.get('size', 0)) > 0]
                    debug_data[f'{category}_active'] = active
                    debug_data[f'{category}_active_count'] = len(active)
                else:
                    debug_data[f'{category}_error'] = response.get('retMsg', 'Unknown error')
                    
            except Exception as e:
                debug_data[f'{category}_exception'] = str(e)
        
        # Test senza categoria
        try:
            all_response = session.get_positions()
            debug_data['all_positions_response'] = all_response
        except Exception as e:
            debug_data['all_positions_exception'] = str(e)
        
        # Test balance per vedere se l'API funziona
        try:
            balance_response = session.get_wallet_balance(accountType="UNIFIED")
            debug_data['wallet_balance'] = balance_response
        except Exception as e:
            debug_data['wallet_balance_exception'] = str(e)
        
        return jsonify({
            'success': True,
            'debug_data': debug_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== API GESTIONE SIMBOLI ====================

@app.route('/api/symbols')
def get_symbols():
    """Restituisce tutti i simboli disponibili"""
    return jsonify({
        'success': True,
        'symbols': get_all_symbols()
    })

@app.route('/api/symbols/verify/<symbol>')
def verify_symbol(symbol):
    """Verifica se un simbolo esiste su Bybit"""
    try:
        # Prova a ottenere il prezzo per verificare l'esistenza
        price_data = vedi_prezzo_moneta('linear', symbol.upper())
        if price_data and price_data > 0:
            return jsonify({
                'success': True,
                'exists': True,
                'price': price_data,
                'symbol': symbol.upper()
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'error': 'Simbolo non trovato'
            })
    except Exception as e:
        return jsonify({
            'success': True,
            'exists': False,
            'error': str(e)
        })

@app.route('/api/symbols/add', methods=['POST'])
def add_custom_symbol():
    """Aggiunge un nuovo simbolo personalizzato"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        name = data.get('name', '').strip()
        
        if not symbol or not name:
            return jsonify({
                'success': False,
                'error': 'Simbolo e nome sono richiesti'
            })
        
        # Verifica che il simbolo non esista già
        all_symbols = get_all_symbols()
        existing_symbols = [s['symbol'] for s in all_symbols]
        
        if symbol in existing_symbols:
            return jsonify({
                'success': False,
                'error': 'Simbolo già esistente'
            })
        
        # Verifica esistenza su Bybit
        try:
            price = vedi_prezzo_moneta('linear', symbol)
            if not price or price <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Simbolo non trovato su Bybit'
                })
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Simbolo non valido o non esistente su Bybit'
            })
        
        # Aggiunge il simbolo alle coppie personalizzate
        custom_symbols = load_custom_symbols()
        new_symbol = {'symbol': symbol, 'name': name}
        custom_symbols.append(new_symbol)
        
        if save_custom_symbols(custom_symbols):
            return jsonify({
                'success': True,
                'symbol': new_symbol,
                'message': f'Simbolo {symbol} aggiunto con successo'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nel salvataggio del simbolo'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/symbols/remove/<symbol>', methods=['DELETE'])
def remove_custom_symbol(symbol):
    """Rimuove un simbolo personalizzato"""
    try:
        symbol = symbol.upper()
        
        # Verifica che non sia un simbolo default
        default_symbols = [s['symbol'] for s in DEFAULT_SYMBOLS]
        if symbol in default_symbols:
            return jsonify({
                'success': False,
                'error': 'Non è possibile rimuovere simboli di default'
            })
        
        custom_symbols = load_custom_symbols()
        custom_symbols = [s for s in custom_symbols if s['symbol'] != symbol]
        
        if save_custom_symbols(custom_symbols):
            return jsonify({
                'success': True,
                'message': f'Simbolo {symbol} rimosso con successo'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nella rimozione del simbolo'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== FUNZIONI BOT ====================

def run_trading_bot():
    """Esegue il bot di trading"""
    global stop_bot_flag, bot_status
    
    try:
        # Configura sempre il wrapper prima di iniziare
        if bot_status['current_session_id']:
            # Usa sessione esistente
            trading_wrapper.set_session(bot_status['current_session_id'])
            trading_wrapper.sync_with_database()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Continuando sessione esistente: {bot_status['current_session_id']}")
        else:
            # Crea nuova sessione
            strategy_config = {
                'symbol': bot_status['symbol'],
                'ema_period': bot_status['ema_period'],
                'interval': bot_status['interval'],
                'open_candles': bot_status['open_candles'],
                'stop_candles': bot_status['stop_candles'],
                'distance': bot_status['distance'],
                'quantity': bot_status['quantity'],
                'operation': bot_status['operation']
            }
            
            # Ottieni saldo iniziale
            try:
                balance_response = mostra_saldo()
                initial_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except:
                initial_balance = 0
            
            bot_status['current_session_id'] = trading_db.start_session(
                bot_status['symbol'], 
                strategy_config, 
                initial_balance
            )
            bot_status['session_start_time'] = datetime.now().isoformat()
            bot_status['total_trades'] = 0
            bot_status['session_pnl'] = 0
            
            # Configura il wrapper di trading per la sessione
            trading_wrapper.set_session(bot_status['current_session_id'])
            trading_wrapper.sync_with_database()
            
            trading_db.log_event(
                "BOT_START", 
                "SYSTEM", 
                f"Bot avviato per {bot_status['symbol']}", 
                strategy_config,
                session_id=bot_status['current_session_id']
            )
            
        # Verifica trade attivi
        active_trades = trading_wrapper.get_active_trades()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Trade attivi trovati: {len(active_trades)}")
        for trade_id, trade_info in active_trades.items():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 {trade_id}: {trade_info['side']} {trade_info['symbol']} - {trade_info['quantity']}")
        
        while not stop_bot_flag and bot_status['running']:
            try:
                # Analisi di mercato
                symbol = bot_status['symbol']
                current_price = vedi_prezzo_moneta('linear', symbol)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Analizzando {symbol} - Prezzo: ${current_price:.4f}")
                
                # Invia log al frontend
                socketio.emit('analysis_log', {
                    'message': f"🔍 Analizzando {symbol} - Prezzo: ${current_price:.4f}",
                    'type': 'info'
                })
                
                # Ottieni dati EMA se disponibili
                try:
                    # Usa l'intervallo configurato dall'utente
                    interval = bot_status['interval']
                    klines = get_kline_data('linear', symbol, interval, 200)  # 200 candele per calcolare EMA correttamente
                    if klines:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Analisi tecnica in corso...")
                        
                        # Invia log al frontend
                        socketio.emit('analysis_log', {
                            'message': f"📊 Analisi tecnica in corso...",
                            'type': 'info'
                        })
                        
                        # Analisi EMA
                        ema_analysis = analizza_prezzo_sopra_media('linear', symbol, interval, bot_status['ema_period'])
                        # ema_analysis restituisce una tupla: (candele_sopra_ema, prezzo_attuale, differenza_percentuale, timestamp_attuale)
                        if ema_analysis and len(ema_analysis) >= 3:
                            candles_above_ema = ema_analysis[0]
                            current_price_from_analysis = ema_analysis[1]
                            distance_percent = ema_analysis[2]
                            is_above_ema = distance_percent > 0
                        else:
                            candles_above_ema = 0
                            distance_percent = 0
                            is_above_ema = False
                        
                        # Calcola EMA attuale per visualizzazione
                        try:
                            # Usa la stessa logica di analizza_prezzo_sopra_media
                            reversed_klines = reversed(klines)
                            close_prices = [float(candle[4]) for candle in reversed_klines]
                            ema_values = media_esponenziale(close_prices, bot_status['ema_period'])
                            ema_value = ema_values[-1] if ema_values else current_price
                            
                            # Ricalcola la percentuale correttamente
                            if ema_value > 0:
                                distance_percent = ((current_price - ema_value) / ema_value) * 100
                                is_above_ema = distance_percent > 0
                        except Exception as e:
                            print(f"Errore nel calcolo EMA: {e}")
                            ema_value = current_price
                        
                        # Controlla candele consecutive
                        candles_above_result = controlla_candele_sopra_ema('linear', symbol, interval, bot_status['ema_period'])
                        candles_below_result = controlla_candele_sotto_ema('linear', symbol, interval, bot_status['ema_period'])
                        
                        # Estrai solo il numero di candele dalle tuple restituite
                        candles_above = candles_above_result[0] if candles_above_result and len(candles_above_result) > 0 else 0
                        candles_below = candles_below_result[0] if candles_below_result and len(candles_below_result) > 0 else 0
                        
                        # Log dettagliato dell'analisi
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 EMA({bot_status['ema_period']}): ${ema_value:.4f}")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Prezzo {'SOPRA' if is_above_ema else 'SOTTO'} EMA ({distance_percent:+.2f}%)")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🕯️ Candele sopra EMA: {candles_above}/{bot_status['open_candles']} richieste")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🕯️ Candele sotto EMA: {candles_below}/{bot_status['open_candles']} richieste")
                        
                        # Invia log dettagliati al frontend
                        socketio.emit('analysis_log', {
                            'message': f"📈 EMA({bot_status['ema_period']}): ${ema_value:.4f}",
                            'type': 'info'
                        })
                        socketio.emit('analysis_log', {
                            'message': f"📍 Prezzo {'SOPRA' if is_above_ema else 'SOTTO'} EMA ({distance_percent:+.2f}%)",
                            'type': 'info'
                        })
                        socketio.emit('analysis_log', {
                            'message': f"🕯️ Candele sopra EMA: {candles_above}/{bot_status['open_candles']} | sotto EMA: {candles_below}/{bot_status['open_candles']}",
                            'type': 'info'
                        })
                        
                        # Controlla condizioni di entrata
                        distance_ok = abs(distance_percent) <= bot_status['distance']
                        
                        # Verifica se ci sono posizioni attive PRIMA di analizzare apertura
                        active_trades = trading_wrapper.get_active_trades()
                        
                        # ============= ANALISI APERTURA (solo se nessuna posizione attiva) =============
                        if not active_trades:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Nessuna posizione attiva - Analisi condizioni apertura...")
                            socketio.emit('analysis_log', {
                                'message': f"🔍 Nessuna posizione attiva - Analisi condizioni apertura...",
                                'type': 'info'
                            })
                            
                            # Condizioni per LONG
                            if bot_status['operation']:  # True = Long
                                long_conditions = {
                                    'above_ema': is_above_ema,
                                    'enough_candles': candles_above >= bot_status['open_candles'],
                                    'distance_ok': distance_ok
                                }
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 LONG - Condizioni apertura:")
                                print(f"  ✅ Sopra EMA: {'✅' if long_conditions['above_ema'] else '❌'}")
                                print(f"  ✅ Candele richieste: {'✅' if long_conditions['enough_candles'] else '❌'} ({candles_above}/{bot_status['open_candles']})")
                                print(f"  ✅ Distanza OK: {'✅' if long_conditions['distance_ok'] else '❌'} ({distance_percent:.2f}% <= {bot_status['distance']}%)")
                                
                                # Invia log delle condizioni al frontend
                                socketio.emit('analysis_log', {
                                    'message': f"🟢 LONG - Analisi condizioni apertura:",
                                    'type': 'info'
                                })
                                socketio.emit('analysis_log', {
                                    'message': f"  {'✅' if long_conditions['above_ema'] else '❌'} Sopra EMA | {'✅' if long_conditions['enough_candles'] else '❌'} Candele ({candles_above}/{bot_status['open_candles']}) | {'✅' if long_conditions['distance_ok'] else '❌'} Distanza ({distance_percent:.2f}%)",
                                    'type': 'info'
                                })
                                
                                if all(long_conditions.values()):
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE LONG! Tutte le condizioni soddisfatte")
                                    
                                    # Invia segnale al frontend
                                    socketio.emit('analysis_log', {
                                        'message': f"🚀 SEGNALE LONG! Tutte le condizioni soddisfatte",
                                        'type': 'success'
                                    })
                                    
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 Apertura posizione LONG...")
                                    
                                    # Apri posizione long
                                    result = trading_wrapper.open_position(
                                        symbol=symbol,
                                        side='Buy',
                                        quantity=bot_status['quantity'],
                                        strategy_signal=f"EMA_LONG_{bot_status['ema_period']}",
                                        categoria=bot_status['category'],
                                        periodo_ema=bot_status['ema_period'],
                                        intervallo=bot_status['interval'],
                                        candele=bot_status['open_candles'],
                                        lunghezza=bot_status['distance']
                                    )
                                    
                                    if result['success']:
                                        bot_status['total_trades'] += 1
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Posizione LONG aperta con successo!")
                                        
                                        socketio.emit('trade_notification', {
                                            'type': 'POSITION_OPENED',
                                            'side': 'LONG',
                                            'symbol': symbol,
                                            'price': current_price,
                                            'quantity': bot_status['quantity'],
                                            'timestamp': datetime.now().isoformat()
                                        })
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore apertura LONG: {result.get('error')}")
                                else:
                                    failed_conditions = [k for k, v in long_conditions.items() if not v]
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ LONG non attivato. Mancano: {', '.join(failed_conditions)}")
                                    
                                    # Invia log al frontend
                                    socketio.emit('analysis_log', {
                                        'message': f"⏳ LONG non attivato. Mancano: {', '.join(failed_conditions)}",
                                        'type': 'warning'
                                    })
                            
                            # Condizioni per SHORT
                            else:  # False = Short
                                short_conditions = {
                                    'below_ema': not is_above_ema,
                                    'enough_candles': candles_below >= bot_status['open_candles'],
                                    'distance_ok': distance_ok
                                }
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 SHORT - Condizioni apertura:")
                                print(f"  ✅ Sotto EMA: {'✅' if short_conditions['below_ema'] else '❌'}")
                                print(f"  ✅ Candele richieste: {'✅' if short_conditions['enough_candles'] else '❌'} ({candles_below}/{bot_status['open_candles']})")
                                print(f"  ✅ Distanza OK: {'✅' if short_conditions['distance_ok'] else '❌'} ({abs(distance_percent):.2f}% <= {bot_status['distance']}%)")
                                
                                # Invia log delle condizioni al frontend
                                socketio.emit('analysis_log', {
                                    'message': f"🔴 SHORT - Analisi condizioni apertura:",
                                    'type': 'info'
                                })
                                socketio.emit('analysis_log', {
                                    'message': f"  {'✅' if short_conditions['below_ema'] else '❌'} Sotto EMA | {'✅' if short_conditions['enough_candles'] else '❌'} Candele ({candles_below}/{bot_status['open_candles']}) | {'✅' if short_conditions['distance_ok'] else '❌'} Distanza ({abs(distance_percent):.2f}%)",
                                    'type': 'info'
                                })
                                
                                if all(short_conditions.values()):
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE SHORT! Tutte le condizioni soddisfatte")
                                    
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 Apertura posizione SHORT...")
                                    
                                    # Apri posizione short
                                    result = trading_wrapper.open_position(
                                        symbol=symbol,
                                        side='Sell',
                                        quantity=bot_status['quantity'],
                                        strategy_signal=f"EMA_SHORT_{bot_status['ema_period']}",
                                        categoria=bot_status['category'],
                                        periodo_ema=bot_status['ema_period'],
                                        intervallo=bot_status['interval'],
                                        candele=bot_status['open_candles'],
                                        lunghezza=bot_status['distance']
                                    )
                                    
                                    if result['success']:
                                        bot_status['total_trades'] += 1
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Posizione SHORT aperta con successo!")
                                        
                                        socketio.emit('trade_notification', {
                                            'type': 'POSITION_OPENED',
                                            'side': 'SHORT',
                                            'symbol': symbol,
                                            'price': current_price,
                                            'quantity': bot_status['quantity'],
                                            'timestamp': datetime.now().isoformat()
                                        })
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore apertura SHORT: {result.get('error')}")
                                else:
                                    failed_conditions = [k for k, v in short_conditions.items() if not v]
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ SHORT non attivato. Mancano: {', '.join(failed_conditions)}")
                        
                        # ============= ANALISI CHIUSURA (solo se ci sono posizioni attive) =============
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Posizioni attive trovate ({len(active_trades)}) - Analisi condizioni chiusura...")
                            socketio.emit('analysis_log', {
                                'message': f"📊 Posizioni attive trovate ({len(active_trades)}) - Analisi condizioni chiusura...",
                                'type': 'info'
                            })
                        
                        # Controlla se ci sono posizioni da chiudere (SEMPRE, indipendentemente se stiamo aprendo o meno)
                        active_trades = trading_wrapper.get_active_trades()
                        if active_trades:
                            for trade_id, trade_info in active_trades.items():
                                trade_side = trade_info['side']
                                trade_symbol = trade_info.get('symbol', bot_status['symbol'])
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Analizzando posizione {trade_side} {trade_symbol} (ID: {trade_id})")
                                
                                # Invia log dettaglio posizione al frontend
                                socketio.emit('analysis_log', {
                                    'message': f"🔄 Analizzando posizione {trade_side} {trade_symbol} (ID: {trade_id})",
                                    'type': 'info'
                                })
                                
                                # Verifica trailing stop prima delle condizioni EMA - DISATTIVATO
                                # if recovery_manager:
                                #     print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Controllo trailing stops...")
                                #     trailing_stop_result = recovery_manager._check_trailing_stops()
                                #     print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Trailing stop result = {trailing_stop_result}")
                                #     if trailing_stop_result:
                                #         print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Trailing stop attivato per {trade_symbol}")
                                #         socketio.emit('analysis_log', {
                                #             'message': f"🎯 Trailing stop attivato per {trade_symbol}",
                                #             'type': 'success'
                                #         })
                                #         continue  # Salta alle altre posizioni se questa è stata chiusa
                                #     else:
                                #         print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Nessun trailing stop attivato, continuo con analisi EMA...")
                                # else:
                                #     print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Recovery manager non disponibile")
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Recovery manager disattivato - Procedo con analisi EMA...")
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: trade_side = {trade_side}")
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: candles_above = {candles_above}, candles_below = {candles_below}")
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: stop_candles = {bot_status['stop_candles']}")
                                
                                # Condizioni di chiusura per LONG
                                if trade_side == 'Buy':
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Entrato nel blocco LONG")
                                    close_long = candles_below >= bot_status['stop_candles']
                                    
                                    # Log delle condizioni di chiusura LONG
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 LONG {trade_symbol} - Analisi chiusura:")
                                    print(f" 📊  Candele sotto EMA: {candles_below}/{bot_status['stop_candles']} richieste")
                                    print(f"  🎯 Condizione chiusura: {'✅ SODDISFATTA' if close_long else '❌ NON SODDISFATTA'}")
                                    
                                    # Invia log condizioni al frontend
                                    socketio.emit('analysis_log', {
                                        'message': f"📊 LONG {trade_symbol} - Analisi chiusura:",
                                        'type': 'info'
                                    })
                                    socketio.emit('analysis_log', {
                                        'message': f"  📉 Candele sotto EMA: {candles_below}/{bot_status['stop_candles']} | {'✅ CHIUSURA' if close_long else '❌ MANTIENI'}",
                                        'type': 'success' if close_long else 'warning'
                                    })
                                    
                                    if close_long:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔻 🚨 SEGNALE CHIUSURA LONG! Eseguendo chiusura...")
                                        
                                        # Invia segnale chiusura al frontend
                                        socketio.emit('analysis_log', {
                                            'message': f"🔻 🚨 SEGNALE CHIUSURA LONG! Eseguendo chiusura...",
                                            'type': 'warning'
                                        })
                                        
                                        result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                                        if result['success']:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ LONG {trade_symbol} chiuso con successo!")
                                            
                                            # Notifica chiusura successo al frontend
                                            socketio.emit('analysis_log', {
                                                'message': f"✅ LONG {trade_symbol} chiuso con successo!",
                                                'type': 'success'
                                            })
                                            
                                            socketio.emit('trade_notification', {
                                                'type': 'POSITION_CLOSED',
                                                'side': 'LONG',
                                                'symbol': trade_symbol,
                                                'price': current_price,
                                                'reason': 'EMA_STOP',
                                                'timestamp': datetime.now().isoformat()
                                            })
                                            
                                            # Rimuovi trailing stop dopo chiusura - DISATTIVATO
                                            # if recovery_manager:
                                            #     recovery_manager.state_manager.remove_trailing_stop(trade_symbol, 'BUY')
                                        else:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore chiusura LONG: {result.get('error')}")
                                            socketio.emit('analysis_log', {
                                                'message': f"❌ Errore chiusura LONG: {result.get('error')}",
                                                'type': 'error'
                                            })
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 LONG {trade_symbol} mantiene posizione - Condizioni chiusura non soddisfatte")
                                        
                                        # Aggiungi/aggiorna trailing stop se non esiste - DISATTIVATO
                                        # if recovery_manager:
                                        #     trailing_stops = recovery_manager.state_manager.get_trailing_stops()
                                        #     has_trailing = any(ts['symbol'] == trade_symbol and ts['side'] == 'BUY' for ts in trailing_stops)
                                        #     if not has_trailing:
                                        #         result = recovery_manager.add_trailing_stop_to_position(trade_symbol, 'BUY', 0.5)
                                        #         if result['success']:
                                        #             print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Trailing stop aggiunto a {trade_symbol} LONG")
                                
                                # Condizioni di chiusura per SHORT  
                                elif trade_side == 'Sell':
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Entrato nel blocco SHORT")
                                    close_short = candles_above >= bot_status['stop_candles']                                    # Log delle condizioni di chiusura SHORT
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] SHORT {trade_symbol} - Analisi chiusura:")
                                    print(f"  📈 Candele sopra EMA: {candles_above}/{bot_status['stop_candles']} richieste")
                                    print(f"  🎯 Condizione chiusura: {'✅ SODDISFATTA' if close_short else '❌ NON SODDISFATTA'}")
                                    
                                    # Invia log condizioni al frontend
                                    socketio.emit('analysis_log', {
                                        'message': f"📊 SHORT {trade_symbol} - Analisi chiusura:",
                                        'type': 'info'
                                    })
                                    socketio.emit('analysis_log', {
                                        'message': f"  📈 Candele sopra EMA: {candles_above}/{bot_status['stop_candles']} | {'✅ CHIUSURA' if close_short else '❌ MANTIENI'}",
                                        'type': 'success' if close_short else 'warning'
                                    })
                                    
                                    if close_short:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔺 🚨 SEGNALE CHIUSURA SHORT! Eseguendo chiusura...")
                                        
                                        # Invia segnale chiusura al frontend
                                        socketio.emit('analysis_log', {
                                            'message': f"🔺 🚨 SEGNALE CHIUSURA SHORT! Eseguendo chiusura...",
                                            'type': 'warning'
                                        })
                                        
                                        result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                                        if result['success']:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ SHORT {trade_symbol} chiuso con successo!")
                                            
                                            # Notifica chiusura successo al frontend
                                            socketio.emit('analysis_log', {
                                                'message': f"✅ SHORT {trade_symbol} chiuso con successo!",
                                                'type': 'success'
                                            })
                                            
                                            socketio.emit('trade_notification', {
                                                'type': 'POSITION_CLOSED',
                                                'side': 'SHORT',
                                                'symbol': trade_symbol,
                                                'price': current_price,
                                                'reason': 'EMA_STOP',
                                                'timestamp': datetime.now().isoformat()
                                            })
                                            
                                            # Rimuovi trailing stop dopo chiusura - DISATTIVATO
                                            # if recovery_manager:
                                            #     recovery_manager.state_manager.remove_trailing_stop(trade_symbol, 'SELL')
                                        else:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore chiusura SHORT: {result.get('error')}")
                                            socketio.emit('analysis_log', {
                                                'message': f"❌ Errore chiusura SHORT: {result.get('error')}",
                                                'type': 'error'
                                            })
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📉 SHORT {trade_symbol} mantiene posizione - Condizioni chiusura non soddisfatte")
                                        
                                        # Aggiungi/aggiorna trailing stop se non esiste - DISATTIVATO
                                        # if recovery_manager:
                                        #     trailing_stops = recovery_manager.state_manager.get_trailing_stops()
                                        #     has_trailing = any(ts['symbol'] == trade_symbol and ts['side'] == 'SELL' for ts in trailing_stops)
                                        #     if not has_trailing:
                                        #         result = recovery_manager.add_trailing_stop_to_position(trade_symbol, 'SELL', 0.5)
                                        #         if result['success']:
                                        #             print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Trailing stop aggiunto a {trade_symbol} SHORT")
                        
                        # Salva analisi di mercato (converti tupla in dizionario)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Finita analisi per tutte le posizioni attive ({len(active_trades)} posizioni elaborate)")
                        ema_data = {
                            'candles_above_ema': candles_above_ema if 'candles_above_ema' in locals() else 0,
                            'price': current_price,
                            'distance_percent': distance_percent,
                            'ema_value': ema_value if 'ema_value' in locals() else current_price,
                            'is_above_ema': is_above_ema
                        }
                        trading_db.add_market_analysis(symbol, current_price, ema_data)
                        
                        # Log dell'analisi per database
                        analysis_msg = f"Prezzo: {current_price}, EMA: {ema_value:.4f}, Distanza: {distance_percent:.2f}%"
                        trading_db.log_event(
                            "MARKET_ANALYSIS", 
                            "TRADING", 
                            analysis_msg,
                            {
                                'price': current_price,
                                'ema_data': ema_data,
                                'candles_above': candles_above,
                                'candles_below': candles_below,
                                'distance_percent': distance_percent
                            },
                            session_id=bot_status['current_session_id']
                        )
                        
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Nessun dato kline disponibile per {symbol}")
                        
                except Exception as analysis_error:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore nell'analisi: {str(analysis_error)}")
                    trading_db.log_event(
                        "ANALYSIS_ERROR", 
                        "ERROR", 
                        f"Errore nell'analisi: {str(analysis_error)}",
                        {'error': str(analysis_error)},
                        severity="ERROR",
                        session_id=bot_status['current_session_id']
                    )
                
                # Emetti aggiornamenti via WebSocket
                socketio.emit('bot_update', {
                    'status': 'running',
                    'timestamp': datetime.now().isoformat(),
                    'message': f"Analisi completata per {symbol}",
                    'price': current_price,
                    'session_id': bot_status['current_session_id'],
                    'total_trades': bot_status['total_trades'],
                    'session_pnl': bot_status['session_pnl'],
                    'ema_value': ema_value if 'ema_value' in locals() else None,
                    'active_trades': len(trading_wrapper.get_active_trades()) if 'trading_wrapper' in globals() else 0
                })
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ Attendo prossimo ciclo (10 secondi)...")
                
                # Invia log al frontend
                socketio.emit('analysis_log', {
                    'message': f"⏱️ Attendo prossimo ciclo (10 secondi)...",
                    'type': 'info'
                })
                
            except Exception as loop_error:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore nel ciclo: {str(loop_error)}")
                trading_db.log_event(
                    "LOOP_ERROR", 
                    "ERROR", 
                    f"Errore nel ciclo: {str(loop_error)}",
                    {'error': str(loop_error)},
                    severity="ERROR",
                    session_id=bot_status['current_session_id']
                )
            
            time.sleep(10)  # Attendi 10 secondi prima del prossimo ciclo
            
    except Exception as e:
        bot_status['running'] = False
        if bot_status.get('current_session_id'):
            trading_db.log_event(
                "BOT_ERROR", 
                "ERROR", 
                f"Errore del bot: {str(e)}",
                {'error': str(e)},
                severity="ERROR",
                session_id=bot_status['current_session_id']
            )
        
        socketio.emit('bot_error', {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print('Client connesso')
    emit('status', {'msg': 'Connesso al server di trading'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnesso')

@socketio.on('request_update')
def handle_request_update():
    """Invia aggiornamenti in tempo reale"""
    try:
        # Ottieni dati di mercato
        if bot_status['symbol']:
            price = vedi_prezzo_moneta('linear', bot_status['symbol'])
            emit('price_update', {
                'symbol': bot_status['symbol'],
                'price': price,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    print("🚀 Avvio Trading Bot Dashboard...")
    
    # Avvia recovery automatico se disponibile
    if recovery_manager:
        print("� Controllo recovery automatico...")
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
    
    print("�📊 Dashboard disponibile su: http://localhost:5000")
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
