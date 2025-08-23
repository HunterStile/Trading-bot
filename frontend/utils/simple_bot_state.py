#!/usr/bin/env python3
"""
Enhanced Bot State Manager
Salva stato completo del bot incluse posizioni attive
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

class EnhancedBotState:
    """Gestisce stato completo del bot incluse posizioni attive"""
    
    def __init__(self, state_file: str = None):
        if state_file is None:
            state_file = Path(__file__).parent.parent / "data" / "enhanced_bot_state.json"
        
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(exist_ok=True)
    
    def save_bot_running_state(self, bot_status: Dict[str, Any], active_trades: Dict = None, trading_wrapper=None):
        """Salva stato completo quando il bot è in esecuzione"""
        
        # Ottieni posizioni attive se non fornite
        if active_trades is None and trading_wrapper:
            try:
                active_trades = trading_wrapper.get_active_trades()
            except Exception as e:
                print(f"Errore nel recupero posizioni attive: {e}")
                active_trades = {}
        
        # Determina la fase operativa del bot
        operational_phase = self._determine_operational_phase(active_trades or {})
        
        state_data = {
            # Configurazione base
            'is_running': True,
            'symbol': bot_status['symbol'],
            'quantity': bot_status['quantity'],
            'operation': bot_status['operation'],  # True = Long, False = Short
            'ema_period': bot_status['ema_period'],
            'interval': bot_status['interval'],
            'open_candles': bot_status['open_candles'],
            'stop_candles': bot_status['stop_candles'],
            'distance': bot_status['distance'],
            'category': bot_status['category'],
            
            # Stato sessione
            'current_session_id': bot_status.get('current_session_id'),
            'session_start_time': bot_status.get('session_start_time'),
            'total_trades': bot_status.get('total_trades', 0),
            'session_pnl': bot_status.get('session_pnl', 0),
            
            # NUOVO: Stato operativo
            'operational_phase': operational_phase,  # 'SEEKING_ENTRY' o 'MANAGING_POSITIONS'
            'active_trades': self._serialize_active_trades(active_trades or {}),
            'has_open_positions': len(active_trades or {}) > 0,
            
            # Metadati
            'last_save_time': datetime.now().isoformat(),
            'stopped_manually': False,  # Il bot era attivo quando salvato
            'crash_recovery_needed': False  # Sarà True solo in caso di crash
        }
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            print(f"💾 Stato salvato - Fase: {operational_phase}, Posizioni: {len(active_trades or {})}")
        except Exception as e:
            print(f"Errore nel salvataggio stato: {e}")
    
    def save_bot_crashed_state(self, bot_status: Dict[str, Any] = None, active_trades: Dict = None):
        """Salva stato quando il bot crasha - marca per recovery"""
        try:
            # Leggi stato esistente o crea nuovo
            current_state = self.get_bot_state() or {}
            
            # Aggiorna con info di crash
            current_state.update({
                'is_running': False,
                'stopped_manually': False,
                'crash_recovery_needed': True,  # IMPORTANTE: marca il crash
                'crash_time': datetime.now().isoformat(),
                'last_save_time': datetime.now().isoformat()
            })
            
            # Aggiorna posizioni se fornite
            if active_trades is not None:
                current_state['active_trades'] = self._serialize_active_trades(active_trades)
                current_state['has_open_positions'] = len(active_trades) > 0
                current_state['operational_phase'] = self._determine_operational_phase(active_trades)
            
            # Aggiorna bot_status se fornito
            if bot_status:
                current_state.update({
                    'current_session_id': bot_status.get('current_session_id'),
                    'total_trades': bot_status.get('total_trades', 0),
                    'session_pnl': bot_status.get('session_pnl', 0)
                })
            
            with open(self.state_file, 'w') as f:
                json.dump(current_state, f, indent=2)
            print(f"💾 Crash state salvato - Fase: {current_state.get('operational_phase', 'UNKNOWN')}")
                
        except Exception as e:
            print(f"Errore nel salvataggio crash: {e}")
    
    def save_bot_stopped_state(self):
        """Salva lo stato quando il bot viene fermato manualmente"""
        try:
            # Leggi stato esistente
            current_state = self.get_bot_state()
            if current_state:
                current_state['is_running'] = False
                current_state['stopped_manually'] = True
                current_state['crash_recovery_needed'] = False  # Non è un crash
                current_state['stop_time'] = datetime.now().isoformat()
                
                with open(self.state_file, 'w') as f:
                    json.dump(current_state, f, indent=2)
            else:
                # Crea stato minimo se non esiste
                state_data = {
                    'is_running': False,
                    'stopped_manually': True,
                    'crash_recovery_needed': False,
                    'stop_time': datetime.now().isoformat(),
                    'operational_phase': 'STOPPED'
                }
                with open(self.state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
                    
        except Exception as e:
            print(f"Errore nel salvataggio stop: {e}")
    
    def get_bot_state(self) -> Optional[Dict[str, Any]]:
        """Recupera lo stato salvato"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Errore nel recupero stato: {e}")
            return None
    
    def should_auto_restart(self) -> bool:
        """Determina se il bot dovrebbe riavviarsi automaticamente"""
        state = self.get_bot_state()
        if not state:
            return False
        
        # Riavvia solo se:
        # 1. Era in esecuzione
        # 2. Non è stato fermato manualmente
        # 3. È un crash che necessita recovery
        was_running = state.get('is_running', False)
        stopped_manually = state.get('stopped_manually', False)
        needs_crash_recovery = state.get('crash_recovery_needed', False)
        
        return (was_running or needs_crash_recovery) and not stopped_manually
    
    def get_operational_phase(self) -> str:
        """Ottieni la fase operativa salvata"""
        state = self.get_bot_state()
        return state.get('operational_phase', 'SEEKING_ENTRY') if state else 'SEEKING_ENTRY'
    
    def has_open_positions_to_manage(self) -> bool:
        """Controlla se ci sono posizioni aperte da gestire"""
        state = self.get_bot_state()
        return state.get('has_open_positions', False) if state else False
    
    def get_saved_active_trades(self) -> Dict:
        """Recupera le posizioni attive salvate"""
        state = self.get_bot_state()
        if not state:
            return {}
        
        saved_trades = state.get('active_trades', {})
        return self._deserialize_active_trades(saved_trades)
    
    def clear_state(self):
        """Pulisce il file di stato"""
        try:
            if self.state_file.exists():
                os.remove(self.state_file)
            print("💾 Stato di recovery cancellato")
        except Exception as e:
            print(f"Errore nella pulizia stato: {e}")
    
    def get_recovery_config(self) -> Optional[Dict[str, Any]]:
        """Ottieni configurazione per il recovery con fase operativa"""
        state = self.get_bot_state()
        if not state or not self.should_auto_restart():
            return None
        
        recovery_config = {
            'symbol': state.get('symbol', 'AVAXUSDT'),
            'quantity': state.get('quantity', 50),
            'operation': state.get('operation', True),
            'ema_period': state.get('ema_period', 10),
            'interval': state.get('interval', 30),
            'open_candles': state.get('open_candles', 3),
            'stop_candles': state.get('stop_candles', 3),
            'distance': state.get('distance', 1),
            'category': state.get('category', 'linear'),
            
            # Info sessione precedente
            'previous_session_id': state.get('current_session_id'),
            'previous_trades': state.get('total_trades', 0),
            'session_pnl': state.get('session_pnl', 0),
            
            # NUOVO: Info fase operativa
            'operational_phase': state.get('operational_phase', 'SEEKING_ENTRY'),
            'has_open_positions': state.get('has_open_positions', False),
            'active_trades': state.get('active_trades', {}),
            'crash_recovery': state.get('crash_recovery_needed', False)
        }
        
        return recovery_config
    
    def _determine_operational_phase(self, active_trades: Dict) -> str:
        """Determina la fase operativa del bot"""
        if len(active_trades) > 0:
            return 'MANAGING_POSITIONS'
        else:
            return 'SEEKING_ENTRY'
    
    def _serialize_active_trades(self, active_trades: Dict) -> Dict:
        """Serializza le posizioni attive per il salvataggio"""
        serialized = {}
        for trade_id, trade_info in active_trades.items():
            serialized[str(trade_id)] = {
                'side': trade_info.get('side'),
                'symbol': trade_info.get('symbol'),
                'quantity': trade_info.get('quantity'),
                'entry_price': trade_info.get('entry_price'),
                'open_time': trade_info.get('open_time'),
                'unrealized_pnl': trade_info.get('unrealized_pnl'),
                # Aggiungi altri campi necessari
                'trade_type': trade_info.get('trade_type', 'MARKET')
            }
        return serialized
    
    def _deserialize_active_trades(self, saved_trades: Dict) -> Dict:
        """Deserializza le posizioni attive dal salvataggio"""
        deserialized = {}
        for trade_id, trade_info in saved_trades.items():
            deserialized[trade_id] = {
                'side': trade_info.get('side'),
                'symbol': trade_info.get('symbol'),
                'quantity': trade_info.get('quantity'),
                'entry_price': trade_info.get('entry_price'),
                'open_time': trade_info.get('open_time'),
                'unrealized_pnl': trade_info.get('unrealized_pnl'),
                'trade_type': trade_info.get('trade_type', 'MARKET')
            }
        return deserialized
    
    def mark_successful_recovery(self):
        """Marca un recovery come completato con successo"""
        try:
            current_state = self.get_bot_state()
            if current_state:
                current_state['crash_recovery_needed'] = False
                current_state['last_successful_recovery'] = datetime.now().isoformat()
                
                with open(self.state_file, 'w') as f:
                    json.dump(current_state, f, indent=2)
                print("✅ Recovery completato con successo")
        except Exception as e:
            print(f"Errore nella marcatura recovery: {e}")
    
    def save_state_with_position(self, bot_status: dict, operational_phase: str, trading_wrapper=None):
        """Salva lo stato con posizione aperta e fase operativa specifica"""
        try:
            # Ottieni posizioni attive dal trading wrapper
            active_trades = {}
            has_positions = False
            
            if trading_wrapper:
                try:
                    trades = trading_wrapper.get_active_trades()
                    active_trades = self._serialize_active_trades(trades) if trades else {}
                    has_positions = len(active_trades) > 0
                except Exception as e:
                    print(f"⚠️ Errore nell'ottenere posizioni attive: {e}")
            
            # Normalizza la fase operativa per coerenza
            normalized_phase = self._normalize_operational_phase(operational_phase, has_positions)
            
            # Crea stato esteso
            enhanced_state = {
                'last_save_time': datetime.now().isoformat(),
                'operational_phase': normalized_phase,
                'has_open_positions': has_positions,
                'active_trades': active_trades,
                'active_trades_count': len(active_trades),
                'is_running': bot_status.get('running', True),
                'stopped_manually': False,  # Non è uno stop manuale se stiamo aprendo posizioni
                'crash_recovery_needed': False,  # Reset flag recovery
                
                # Config bot per recovery
                'symbol': bot_status.get('symbol', 'AVAXUSDT'),
                'quantity': bot_status.get('quantity', 50),
                'operation': bot_status.get('operation', True),
                'ema_period': bot_status.get('ema_period', 10),
                'interval': bot_status.get('interval', 30),
                'open_candles': bot_status.get('open_candles', 3),
                'stop_candles': bot_status.get('stop_candles', 3),
                'distance': bot_status.get('distance', 1.0),
                'category': bot_status.get('category', 'linear'),
                
                # Session info
                'current_session_id': bot_status.get('current_session_id'),
                'session_start_time': bot_status.get('session_start_time'),
                'total_trades': bot_status.get('total_trades', 0),
                'session_pnl': bot_status.get('session_pnl', 0)
            }
            
            # Salva nel file
            with open(self.state_file, 'w') as f:
                json.dump(enhanced_state, f, indent=2)
            
            print(f"💾 Stato salvato - Fase: {operational_phase}, Posizioni: {len(active_trades)}")
            
        except Exception as e:
            print(f"❌ Errore nel salvare stato con posizione: {e}")
            # Fallback - salva almeno lo stato base
            self.save_bot_running_state(bot_status)
    
    def get_recovery_summary(self) -> Dict:
        """Ottieni un riassunto dello stato di recovery"""
        state = self.get_bot_state()
        if not state:
            return {'has_state': False}
        
        return {
            'has_state': True,
            'can_restart': self.should_auto_restart(),
            'operational_phase': state.get('operational_phase', 'UNKNOWN'),
            'has_open_positions': state.get('has_open_positions', False),
            'active_trades_count': len(state.get('active_trades', {})),
            'crash_recovery': state.get('crash_recovery_needed', False),
            'stopped_manually': state.get('stopped_manually', False),
            'last_save_time': state.get('last_save_time'),
            'session_id': state.get('current_session_id')
        }
    
    def _normalize_operational_phase(self, operational_phase: str, has_positions: bool) -> str:
        """Normalizza la fase operativa basata su posizioni reali"""
        # Se ci sono posizioni attive, deve essere una fase di gestione posizioni
        if has_positions:
            if operational_phase.upper() in ['IN_POSITION_LONG', 'IN_POSITION_SHORT', 'MANAGING_POSITIONS']:
                return operational_phase  # Mantieni il nome specifico se fornito
            else:
                return 'MANAGING_POSITIONS'  # Default per posizioni attive
        else:
            # Se non ci sono posizioni, deve essere seeking entry
            return 'SEEKING_ENTRY'
