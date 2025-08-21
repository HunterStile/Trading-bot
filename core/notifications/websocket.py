#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Manager
=================

Gestisce tutte le comunicazioni WebSocket tra frontend e backend
"""

from flask_socketio import SocketIO, emit
from datetime import datetime
import logging
from typing import Dict, Any, Optional, Callable

class WebSocketManager:
    """
    Gestisce le comunicazioni WebSocket per il trading bot
    """
    
    def __init__(self, socketio: SocketIO, logger: Optional[logging.Logger] = None):
        """
        Inizializza il WebSocket Manager
        
        Args:
            socketio: Istanza Flask-SocketIO
            logger: Logger per il sistema
        """
        self.socketio = socketio
        self.logger = logger or logging.getLogger(__name__)
        
        # Registra gli event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """
        Registra tutti gli event handlers WebSocket
        """
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('Client connesso via WebSocket')
            emit('status', {'msg': 'Connesso al server di trading'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('Client disconnesso da WebSocket')
        
        @self.socketio.on('request_update')
        def handle_request_update():
            """Gestisce richieste di aggiornamento dal client"""
            try:
                # Qui potresti chiamare un callback per ottenere dati aggiornati
                self.emit_status_update("Aggiornamento richiesto dal client")
            except Exception as e:
                self.logger.error(f"Errore nell'aggiornamento richiesto: {e}")
                emit('error', {'message': str(e)})
    
    def emit_analysis_log(self, message: str, log_type: str = 'info'):
        """
        Emette log di analisi al frontend
        
        Args:
            message: Messaggio da inviare
            log_type: Tipo di log ('info', 'warning', 'error', 'success')
        """
        try:
            self.socketio.emit('analysis_log', {
                'message': message,
                'type': log_type,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Errore nell'emissione log: {e}")
    
    def emit_bot_update(self, data: Dict[str, Any]):
        """
        Emette aggiornamento generale del bot
        
        Args:
            data: Dati di aggiornamento
        """
        try:
            update_data = {
                'timestamp': datetime.now().isoformat(),
                **data
            }
            self.socketio.emit('bot_update', update_data)
        except Exception as e:
            self.logger.error(f"Errore nell'emissione aggiornamento bot: {e}")
    
    def emit_trade_notification(self, trade_data: Dict[str, Any]):
        """
        Emette notifica di trade (apertura/chiusura)
        
        Args:
            trade_data: Dati del trade
        """
        try:
            notification_data = {
                'timestamp': datetime.now().isoformat(),
                **trade_data
            }
            self.socketio.emit('trade_notification', notification_data)
        except Exception as e:
            self.logger.error(f"Errore nell'emissione notifica trade: {e}")
    
    def emit_price_update(self, symbol: str, price: float):
        """
        Emette aggiornamento prezzo
        
        Args:
            symbol: Simbolo della coppia
            price: Prezzo corrente
        """
        try:
            self.socketio.emit('price_update', {
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Errore nell'emissione aggiornamento prezzo: {e}")
    
    def emit_error(self, error_message: str, error_data: Optional[Dict] = None):
        """
        Emette errore al frontend
        
        Args:
            error_message: Messaggio di errore
            error_data: Dati aggiuntivi dell'errore
        """
        try:
            error_payload = {
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
            if error_data:
                error_payload.update(error_data)
            
            self.socketio.emit('bot_error', error_payload)
        except Exception as e:
            self.logger.error(f"Errore nell'emissione errore: {e}")
    
    def emit_status_update(self, message: str, status_data: Optional[Dict] = None):
        """
        Emette aggiornamento di stato generale
        
        Args:
            message: Messaggio di stato
            status_data: Dati aggiuntivi di stato
        """
        try:
            payload = {
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            if status_data:
                payload.update(status_data)
            
            self.socketio.emit('status_update', payload)
        except Exception as e:
            self.logger.error(f"Errore nell'emissione stato: {e}")
    
    def broadcast_message(self, event: str, data: Dict[str, Any]):
        """
        Invia messaggio broadcast a tutti i client connessi
        
        Args:
            event: Nome dell'evento
            data: Dati da inviare
        """
        try:
            self.socketio.emit(event, data)
        except Exception as e:
            self.logger.error(f"Errore nel broadcast {event}: {e}")
    
    def emit_to_room(self, room: str, event: str, data: Dict[str, Any]):
        """
        Invia messaggio a una room specifica
        
        Args:
            room: Nome della room
            event: Nome dell'evento
            data: Dati da inviare
        """
        try:
            self.socketio.emit(event, data, room=room)
        except Exception as e:
            self.logger.error(f"Errore nell'invio a room {room}: {e}")
