from flask_socketio import emit
from datetime import datetime
from trading_functions import vedi_prezzo_moneta

def register_websocket_events(socketio, trading_wrapper, trading_db):
    """Registra tutti gli eventi WebSocket"""
    
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
            from flask import current_app
            bot_status = current_app.config['BOT_STATUS']
            
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