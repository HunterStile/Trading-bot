from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import sys
import os
import threading
import time
from datetime import datetime
import json

# Aggiungi il percorso del trading bot al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import delle funzioni del trading bot
try:
    from config import api, api_sec, TELEGRAM_TOKEN, CHAT_ID
    from trading_functions import (
        mostra_saldo, vedi_prezzo_moneta, get_kline_data, 
        analizza_prezzo_sopra_media, controlla_candele_sopra_ema,
        bot_open_position, bot_trailing_stop
    )
except ImportError as e:
    print(f"Errore nell'importazione delle funzioni del trading bot: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading_bot_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

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
    'last_update': None
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

def run_trading_bot():
    """Esegue il bot di trading"""
    global stop_bot_flag, bot_status
    
    try:
        while not stop_bot_flag and bot_status['running']:
            # Simula l'esecuzione del bot
            # In una implementazione reale, qui chiameresti le tue funzioni di trading
            
            # Emetti aggiornamenti via WebSocket
            socketio.emit('bot_update', {
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'message': f"Bot in esecuzione su {bot_status['symbol']}"
            })
            
            time.sleep(10)  # Attendi 10 secondi prima del prossimo ciclo
            
    except Exception as e:
        bot_status['running'] = False
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
