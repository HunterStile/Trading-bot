#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Service
===============

Service layer che coordina TradingEngine e notifiche
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .engine import TradingEngine
from ..notifications.websocket import WebSocketManager

class TradingService:
    """
    Service che coordina il trading engine con le notifiche
    """
    
    def __init__(self, 
                 trading_wrapper=None,
                 trading_db=None,
                 websocket_manager: Optional[WebSocketManager] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Inizializza il Trading Service
        
        Args:
            trading_wrapper: Wrapper per operazioni trading
            trading_db: Database per logging
            websocket_manager: Manager per WebSocket
            logger: Logger per il sistema
        """
        self.logger = logger or logging.getLogger(__name__)
        self.websocket_manager = websocket_manager
        
        # Crea il trading engine
        self.engine = TradingEngine(
            trading_wrapper=trading_wrapper,
            trading_db=trading_db,
            socketio=websocket_manager.socketio if websocket_manager else None,
            logger=self.logger
        )
        
        # Registra callbacks per eventi del trading engine
        self._setup_callbacks()
        
        # Stato del servizio
        self.bot_status = {
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
    
    def _setup_callbacks(self):
        """
        Configura i callbacks per gli eventi del trading engine
        """
        self.engine.add_callback('on_analysis', self._handle_analysis)
        self.engine.add_callback('on_trade_open', self._handle_trade_open)
        self.engine.add_callback('on_trade_close', self._handle_trade_close)
        self.engine.add_callback('on_error', self._handle_error)
        self.engine.add_callback('bot_update', self._handle_bot_update)
    
    def _handle_analysis(self, data: Dict[str, Any]):
        """
        Gestisce eventi di analisi di mercato
        
        Args:
            data: Dati dell'analisi
        """
        if not self.websocket_manager:
            return
        
        symbol = data.get('symbol', 'N/A')
        current_price = data.get('current_price', 0)
        ema_value = data.get('ema_value', 0)
        is_above_ema = data.get('is_above_ema', False)
        distance_percent = data.get('distance_percent', 0)
        
        # Log analisi
        self.websocket_manager.emit_analysis_log(
            f"🔍 Analizzando {symbol} - Prezzo: ${current_price:.4f}"
        )
        
        if ema_value:
            self.websocket_manager.emit_analysis_log(
                f"📈 EMA: ${ema_value:.4f}"
            )
            
        self.websocket_manager.emit_analysis_log(
            f"📍 Prezzo {'SOPRA' if is_above_ema else 'SOTTO'} EMA ({distance_percent:+.2f}%)"
        )
        
        # Aggiorna prezzo
        self.websocket_manager.emit_price_update(symbol, current_price)
    
    def _handle_trade_open(self, data: Dict[str, Any]):
        """
        Gestisce apertura trade
        
        Args:
            data: Dati del trade aperto
        """
        self.bot_status['total_trades'] += 1
        self.bot_status['last_update'] = datetime.now().isoformat()
        
        if self.websocket_manager:
            self.websocket_manager.emit_analysis_log(
                f"✅ Posizione {data.get('side')} aperta per {data.get('symbol')}!",
                'success'
            )
            self.websocket_manager.emit_trade_notification({
                'type': 'POSITION_OPENED',
                **data
            })
    
    def _handle_trade_close(self, data: Dict[str, Any]):
        """
        Gestisce chiusura trade
        
        Args:
            data: Dati del trade chiuso
        """
        self.bot_status['last_update'] = datetime.now().isoformat()
        
        if self.websocket_manager:
            self.websocket_manager.emit_analysis_log(
                f"✅ Posizione chiusa: {data.get('reason')}!",
                'success'
            )
            self.websocket_manager.emit_trade_notification({
                'type': 'POSITION_CLOSED',
                **data
            })
    
    def _handle_error(self, data: Dict[str, Any]):
        """
        Gestisce errori
        
        Args:
            data: Dati dell'errore
        """
        error_msg = data.get('error', 'Errore sconosciuto')
        self.logger.error(f"Trading error: {error_msg}")
        
        if self.websocket_manager:
            self.websocket_manager.emit_analysis_log(
                f"❌ Errore: {error_msg}",
                'error'
            )
            self.websocket_manager.emit_error(error_msg, data)
    
    def _handle_bot_update(self, data: Dict[str, Any]):
        """
        Gestisce aggiornamenti generali del bot
        
        Args:
            data: Dati di aggiornamento
        """
        # Aggiorna stato locale
        market_data = data.get('market_data', {})
        if market_data:
            symbol = market_data.get('symbol')
            if symbol:
                self.bot_status['symbol'] = symbol
        
        self.bot_status['last_update'] = data.get('timestamp')
        
        # Emetti aggiornamento via WebSocket
        if self.websocket_manager:
            update_data = {
                'status': 'running' if self.bot_status['running'] else 'stopped',
                'bot_status': self.bot_status.copy(),
                **data
            }
            self.websocket_manager.emit_bot_update(update_data)
    
    def start_bot(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avvia il bot di trading
        
        Args:
            config: Configurazione del bot
            
        Returns:
            Risultato dell'operazione
        """
        if self.bot_status['running']:
            return {'success': False, 'error': 'Il bot è già in esecuzione'}
        
        try:
            # Aggiorna configurazione
            self.bot_status.update(config)
            self.bot_status['running'] = True
            self.bot_status['last_update'] = datetime.now().isoformat()
            
            # Configura e avvia il trading engine
            engine_config = {
                'symbol': config.get('symbol'),
                'quantity': config.get('quantity'),
                'operation': config.get('operation'),
                'ema_period': config.get('ema_period'),
                'interval': config.get('interval'),
                'open_candles': config.get('open_candles'),
                'stop_candles': config.get('stop_candles'),
                'distance': config.get('distance'),
                'current_session_id': self.bot_status.get('current_session_id')
            }
            
            self.engine.configure(engine_config)
            
            if self.engine.start():
                # Aggiorna session ID dal trading engine
                engine_status = self.engine.get_status()
                self.bot_status['current_session_id'] = engine_status.get('session_id')
                
                self.logger.info("Trading Service avviato con successo")
                return {'success': True, 'message': 'Bot avviato con successo'}
            else:
                self.bot_status['running'] = False
                return {'success': False, 'error': 'Errore nell\'avvio del trading engine'}
                
        except Exception as e:
            self.bot_status['running'] = False
            self.logger.error(f"Errore nell'avvio del Trading Service: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_bot(self) -> Dict[str, Any]:
        """
        Ferma il bot di trading
        
        Returns:
            Risultato dell'operazione
        """
        try:
            self.engine.stop()
            self.bot_status['running'] = False
            self.bot_status['last_update'] = datetime.now().isoformat()
            
            # Reset session data se necessario
            if self.bot_status.get('current_session_id'):
                # Qui potresti chiudere la sessione nel database
                pass
            
            self.logger.info("Trading Service fermato")
            return {'success': True, 'message': 'Bot fermato con successo'}
            
        except Exception as e:
            self.logger.error(f"Errore nel fermare il Trading Service: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Restituisce lo stato corrente del servizio
        
        Returns:
            Stato del servizio
        """
        engine_status = self.engine.get_status()
        
        return {
            'bot_status': self.bot_status.copy(),
            'engine_status': engine_status,
            'is_running': self.bot_status['running'] and engine_status['is_running']
        }
    
    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggiorna le impostazioni del bot
        
        Args:
            settings: Nuove impostazioni
            
        Returns:
            Risultato dell'operazione
        """
        try:
            self.bot_status.update(settings)
            self.bot_status['last_update'] = datetime.now().isoformat()
            
            # Se il bot è in esecuzione, aggiorna anche la configurazione del engine
            if self.bot_status['running']:
                engine_config = {
                    'symbol': settings.get('symbol', self.bot_status['symbol']),
                    'quantity': settings.get('quantity', self.bot_status['quantity']),
                    'operation': settings.get('operation', self.bot_status['operation']),
                    'ema_period': settings.get('ema_period', self.bot_status['ema_period']),
                    'interval': settings.get('interval', self.bot_status['interval']),
                    'open_candles': settings.get('open_candles', self.bot_status['open_candles']),
                    'stop_candles': settings.get('stop_candles', self.bot_status['stop_candles']),
                    'distance': settings.get('distance', self.bot_status['distance'])
                }
                self.engine.configure(engine_config)
            
            return {'success': True, 'message': 'Impostazioni aggiornate'}
            
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento impostazioni: {e}")
            return {'success': False, 'error': str(e)}
