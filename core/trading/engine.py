#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Engine
==============

Motore principale del trading bot che gestisce:
- Ciclo di trading principale
- Analisi di mercato
- Gestione posizioni
- Segnali di trading
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import logging

# Import delle funzioni esistenti (mantengo temporaneamente per compatibilità)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from trading_functions import (
        vedi_prezzo_moneta, get_kline_data, 
        analizza_prezzo_sopra_media, controlla_candele_sopra_ema,
        controlla_candele_sotto_ema, media_esponenziale
    )
except ImportError as e:
    print(f"Errore importazione trading_functions: {e}")

class TradingEngine:
    """
    Motore principale del trading bot che coordina tutte le operazioni
    """
    
    def __init__(self, 
                 trading_wrapper=None, 
                 trading_db=None, 
                 socketio=None,
                 logger=None):
        """
        Inizializza il Trading Engine
        
        Args:
            trading_wrapper: Wrapper per operazioni di trading
            trading_db: Database per logging
            socketio: WebSocket per comunicazioni real-time
            logger: Logger per il sistema
        """
        self.trading_wrapper = trading_wrapper
        self.trading_db = trading_db
        self.socketio = socketio
        self.logger = logger or logging.getLogger(__name__)
        
        # Stato del bot
        self.is_running = False
        self.stop_flag = False
        self.bot_thread = None
        
        # Configurazione di trading
        self.config = {}
        
        # Callbacks per eventi
        self.callbacks = {
            'on_analysis': [],
            'on_signal': [],
            'on_trade_open': [],
            'on_trade_close': [],
            'on_error': []
        }
    
    def configure(self, config: Dict[str, Any]):
        """
        Configura il trading engine
        
        Args:
            config: Dizionario con configurazione di trading
        """
        self.config = config.copy()
        self.logger.info(f"Trading Engine configurato per {config.get('symbol', 'N/A')}")
    
    def add_callback(self, event: str, callback: Callable):
        """
        Aggiunge callback per eventi specifici
        
        Args:
            event: Nome dell'evento ('on_analysis', 'on_signal', etc.)
            callback: Funzione da chiamare
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def emit_event(self, event: str, data: Dict[str, Any]):
        """
        Emette un evento e chiama tutti i callbacks registrati
        
        Args:
            event: Nome dell'evento
            data: Dati dell'evento
        """
        # Chiama callbacks registrati
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Errore nel callback {event}: {e}")
        
        # Emetti via WebSocket se disponibile
        if self.socketio:
            self.socketio.emit(event, data)
    
    def start(self) -> bool:
        """
        Avvia il trading engine
        
        Returns:
            True se avviato con successo, False altrimenti
        """
        if self.is_running:
            self.logger.warning("Trading Engine già in esecuzione")
            return False
        
        if not self.config:
            self.logger.error("Trading Engine non configurato")
            return False
        
        try:
            self.is_running = True
            self.stop_flag = False
            
            # Avvia il thread principale
            self.bot_thread = threading.Thread(target=self._trading_loop, daemon=True)
            self.bot_thread.start()
            
            self.logger.info("Trading Engine avviato con successo")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nell'avvio del Trading Engine: {e}")
            self.is_running = False
            return False
    
    def stop(self):
        """
        Ferma il trading engine
        """
        self.stop_flag = True
        self.is_running = False
        self.logger.info("Trading Engine fermato")
    
    def _trading_loop(self):
        """
        Loop principale del trading (estratto da run_trading_bot)
        """
        try:
            # Setup iniziale
            self._setup_session()
            
            # Loop principale
            while not self.stop_flag and self.is_running:
                try:
                    # Analisi di mercato
                    market_data = self._analyze_market()
                    
                    # Controlla posizioni esistenti
                    active_trades = self._get_active_trades()
                    
                    if not active_trades:
                        # Analisi per apertura posizioni
                        self._analyze_entry_conditions(market_data)
                    else:
                        # Analisi per chiusura posizioni
                        self._analyze_exit_conditions(active_trades, market_data)
                    
                    # Emetti aggiornamento
                    self._emit_status_update(market_data)
                    
                except Exception as loop_error:
                    self.logger.error(f"Errore nel ciclo di trading: {loop_error}")
                    self.emit_event('on_error', {
                        'error': str(loop_error),
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Attendi prossimo ciclo
                time.sleep(10)
                
        except Exception as e:
            self.logger.error(f"Errore fatale nel trading loop: {e}")
            self.is_running = False
    
    def _setup_session(self):
        """
        Setup iniziale della sessione di trading
        """
        if not self.trading_wrapper or not self.trading_db:
            return
        
        # Logic per setup sessione (estratta da app.py)
        if self.config.get('current_session_id'):
            # Usa sessione esistente
            self.trading_wrapper.set_session(self.config['current_session_id'])
            self.trading_wrapper.sync_with_database()
            self.logger.info(f"Continuando sessione esistente: {self.config['current_session_id']}")
        else:
            # Crea nuova sessione
            session_id = self._create_new_session()
            self.config['current_session_id'] = session_id
            self.trading_wrapper.set_session(session_id)
    
    def _create_new_session(self) -> str:
        """
        Crea una nuova sessione di trading
        
        Returns:
            ID della sessione creata
        """
        strategy_config = {
            'symbol': self.config.get('symbol'),
            'ema_period': self.config.get('ema_period'),
            'interval': self.config.get('interval'),
            'open_candles': self.config.get('open_candles'),
            'stop_candles': self.config.get('stop_candles'),
            'distance': self.config.get('distance'),
            'quantity': self.config.get('quantity'),
            'operation': self.config.get('operation')
        }
        
        # Ottieni saldo iniziale
        try:
            from trading_functions import mostra_saldo
            balance_response = mostra_saldo()
            initial_balance = balance_response.get('total_equity', 0) if balance_response else 0
        except Exception as e:
            self.logger.error(f"Errore nel recupero saldo iniziale: {e}")
            initial_balance = 0
        
        session_id = self.trading_db.start_session(
            self.config.get('symbol'), 
            strategy_config, 
            initial_balance
        )
        
        self.trading_db.log_event(
            "BOT_START", 
            "SYSTEM", 
            f"Bot avviato per {self.config.get('symbol')}", 
            strategy_config,
            session_id=session_id
        )
        
        self.logger.info(f"Nuova sessione creata: {session_id}")
        return session_id
    
    def _analyze_market(self) -> Dict[str, Any]:
        """
        Analizza il mercato e restituisce dati
        
        Returns:
            Dizionario con dati di mercato e analisi
        """
        symbol = self.config.get('symbol')
        if not symbol:
            return {}
        
        try:
            # Ottieni prezzo corrente
            current_price = vedi_prezzo_moneta('linear', symbol)
            
            # Ottieni dati delle candele
            interval = self.config.get('interval', 30)
            klines = get_kline_data('linear', symbol, interval, 200)
            
            market_data = {
                'symbol': symbol,
                'current_price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
            if klines:
                # Analisi EMA
                ema_period = self.config.get('ema_period', 10)
                ema_analysis = analizza_prezzo_sopra_media('linear', symbol, interval, ema_period)
                
                if ema_analysis and len(ema_analysis) >= 3:
                    market_data.update({
                        'candles_above_ema': ema_analysis[0],
                        'distance_percent': ema_analysis[2],
                        'is_above_ema': ema_analysis[2] > 0
                    })
                
                # Calcola EMA attuale
                try:
                    ema_value = media_esponenziale('linear', symbol, interval, ema_period)
                    market_data['ema_value'] = ema_value
                except Exception as e:
                    self.logger.warning(f"Errore calcolo EMA: {e}")
                    market_data['ema_value'] = current_price
                
                # Controlla candele consecutive
                candles_above_result = controlla_candele_sopra_ema('linear', symbol, interval, ema_period)
                candles_below_result = controlla_candele_sotto_ema('linear', symbol, interval, ema_period)
                
                market_data.update({
                    'candles_above': candles_above_result[0] if candles_above_result else 0,
                    'candles_below': candles_below_result[0] if candles_below_result else 0
                })
            
            # Emetti evento di analisi
            self.emit_event('on_analysis', market_data)
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Errore nell'analisi di mercato: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_active_trades(self) -> Dict:
        """
        Ottieni trade attivi
        
        Returns:
            Dizionario con trade attivi
        """
        if not self.trading_wrapper:
            return {}
        
        return self.trading_wrapper.get_active_trades()
    
    def _analyze_entry_conditions(self, market_data: Dict[str, Any]):
        """
        Analizza condizioni per aprire nuove posizioni
        
        Args:
            market_data: Dati di mercato correnti
        """
        if not market_data or 'current_price' not in market_data:
            return
        
        symbol = self.config.get('symbol')
        operation = self.config.get('operation', True)  # True = Long, False = Short
        
        # Controlla condizioni di distanza
        distance_percent = market_data.get('distance_percent', 0)
        distance_ok = abs(distance_percent) <= self.config.get('distance', 1)
        
        candles_above = market_data.get('candles_above', 0)
        candles_below = market_data.get('candles_below', 0)
        is_above_ema = market_data.get('is_above_ema', False)
        
        self.logger.info(f"Analisi condizioni apertura per {symbol}")
        self.logger.info(f"Prezzo {'SOPRA' if is_above_ema else 'SOTTO'} EMA ({distance_percent:+.2f}%)")
        self.logger.info(f"Candele sopra/sotto EMA: {candles_above}/{candles_below}")
        
        # Analisi per LONG
        if operation:
            long_conditions = {
                'above_ema': is_above_ema,
                'enough_candles': candles_above >= self.config.get('open_candles', 3),
                'distance_ok': distance_ok
            }
            
            if all(long_conditions.values()):
                self._open_position('Buy', market_data, 'LONG_SIGNAL')
        
        # Analisi per SHORT
        else:
            short_conditions = {
                'below_ema': not is_above_ema,
                'enough_candles': candles_below >= self.config.get('open_candles', 3),
                'distance_ok': distance_ok
            }
            
            if all(short_conditions.values()):
                self._open_position('Sell', market_data, 'SHORT_SIGNAL')
    
    def _analyze_exit_conditions(self, active_trades: Dict, market_data: Dict[str, Any]):
        """
        Analizza condizioni per chiudere posizioni esistenti
        
        Args:
            active_trades: Trade attualmente attivi
            market_data: Dati di mercato correnti
        """
        candles_above = market_data.get('candles_above', 0)
        candles_below = market_data.get('candles_below', 0)
        stop_candles = self.config.get('stop_candles', 3)
        
        for trade_id, trade_info in active_trades.items():
            trade_side = trade_info['side']
            trade_symbol = trade_info.get('symbol', self.config.get('symbol'))
            
            self.logger.info(f"Analizzando posizione {trade_side} {trade_symbol}")
            
            # Condizioni di chiusura per LONG
            if trade_side == 'Buy':
                close_long = candles_below >= stop_candles
                if close_long:
                    self._close_position(trade_id, market_data, 'EMA_STOP_LONG')
            
            # Condizioni di chiusura per SHORT
            elif trade_side == 'Sell':
                close_short = candles_above >= stop_candles
                if close_short:
                    self._close_position(trade_id, market_data, 'EMA_STOP_SHORT')
    
    def _open_position(self, side: str, market_data: Dict[str, Any], signal: str):
        """
        Apre una nuova posizione
        
        Args:
            side: 'Buy' o 'Sell'
            market_data: Dati di mercato
            signal: Tipo di segnale
        """
        if not self.trading_wrapper:
            return
        
        symbol = self.config.get('symbol')
        quantity = self.config.get('quantity', 50)
        
        self.logger.info(f"Apertura posizione {side} per {symbol}")
        
        result = self.trading_wrapper.open_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            strategy_signal=signal
        )
        
        if result.get('success'):
            self.logger.info(f"Posizione {side} aperta con successo!")
            self.emit_event('on_trade_open', {
                'side': side,
                'symbol': symbol,
                'price': market_data.get('current_price'),
                'quantity': quantity,
                'timestamp': datetime.now().isoformat()
            })
        else:
            self.logger.error(f"Errore apertura {side}: {result.get('error')}")
    
    def _close_position(self, trade_id: str, market_data: Dict[str, Any], reason: str):
        """
        Chiude una posizione esistente
        
        Args:
            trade_id: ID del trade da chiudere
            market_data: Dati di mercato
            reason: Motivo della chiusura
        """
        if not self.trading_wrapper:
            return
        
        self.logger.info(f"Chiusura posizione {trade_id} per {reason}")
        
        result = self.trading_wrapper.close_position(
            trade_id=trade_id,
            reason=reason
        )
        
        if result.get('success'):
            self.logger.info(f"Posizione {trade_id} chiusa con successo!")
            self.emit_event('on_trade_close', {
                'trade_id': trade_id,
                'price': market_data.get('current_price'),
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
        else:
            self.logger.error(f"Errore chiusura {trade_id}: {result.get('error')}")
    
    def _emit_status_update(self, market_data: Dict[str, Any]):
        """
        Emette aggiornamento di stato
        
        Args:
            market_data: Dati di mercato correnti
        """
        active_trades = self._get_active_trades()
        
        status_data = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'market_data': market_data,
            'active_trades_count': len(active_trades),
            'session_id': self.config.get('current_session_id')
        }
        
        self.emit_event('bot_update', status_data)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Restituisce lo stato corrente del trading engine
        
        Returns:
            Dizionario con stato corrente
        """
        return {
            'is_running': self.is_running,
            'config': self.config.copy(),
            'active_trades': len(self._get_active_trades()) if self.trading_wrapper else 0,
            'session_id': self.config.get('current_session_id')
        }
