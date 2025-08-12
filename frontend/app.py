from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import sys
import os
import threading
import time
from datetime import datetime, timedelta
import json

# Aggiungi il percorso del trading bot al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import del database e wrapper
from utils.database import trading_db
from utils.trading_wrapper import trading_wrapper

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
socketio = SocketIO(app, cors_allowed_origins="*")

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

# ==================== ROUTE PER DATI STORICI ====================

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
        price = data.get('price')  # None per market price
        reason = data.get('reason', 'MANUAL_CLOSE')
        
        if not trade_id:
            return jsonify({
                'success': False,
                'error': 'Trade ID richiesto'
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

@app.route('/api/trading/sync-trades', methods=['POST'])
def sync_trades():
    """Sincronizza trade con il database"""
    try:
        trading_wrapper.sync_with_database()
        active_trades = trading_wrapper.get_active_trades()
        
        return jsonify({
            'success': True,
            'message': f'Sincronizzati {len(active_trades)} trade attivi',
            'active_trades': len(active_trades)
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
        # Avvia una nuova sessione di trading
        if not bot_status['current_session_id']:
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
                        
                        # Condizioni per LONG
                        if bot_status['operation']:  # True = Long
                            long_conditions = {
                                'above_ema': is_above_ema,
                                'enough_candles': candles_above >= bot_status['open_candles'],
                                'distance_ok': distance_ok
                            }
                            
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 LONG - Condizioni:")
                            print(f"  ✅ Sopra EMA: {'✅' if long_conditions['above_ema'] else '❌'}")
                            print(f"  ✅ Candele richieste: {'✅' if long_conditions['enough_candles'] else '❌'} ({candles_above}/{bot_status['open_candles']})")
                            print(f"  ✅ Distanza OK: {'✅' if long_conditions['distance_ok'] else '❌'} ({distance_percent:.2f}% <= {bot_status['distance']}%)")
                            
                            # Invia log delle condizioni al frontend
                            socketio.emit('analysis_log', {
                                'message': f"🟢 LONG - Analisi condizioni:",
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
                                
                                # Verifica se non abbiamo già posizioni aperte
                                active_trades = trading_wrapper.get_active_trades()
                                if not active_trades:
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
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Trade già attivi ({len(active_trades)}), attendo chiusura")
                                    
                                    # Invia log al frontend
                                    socketio.emit('analysis_log', {
                                        'message': f"⚠️ Trade già attivi ({len(active_trades)}), attendo chiusura",
                                        'type': 'warning'
                                    })
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
                            
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 SHORT - Condizioni:")
                            print(f"  ✅ Sotto EMA: {'✅' if short_conditions['below_ema'] else '❌'}")
                            print(f"  ✅ Candele richieste: {'✅' if short_conditions['enough_candles'] else '❌'} ({candles_below}/{bot_status['open_candles']})")
                            print(f"  ✅ Distanza OK: {'✅' if short_conditions['distance_ok'] else '❌'} ({abs(distance_percent):.2f}% <= {bot_status['distance']}%)")
                            
                            # Invia log delle condizioni al frontend
                            socketio.emit('analysis_log', {
                                'message': f"🔴 SHORT - Analisi condizioni:",
                                'type': 'info'
                            })
                            socketio.emit('analysis_log', {
                                'message': f"  {'✅' if short_conditions['below_ema'] else '❌'} Sotto EMA | {'✅' if short_conditions['enough_candles'] else '❌'} Candele ({candles_below}/{bot_status['open_candles']}) | {'✅' if short_conditions['distance_ok'] else '❌'} Distanza ({abs(distance_percent):.2f}%)",
                                'type': 'info'
                            })
                            
                            if all(short_conditions.values()):
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE SHORT! Tutte le condizioni soddisfatte")
                                
                                # Verifica se non abbiamo già posizioni aperte
                                active_trades = trading_wrapper.get_active_trades()
                                if not active_trades:
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
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Trade già attivi ({len(active_trades)}), attendo chiusura")
                            else:
                                failed_conditions = [k for k, v in short_conditions.items() if not v]
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ SHORT non attivato. Mancano: {', '.join(failed_conditions)}")
                        
                        # Controlla se ci sono posizioni da chiudere
                        active_trades = trading_wrapper.get_active_trades()
                        if active_trades:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 👀 Controllo {len(active_trades)} posizioni attive per chiusura...")
                            
                            # Invia log al frontend
                            socketio.emit('analysis_log', {
                                'message': f"👀 Controllo {len(active_trades)} posizioni attive per chiusura...",
                                'type': 'info'
                            })
                            
                            for trade_id, trade_info in active_trades.items():
                                trade_side = trade_info['side']
                                
                                # Condizioni di chiusura per LONG
                                if trade_side == 'BUY':
                                    close_long = candles_below >= bot_status['stop_candles']
                                    if close_long:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔻 Chiusura LONG: {candles_below} candele sotto EMA")
                                        result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                                        if result['success']:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ LONG chiuso con successo!")
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 LONG attivo - Candele sotto EMA: {candles_below}/{bot_status['stop_candles']}")
                                
                                # Condizioni di chiusura per SHORT
                                elif trade_side == 'SELL':
                                    close_short = candles_above >= bot_status['stop_candles']
                                    if close_short:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔺 Chiusura SHORT: {candles_above} candele sopra EMA")
                                        result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                                        if result['success']:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ SHORT chiuso con successo!")
                                    else:
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📉 SHORT attivo - Candele sopra EMA: {candles_above}/{bot_status['stop_candles']}")
                        
                        # Salva analisi di mercato (converti tupla in dizionario)
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
    print("📊 Dashboard disponibile su: http://localhost:5000")
    print("🔧 Controllo Bot: http://localhost:5000/control")
    print("🧪 Test API: http://localhost:5000/api-test")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
