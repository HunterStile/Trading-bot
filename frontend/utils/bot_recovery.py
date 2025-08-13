#!/usr/bin/env python3
"""
Bot Recovery Manager
Gestisce il recovery automatico del bot al riavvio
"""

import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Import del bot state manager
from .bot_state import BotStateManager

class BotRecoveryManager:
    """Gestisce il recovery automatico del bot"""
    
    def __init__(self, trading_wrapper, state_manager: BotStateManager = None):
        self.trading_wrapper = trading_wrapper
        self.state_manager = state_manager or BotStateManager()
        self.recovery_active = False
        self.logger = logging.getLogger('BotRecovery')
        
        # Setup logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def start_recovery_check(self):
        """Avvia il controllo di recovery in background"""
        if self.recovery_active:
            return
        
        self.recovery_active = True
        recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        recovery_thread.start()
        self.logger.info("🔄 Recovery Manager avviato")
    
    def stop_recovery_check(self):
        """Ferma il controllo di recovery"""
        self.recovery_active = False
        self.logger.info("⏹️ Recovery Manager fermato")
    
    def _recovery_loop(self):
        """Loop principale di recovery"""
        while self.recovery_active:
            try:
                # Controlla ogni 30 secondi
                time.sleep(30)
                
                if not self.recovery_active:
                    break
                
                # Sincronizza stato con posizioni reali
                self._sync_with_real_positions()
                
                # Controlla trailing stops
                self._check_trailing_stops()
                
                # Controlla strategie attive
                self._check_active_strategies()
                
            except Exception as e:
                self.logger.error(f"❌ Errore nel recovery loop: {e}")
                time.sleep(10)  # Aspetta meno in caso di errore
    
    def perform_initial_recovery(self) -> Dict[str, Any]:
        """Esegue recovery iniziale al startup del bot"""
        self.logger.info("🚀 Avvio recovery iniziale...")
        
        try:
            # Ottieni summary di recovery
            recovery_summary = self.state_manager.get_recovery_summary()
            
            # Controlla se il bot era attivo
            bot_config = self.state_manager.get_bot_state('bot_config')
            should_restart_bot = False
            
            if bot_config:
                was_running = bot_config.get('was_running', False)
                stopped_manually = bot_config.get('stopped_manually', False)
                auto_restart = bot_config.get('auto_restart', True)
                restart_attempted = bot_config.get('auto_restart_attempted', False)
                
                # Controlla se è passato abbastanza tempo dall'ultimo tentativo
                last_attempt = bot_config.get('restart_attempt_time')
                enough_time_passed = True
                
                if last_attempt:
                    from datetime import datetime, timedelta
                    try:
                        last_time = datetime.fromisoformat(last_attempt)
                        enough_time_passed = (datetime.now() - last_time) > timedelta(minutes=2)
                    except:
                        enough_time_passed = True
                
                # Riavvia solo se:
                # 1. Era in esecuzione
                # 2. Non è stato fermato manualmente
                # 3. Auto-restart è abilitato
                # 4. Non è già stato tentato il riavvio (o è passato abbastanza tempo)
                # 5. È passato abbastanza tempo dall'ultimo tentativo
                if (was_running and not stopped_manually and auto_restart and 
                    (not restart_attempted or enough_time_passed)):
                    should_restart_bot = True
                    self.logger.info("🔄 Bot era attivo prima del crash - preparazione auto-restart")
                elif restart_attempted and not enough_time_passed:
                    self.logger.info("⏰ Auto-restart già tentato di recente, skip")
            
            if not recovery_summary['needs_recovery'] and not should_restart_bot:
                self.logger.info("✅ Nessun recovery necessario")
                return {'success': True, 'message': 'Nessun recovery necessario'}
            
            # Ottieni posizioni reali da Bybit
            real_positions = self._get_real_positions()
            
            # Sincronizza stato
            self.state_manager.cleanup_closed_positions(real_positions)
            
            # Recovery di strategie attive
            recovered_strategies = self._recover_active_strategies(real_positions)
            
            # Recovery di trailing stops
            recovered_trailing = self._recover_trailing_stops(real_positions)
            
            # Auto-restart del bot se necessario
            bot_restarted = False
            if should_restart_bot:
                bot_restarted = self._auto_restart_bot(bot_config)
            
            # Avvia monitoraggio continuo
            self.start_recovery_check()
            
            recovery_result = {
                'success': True,
                'message': 'Recovery completato con successo',
                'recovered_strategies': recovered_strategies,
                'recovered_trailing_stops': recovered_trailing,
                'active_positions': len(real_positions),
                'bot_restarted': bot_restarted,
                'bot_config': bot_config if should_restart_bot else None
            }
            
            if bot_restarted:
                self.logger.info(f"✅ Recovery completato con auto-restart: {len(recovered_strategies)} strategie, {len(recovered_trailing)} trailing stops, bot riavviato")
            else:
                self.logger.info(f"✅ Recovery completato: {len(recovered_strategies)} strategie, {len(recovered_trailing)} trailing stops")
            
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"❌ Errore durante recovery iniziale: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_real_positions(self) -> List[Dict[str, Any]]:
        """Ottieni posizioni reali da Bybit"""
        try:
            # Usa l'API wrapper per ottenere posizioni
            from pybit.unified_trading import HTTP
            import os
            
            session = HTTP(
                testnet=False,
                api_key=os.getenv('BYBIT_API_KEY'),
                api_secret=os.getenv('BYBIT_API_SECRET'),
            )
            
            positions = []
            
            # Controlla tutte le categorie
            for settle_coin in ['USDT', 'BTC', 'ETH']:
                try:
                    response = session.get_positions(category="linear", settleCoin=settle_coin)
                    if response['retCode'] == 0:
                        for pos in response['result']['list']:
                            if float(pos.get('size', 0)) > 0:
                                positions.append({
                                    'symbol': pos['symbol'],
                                    'side': pos['side'],
                                    'size': float(pos['size']),
                                    'avgPrice': float(pos['avgPrice']),
                                    'markPrice': float(pos['markPrice']),
                                    'unrealisedPnl': float(pos['unrealisedPnl']),
                                    'category': f'linear-{settle_coin}'
                                })
                except Exception as e:
                    self.logger.warning(f"⚠️ Errore nel recupero posizioni {settle_coin}: {e}")
            
            # Controlla inverse
            try:
                response = session.get_positions(category="inverse")
                if response['retCode'] == 0:
                    for pos in response['result']['list']:
                        if float(pos.get('size', 0)) > 0:
                            positions.append({
                                'symbol': pos['symbol'],
                                'side': pos['side'],
                                'size': float(pos['size']),
                                'avgPrice': float(pos['avgPrice']),
                                'markPrice': float(pos['markPrice']),
                                'unrealisedPnl': float(pos['unrealisedPnl']),
                                'category': 'inverse'
                            })
            except Exception as e:
                self.logger.warning(f"⚠️ Errore nel recupero posizioni inverse: {e}")
            
            return positions
            
        except Exception as e:
            self.logger.error(f"❌ Errore nel recupero posizioni reali: {e}")
            return []
    
    def _recover_active_strategies(self, real_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recupera strategie attive"""
        strategies = self.state_manager.get_active_strategies()
        recovered = []
        
        for strategy in strategies:
            # Controlla se la posizione esiste ancora
            position_exists = any(
                pos['symbol'] == strategy['symbol'] and pos['side'] == strategy['side']
                for pos in real_positions
            )
            
            if position_exists:
                self.logger.info(f"🔄 Recupero strategia {strategy['symbol']} {strategy['side']}")
                recovered.append(strategy)
                
                # Re-applica la strategia se necessario
                self._reapply_strategy(strategy, real_positions)
            else:
                # Posizione non esiste più, disattiva strategia
                self.state_manager.deactivate_strategy(strategy['symbol'], strategy['side'])
                self.logger.info(f"🗑️ Strategia rimossa (posizione chiusa): {strategy['symbol']} {strategy['side']}")
        
        return recovered
    
    def _recover_trailing_stops(self, real_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recupera trailing stops"""
        trailing_stops = self.state_manager.get_trailing_stops()
        recovered = []
        
        for trail in trailing_stops:
            # Controlla se la posizione esiste ancora
            position_exists = any(
                pos['symbol'] == trail['symbol'] and pos['side'] == trail['side']
                for pos in real_positions
            )
            
            if position_exists:
                self.logger.info(f"🎯 Recupero trailing stop {trail['symbol']} {trail['side']}")
                recovered.append(trail)
            else:
                # Posizione non esiste più, rimuovi trailing stop
                self.state_manager.remove_trailing_stop(trail['symbol'], trail['side'])
                self.logger.info(f"🗑️ Trailing stop rimosso (posizione chiusa): {trail['symbol']} {trail['side']}")
        
        return recovered
    
    def _reapply_strategy(self, strategy: Dict[str, Any], real_positions: List[Dict[str, Any]]):
        """Re-applica una strategia"""
        try:
            # Trova la posizione corrispondente
            position = next(
                (pos for pos in real_positions 
                 if pos['symbol'] == strategy['symbol'] and pos['side'] == strategy['side']),
                None
            )
            
            if not position:
                return
            
            # Re-applica in base al tipo di strategia
            strategy_type = strategy['strategy_type']
            strategy_params = strategy['strategy_params']
            
            if strategy_type == 'trailing_stop':
                # Re-attiva trailing stop
                trail_amount = strategy_params.get('trail_amount', 0.005)  # Default 0.5%
                current_price = position['markPrice']
                
                if position['side'] == 'Buy':
                    stop_price = current_price * (1 - trail_amount)
                    best_price = current_price
                else:
                    stop_price = current_price * (1 + trail_amount)
                    best_price = current_price
                
                self.state_manager.save_trailing_stop(
                    strategy['symbol'], 
                    strategy['side'], 
                    stop_price, 
                    trail_amount, 
                    best_price
                )
                
                self.logger.info(f"🎯 Trailing stop riattivato: {strategy['symbol']} @ {stop_price}")
            
            elif strategy_type == 'take_profit':
                # Controlla se il take profit è ancora valido
                target_price = strategy_params.get('target_price')
                if target_price:
                    current_price = position['markPrice']
                    entry_price = position['avgPrice']
                    
                    # Verifica se il target è ancora raggiungibile
                    if position['side'] == 'Buy' and current_price < target_price:
                        self.logger.info(f"💰 Take profit ancora attivo: {strategy['symbol']} target {target_price}")
                    elif position['side'] == 'Sell' and current_price > target_price:
                        self.logger.info(f"💰 Take profit ancora attivo: {strategy['symbol']} target {target_price}")
                    else:
                        # Target già raggiunto o superato
                        self.logger.warning(f"⚠️ Take profit già raggiunto: {strategy['symbol']}")
            
        except Exception as e:
            self.logger.error(f"❌ Errore nel re-applicare strategia {strategy['symbol']}: {e}")
    
    def _sync_with_real_positions(self):
        """Sincronizza stato con posizioni reali"""
        try:
            real_positions = self._get_real_positions()
            self.state_manager.cleanup_closed_positions(real_positions)
        except Exception as e:
            self.logger.error(f"❌ Errore nella sincronizzazione: {e}")
    
    def _check_trailing_stops(self):
        """Controlla e aggiorna trailing stops"""
        trailing_stops = self.state_manager.get_trailing_stops()
        closed_positions = False
        
        for trail in trailing_stops:
            try:
                # Ottieni prezzo corrente
                current_price = self._get_current_price(trail['symbol'])
                if not current_price:
                    continue
                
                symbol = trail['symbol']
                side = trail['side']
                current_stop = trail['current_stop_price']
                trail_amount = trail['trail_amount']
                best_price = trail['best_price']
                
                # Aggiorna trailing stop
                if side == 'Buy':
                    if current_price > best_price:
                        # Nuovo massimo, aggiorna trailing
                        new_stop = current_price * (1 - trail_amount)
                        if new_stop > current_stop:
                            self.state_manager.save_trailing_stop(
                                symbol, side, new_stop, trail_amount, current_price
                            )
                            self.logger.info(f"🎯 Trailing stop aggiornato {symbol}: {new_stop:.4f}")
                    elif current_price <= current_stop:
                        # Stop triggered
                        if self._execute_trailing_stop(symbol, side, current_price):
                            closed_positions = True
                else:  # Sell
                    if current_price < best_price:
                        # Nuovo minimo, aggiorna trailing
                        new_stop = current_price * (1 + trail_amount)
                        if new_stop < current_stop:
                            self.state_manager.save_trailing_stop(
                                symbol, side, new_stop, trail_amount, current_price
                            )
                            self.logger.info(f"🎯 Trailing stop aggiornato {symbol}: {new_stop:.4f}")
                    elif current_price >= current_stop:
                        # Stop triggered
                        if self._execute_trailing_stop(symbol, side, current_price):
                            closed_positions = True
                        
            except Exception as e:
                self.logger.error(f"❌ Errore nel controllo trailing stop {trail['symbol']}: {e}")
        
        return closed_positions
    
    def _check_active_strategies(self):
        """Controlla strategie attive"""
        strategies = self.state_manager.get_active_strategies()
        
        for strategy in strategies:
            try:
                # Implementa controlli specifici per tipo di strategia
                strategy_type = strategy['strategy_type']
                
                if strategy_type == 'take_profit':
                    self._check_take_profit(strategy)
                elif strategy_type == 'stop_loss':
                    self._check_stop_loss(strategy)
                    
            except Exception as e:
                self.logger.error(f"❌ Errore nel controllo strategia {strategy['symbol']}: {e}")
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Ottieni prezzo corrente di un simbolo"""
        try:
            # Usa la funzione esistente del bot
            from Alert import vedi_prezzo_moneta
            price = vedi_prezzo_moneta('linear', symbol)
            return float(price) if price else None
        except Exception as e:
            self.logger.error(f"❌ Errore nel recupero prezzo {symbol}: {e}")
            return None
    
    def _execute_trailing_stop(self, symbol: str, side: str, trigger_price: float):
        """Esegue trailing stop"""
        try:
            self.logger.info(f"🚨 Trailing stop triggered: {symbol} {side} @ {trigger_price}")
            
            # Trova il trade ID corrispondente
            trade_id = None
            active_trades = self.trading_wrapper.get_active_trades()
            
            for tid, trade_info in active_trades.items():
                if (trade_info.get('symbol') == symbol and 
                    trade_info.get('side') == side):
                    trade_id = tid
                    break
            
            # Se non trovato nei trade attivi, cerca nel database
            if not trade_id and self.trading_wrapper.current_session_id:
                try:
                    from .database import trading_db
                    trades = trading_db.get_trade_history(self.trading_wrapper.current_session_id, 100)
                    open_trades = [t for t in trades if t['status'] == 'OPEN' 
                                 and t['symbol'] == symbol and t['side'] == side]
                    if open_trades:
                        trade_id = open_trades[0]['trade_id']
                except Exception as e:
                    self.logger.error(f"Errore ricerca trade nel database: {e}")
            
            # Chiudi posizione
            if trade_id:
                result = self.trading_wrapper.close_position(
                    trade_id=trade_id,
                    price=trigger_price,
                    reason=f"TRAILING_STOP_{side}"
                )
                
                if result.get('success'):
                    self.logger.info(f"✅ Posizione chiusa via trailing stop: {symbol} {side}")
                else:
                    self.logger.error(f"❌ Errore chiusura trailing stop: {result.get('error')}")
                    return False
            else:
                self.logger.warning(f"⚠️ Trade ID non trovato per {symbol} {side}")
                # Prova a chiudere direttamente tramite Bybit API se disponibile
                # Per ora logga l'errore
                return False
            
            # Rimuovi trailing stop
            self.state_manager.remove_trailing_stop(symbol, side)
            
            # Disattiva strategia correlata
            self.state_manager.deactivate_strategy(symbol, side)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore nell'esecuzione trailing stop {symbol}: {e}")
            return False
    
    def _check_take_profit(self, strategy: Dict[str, Any]):
        """Controlla take profit"""
        # Implementa logica take profit
        pass
    
    def _check_stop_loss(self, strategy: Dict[str, Any]):
        """Controlla stop loss"""
        # Implementa logica stop loss
        pass

    def add_trailing_stop_to_position(self, symbol: str, side: str, trail_percentage: float = 0.5) -> Dict[str, Any]:
        """Aggiunge trailing stop a una posizione esistente"""
        try:
            # Verifica che la posizione esista
            real_positions = self._get_real_positions()
            position = next(
                (pos for pos in real_positions if pos['symbol'] == symbol and pos['side'] == side),
                None
            )
            
            if not position:
                return {'success': False, 'error': 'Posizione non trovata'}
            
            # Calcola trailing stop
            current_price = position['markPrice']
            trail_amount = trail_percentage / 100  # Converti percentuale
            
            if side == 'Buy':
                stop_price = current_price * (1 - trail_amount)
                best_price = current_price
            else:
                stop_price = current_price * (1 + trail_amount)
                best_price = current_price
            
            # Salva trailing stop
            self.state_manager.save_trailing_stop(symbol, side, stop_price, trail_amount, best_price)
            
            # Salva strategia
            self.state_manager.save_active_strategy(
                symbol=symbol,
                side=side,
                entry_price=position['avgPrice'],
                strategy_type='trailing_stop',
                strategy_params={
                    'trail_amount': trail_amount,
                    'initial_stop': stop_price
                },
                position_size=position['size']
            )
            
            self.logger.info(f"🎯 Trailing stop aggiunto: {symbol} {side} @ {stop_price:.4f} ({trail_percentage}%)")
            
            return {
                'success': True,
                'message': f'Trailing stop aggiunto: {trail_percentage}%',
                'stop_price': stop_price,
                'trail_amount': trail_percentage
            }
            
        except Exception as e:
            self.logger.error(f"❌ Errore nell'aggiunta trailing stop: {e}")
            return {'success': False, 'error': str(e)}
    
    def _auto_restart_bot(self, bot_config: Dict[str, Any]) -> bool:
        """Auto-riavvia il bot con la configurazione salvata"""
        try:
            self.logger.info("🚀 Riavvio automatico del bot...")
            
            # Marca immediatamente che il bot è stato processato per il recovery
            # per evitare loop infiniti
            bot_config['was_running'] = False  
            bot_config['auto_restart_attempted'] = True
            bot_config['restart_attempt_time'] = datetime.now().isoformat()
            self.state_manager.save_bot_state('bot_config', bot_config)
            
            # Usa threading per evitare deadlock
            import threading
            import time
            
            def restart_bot_delayed():
                time.sleep(5)  # Aspetta che il server sia completamente avviato
                
                try:
                    # Importa qui per evitare circular imports
                    import requests
                    
                    # Prepara i dati per l'API
                    bot_data = {
                        'symbol': bot_config.get('symbol', 'AVAXUSDT'),
                        'quantity': bot_config.get('quantity', 50),
                        'operation': bot_config.get('operation', 'true'),
                        'ema_period': bot_config.get('ema_period', 10),
                        'interval': bot_config.get('interval', 30),
                        'open_candles': bot_config.get('open_candles', 3),
                        'stop_candles': bot_config.get('stop_candles', 3),
                        'distance': bot_config.get('distance', 1)
                    }
                    
                    self.logger.info(f"📡 Tentativo riavvio bot con simbolo: {bot_data['symbol']}")
                    
                    # Richiesta di avvio del bot
                    response = requests.post(
                        'http://localhost:5000/api/bot/start',
                        json=bot_data,
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            self.logger.info(f"✅ Bot riavviato automaticamente con simbolo {bot_data['symbol']}")
                            
                            # Aggiorna stato finale
                            final_config = bot_config.copy()
                            final_config['auto_restart_successful'] = True
                            final_config['restart_success_time'] = datetime.now().isoformat()
                            self.state_manager.save_bot_state('bot_config', final_config)
                        else:
                            self.logger.error(f"❌ Errore nel riavvio bot: {result.get('error')}")
                    else:
                        self.logger.error(f"❌ Errore HTTP nel riavvio bot: {response.status_code}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Errore di connessione nel riavvio bot: {e}")
            
            # Avvia in thread separato
            restart_thread = threading.Thread(target=restart_bot_delayed, daemon=True)
            restart_thread.start()
            
            self.logger.info("🔄 Riavvio bot programmato (delay 5s)")
            return True  # Consideriamo successo la programmazione
            
        except Exception as e:
            self.logger.error(f"❌ Errore nell'auto-restart del bot: {e}")
            return False
