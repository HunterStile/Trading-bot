"""
WebSocket Events per Real-time Communication
Gestisce gli eventi real-time tra frontend Next.js e backend Flask
"""
from flask_socketio import emit, join_room, leave_room
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def register_websocket_events(socketio):
    """Registra tutti gli eventi WebSocket"""
    
    @socketio.on('connect')
    def on_connect():
        """Client connesso"""
        logger.info(f"Client connesso: {request.sid}")
        emit('connected', {
            'message': 'Connesso al Trading Bot Server',
            'timestamp': datetime.now().isoformat()
        })
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Client disconnesso"""
        logger.info(f"Client disconnesso: {request.sid}")
    
    @socketio.on('join_room')
    def on_join_room(data):
        """Join room per updates specifici"""
        room = data.get('room', 'general')
        join_room(room)
        logger.info(f"Client {request.sid} joined room: {room}")
        emit('joined_room', {'room': room})
    
    @socketio.on('leave_room') 
    def on_leave_room(data):
        """Leave room"""
        room = data.get('room', 'general')
        leave_room(room)
        logger.info(f"Client {request.sid} left room: {room}")
        emit('left_room', {'room': room})
    
    @socketio.on('request_bot_status')
    def on_request_bot_status():
        """Richiesta status bot real-time"""
        try:
            # Qui userai le tue funzioni per ottenere status real-time
            status = {
                'running': False,  # Da tuo bot state
                'symbol': 'BTCUSDT',
                'pnl': 0,
                'trades_today': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            emit('bot_status_update', status)
            
        except Exception as e:
            logger.error(f"Errore request_bot_status: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('request_market_data')
    def on_request_market_data(data):
        """Richiesta dati mercato real-time"""
        try:
            symbol = data.get('symbol', 'BTCUSDT')
            
            # Qui userai le tue funzioni per dati real-time
            market_data = {
                'symbol': symbol,
                'price': 43250.00,  # Da tua API
                'change_24h': 2.5,
                'volume': 1234567,
                'timestamp': datetime.now().isoformat()
            }
            
            emit('market_data_update', market_data)
            
        except Exception as e:
            logger.error(f"Errore request_market_data: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('request_ai_analysis')
    def on_request_ai_analysis(data):
        """Richiesta analisi AI real-time"""
        try:
            symbol = data.get('symbol', 'BTCUSDT')
            
            # Qui integrerai il tuo sistema AI
            ai_analysis = {
                'symbol': symbol,
                'signal': 'BUY',
                'confidence': 0.85,
                'reasoning': [
                    'EMA crossover detected',
                    'Volume confirmation',
                    'RSI favorable'
                ],
                'timestamp': datetime.now().isoformat()
            }
            
            emit('ai_analysis_update', ai_analysis)
            
        except Exception as e:
            logger.error(f"Errore request_ai_analysis: {e}")
            emit('error', {'message': str(e)})

# Funzioni helper per inviare updates dal backend
def broadcast_bot_update(socketio, status_data):
    """Invia update bot a tutti i client connessi"""
    socketio.emit('bot_status_update', status_data, room='bot_updates')

def broadcast_market_update(socketio, market_data):
    """Invia update mercato a tutti i client"""
    socketio.emit('market_data_update', market_data, room='market_updates')

def broadcast_ai_update(socketio, ai_data):
    """Invia update AI a tutti i client"""
    socketio.emit('ai_analysis_update', ai_data, room='ai_updates')

def broadcast_trade_update(socketio, trade_data):
    """Invia update trade a tutti i client"""
    socketio.emit('trade_update', trade_data, room='trade_updates')

print("✅ WebSocket events registrati per real-time communication")