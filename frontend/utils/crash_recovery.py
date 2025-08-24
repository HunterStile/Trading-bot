#!/usr/bin/env python3
"""
Advanced Crash Recovery System
Sistema avanzato per gestire il recovery del bot dopo crash
preservando lo stato operativo e le posizioni attive
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import traceback

from .simple_bot_state import EnhancedBotState


class CrashRecoveryManager:
    """Gestisce il recovery completo del bot dopo crash o riavvii inaspettati"""
    
    def __init__(self, state_manager: EnhancedBotState = None, trading_wrapper=None):
        self.state_manager = state_manager or EnhancedBotState()
        self.trading_wrapper = trading_wrapper
        self.recovery_log_file = Path(__file__).parent.parent / "data" / "recovery_log.json"
        self.recovery_log_file.parent.mkdir(exist_ok=True)
    
    def log_recovery_action(self, action: str, details: Dict = None, status: str = "INFO"):
        """Log delle azioni di recovery per debugging"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'status': status,
            'details': details or {},
            'session_info': self._get_session_info()
        }
        
        try:
            # Carica log esistente
            if self.recovery_log_file.exists():
                with open(self.recovery_log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Aggiungi nuovo log
            logs.append(log_entry)
            
            # Mantieni solo gli ultimi 100 log
            if len(logs) > 100:
                logs = logs[-100:]
            
            # Salva
            with open(self.recovery_log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Errore salvataggio recovery log: {e}")
    
    def _get_session_info(self) -> Dict:
        """Ottieni info sessione corrente per i log"""
        try:
            state = self.state_manager.get_bot_state()
            return {
                'session_id': state.get('current_session_id') if state else None,
                'operational_phase': state.get('operational_phase') if state else 'UNKNOWN'
            }
        except:
            return {'session_id': None, 'operational_phase': 'ERROR'}
    
    def check_crash_recovery_needed(self) -> Tuple[bool, Dict]:
        """
        Controlla se il bot necessita di crash recovery
        Returns: (needs_recovery, recovery_info)
        """
        try:
            self.log_recovery_action("CHECKING_CRASH_RECOVERY", status="START")
            
            # 1. Controlla stato salvato
            saved_state = self.state_manager.get_bot_state()
            if not saved_state:
                self.log_recovery_action("NO_SAVED_STATE", status="INFO")
                return False, {}
            
            # 2. Determina se è necessario recovery
            needs_recovery = self._analyze_recovery_need(saved_state)
            
            if not needs_recovery:
                self.log_recovery_action("NO_RECOVERY_NEEDED", 
                                        {'reason': 'Normal stop or no active state'}, 
                                        status="INFO")
                return False, {}
            
            # 3. Verifica posizioni reali su Bybit
            real_positions = self._get_real_positions_from_exchange()
            
            # 4. Analizza discrepanze
            recovery_info = self._analyze_position_discrepancies(saved_state, real_positions)
            
            self.log_recovery_action("CRASH_RECOVERY_ANALYSIS_COMPLETE", 
                                   recovery_info, 
                                   status="SUCCESS")
            
            return True, recovery_info
            
        except Exception as e:
            self.log_recovery_action("CRASH_RECOVERY_CHECK_ERROR", 
                                   {'error': str(e), 'traceback': traceback.format_exc()}, 
                                   status="ERROR")
            return False, {}
    
    def _analyze_recovery_need(self, saved_state: Dict) -> bool:
        """Analizza se il recovery è necessario"""
        # Non serve recovery se fermato manualmente
        if saved_state.get('stopped_manually', False):
            return False
        
        # Serve recovery se:
        # 1. Il bot era in esecuzione ma ora non lo è
        # 2. C'è un flag esplicito di crash recovery
        # 3. Ha posizioni attive salvate
        was_running = saved_state.get('is_running', False)
        crash_flag = saved_state.get('crash_recovery_needed', False)
        has_positions = saved_state.get('has_open_positions', False)
        
        # Se era in running o ha il flag crash o ha posizioni, serve recovery
        return was_running or crash_flag or has_positions
    
    def _get_real_positions_from_exchange(self) -> Dict:
        """Ottieni posizioni reali dall'exchange"""
        try:
            if not self.trading_wrapper:
                self.log_recovery_action("NO_TRADING_WRAPPER", status="WARNING")
                print(f"⚠️ RECOVERY DEBUG: Trading wrapper non disponibile")
                return {}
            
            # 🆕 IMPORTANTE: Imposta una sessione temporanea se necessario per il recovery
            saved_state = self.state_manager.get_bot_state() if self.state_manager else None
            temp_session_id = None
            
            if saved_state and saved_state.get('current_session_id'):
                temp_session_id = saved_state['current_session_id']
                self.trading_wrapper.set_session(temp_session_id)
                print(f"🔄 RECOVERY DEBUG: Impostata sessione temporanea: {temp_session_id}")
            else:
                print(f"🔄 RECOVERY DEBUG: Nessuna sessione salvata - recovery senza sessione")
            
            # Prima sincronizza con il database per caricare trade esistenti
            self.trading_wrapper.sync_with_database()
            
            # Poi sincronizza con Bybit per trovare posizioni reali
            sync_result = self.trading_wrapper.sync_with_bybit()
            
            if sync_result['success']:
                # Usa il metodo del trading wrapper per ottenere posizioni attive
                real_positions = self.trading_wrapper.get_active_trades()
                
                # DEBUG: Log dettagliato delle posizioni trovate
                print(f"🔍 RECOVERY DEBUG: Posizioni reali dall'exchange:")
                print(f"   Numero posizioni: {len(real_positions)}")
                if real_positions:
                    for trade_id, trade_info in real_positions.items():
                        external_id = trade_info.get('external_trade_id', 'N/A')
                        recovery_flag = "🆘" if trade_info.get('recovery_orphan') else "📋"
                        print(f"   {recovery_flag} {trade_id} (ext: {external_id}): {trade_info.get('side', 'N/A')} {trade_info.get('symbol', 'N/A')} {trade_info.get('quantity', 'N/A')}")
                else:
                    print(f"   - Nessuna posizione trovata")
                
                self.log_recovery_action("REAL_POSITIONS_FETCHED", 
                                       {'positions_count': len(real_positions),
                                        'positions_details': list(real_positions.keys()) if real_positions else [],
                                        'sync_success': True,
                                        'session_used': temp_session_id}, 
                                       status="SUCCESS")
                
                return real_positions
            else:
                print(f"⚠️ RECOVERY DEBUG: Errore sincronizzazione Bybit: {sync_result.get('error')}")
                self.log_recovery_action("BYBIT_SYNC_FAILED", 
                                       {'error': sync_result.get('error')}, 
                                       status="WARNING")
                return {}
            
        except Exception as e:
            self.log_recovery_action("REAL_POSITIONS_FETCH_ERROR", 
                                   {'error': str(e)}, 
                                   status="ERROR")
            print(f"❌ RECOVERY DEBUG: Eccezione durante sync: {e}")
            return {}
    
    def _analyze_position_discrepancies(self, saved_state: Dict, real_positions: Dict) -> Dict:
        """Analizza discrepanze tra stato salvato e posizioni reali"""
        saved_positions = saved_state.get('active_trades', {})
        operational_phase = saved_state.get('operational_phase', 'SEEKING_ENTRY')
        
        # DEBUG: Log dettagliato dello stato salvato
        print(f"🔍 RECOVERY DEBUG: Stato salvato:")
        print(f"   Fase operativa salvata: {operational_phase}")
        print(f"   Has open positions: {saved_state.get('has_open_positions', False)}")
        print(f"   Numero posizioni salvate: {len(saved_positions)}")
        if saved_positions:
            for trade_id, trade_info in saved_positions.items():
                print(f"   - {trade_id}: {trade_info.get('side', 'N/A')} {trade_info.get('symbol', 'N/A')} {trade_info.get('quantity', 'N/A')}")
        else:
            print(f"   - Nessuna posizione salvata")
        
        # Conta posizioni
        saved_count = len(saved_positions)
        real_count = len(real_positions)
        
        # Determina la fase operativa corretta basata su posizioni reali
        correct_phase = 'MANAGING_POSITIONS' if real_count > 0 else 'SEEKING_ENTRY'
        
        print(f"🔍 RECOVERY DEBUG: Confronto stati:")
        print(f"   Salvate: {saved_count} posizioni, Fase: {operational_phase}")
        print(f"   Reali: {real_count} posizioni, Fase corretta: {correct_phase}")
        
        # Identifica posizioni mancanti o extra
        saved_symbols = set(saved_positions.keys()) if saved_positions else set()
        real_symbols = set(real_positions.keys()) if real_positions else set()
        
        missing_in_real = saved_symbols - real_symbols  # Salvate ma non reali
        extra_in_real = real_symbols - saved_symbols    # Reali ma non salvate
        
        recovery_info = {
            'saved_state_summary': {
                'operational_phase': operational_phase,
                'saved_positions_count': saved_count,
                'session_id': saved_state.get('current_session_id'),
                'last_save_time': saved_state.get('last_save_time'),
            },
            'real_positions_summary': {
                'real_positions_count': real_count,
                'positions': list(real_positions.keys()) if real_positions else []
            },
            'analysis': {
                'correct_operational_phase': correct_phase,
                'phase_mismatch': operational_phase != correct_phase,
                'positions_discrepancy': saved_count != real_count,
                'missing_in_real': list(missing_in_real),
                'extra_in_real': list(extra_in_real)
            },
            'recovery_action': self._determine_recovery_action(
                operational_phase, correct_phase, saved_count, real_count
            )
        }
        
        return recovery_info
    
    def _determine_recovery_action(self, saved_phase: str, correct_phase: str, 
                                 saved_count: int, real_count: int) -> str:
        """Determina l'azione di recovery necessaria"""
        
        # Normalizza le fasi operative per il confronto
        normalized_saved = self._normalize_operational_phase(saved_phase)
        normalized_correct = self._normalize_operational_phase(correct_phase)
        
        if normalized_saved == normalized_correct and saved_count == real_count:
            return "CONTINUE_NORMAL"  # Tutto ok, continua normale
        
        if normalized_correct == 'MANAGING_POSITIONS' and real_count > 0:
            if normalized_saved == 'SEEKING_ENTRY':
                return "SWITCH_TO_MANAGING"  # Aveva posizioni ma era in seeking
            else:
                return "UPDATE_POSITIONS"    # Era in managing ma posizioni diverse
        
        if normalized_correct == 'SEEKING_ENTRY' and real_count == 0:
            if normalized_saved == 'MANAGING_POSITIONS':
                return "SWITCH_TO_SEEKING"   # Posizioni chiuse, torna a seeking
            else:
                return "CONTINUE_SEEKING"    # Era già in seeking
        
        return "MANUAL_REVIEW_NEEDED"  # Situazione complessa
    
    def _normalize_operational_phase(self, phase: str) -> str:
        """Normalizza le fasi operative per confronti consistenti"""
        if not phase:
            return 'SEEKING_ENTRY'
        
        phase_upper = phase.upper()
        
        # Mappa fasi specifiche a categorie generali
        if phase_upper in ['IN_POSITION_LONG', 'IN_POSITION_SHORT', 'MANAGING_POSITIONS']:
            return 'MANAGING_POSITIONS'
        elif phase_upper in ['SEEKING_ENTRY', 'WAITING_ENTRY']:
            return 'SEEKING_ENTRY'
        else:
            # Default per fasi sconosciute
            return 'SEEKING_ENTRY'
    
    def execute_recovery(self, recovery_info: Dict, bot_status: Dict) -> Tuple[bool, str, Dict]:
        """
        Esegue il recovery del bot basato sull'analisi
        Returns: (success, operational_phase, updated_bot_status)
        """
        try:
            action = recovery_info['recovery_action']
            self.log_recovery_action("EXECUTING_RECOVERY", 
                                   {'action': action}, 
                                   status="START")
            
            # Aggiorna bot_status con info di recovery
            updated_status = bot_status.copy()
            
            if action == "CONTINUE_NORMAL":
                return self._continue_normal_operation(updated_status, recovery_info)
            
            elif action == "SWITCH_TO_MANAGING":
                return self._switch_to_managing_positions(updated_status, recovery_info)
            
            elif action == "UPDATE_POSITIONS":
                return self._update_position_tracking(updated_status, recovery_info)
            
            elif action == "SWITCH_TO_SEEKING":
                return self._switch_to_seeking_entry(updated_status, recovery_info)
            
            elif action == "CONTINUE_SEEKING":
                return self._continue_seeking_entry(updated_status, recovery_info)
            
            else:  # MANUAL_REVIEW_NEEDED
                return self._handle_manual_review_case(updated_status, recovery_info)
                
        except Exception as e:
            self.log_recovery_action("RECOVERY_EXECUTION_ERROR", 
                                   {'error': str(e), 'traceback': traceback.format_exc()}, 
                                   status="ERROR")
            return False, 'SEEKING_ENTRY', bot_status
    
    def _continue_normal_operation(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Continua operazione normale - stato coerente"""
        # 🔧 CORREZIONE: Usa la fase corretta calcolata, non quella salvata
        correct_phase = recovery_info.get('correct_operational_phase', 
                                        recovery_info['saved_state_summary']['operational_phase'])
        
        # ✅ CORREZIONE CRITICA: Trasferisci session_id dal recovery_info a bot_status
        saved_session_id = recovery_info['saved_state_summary'].get('session_id')
        if saved_session_id:
            bot_status['current_session_id'] = saved_session_id
            print(f"🔄 Recovery: session_id trasferita: {saved_session_id}")
        else:
            print(f"⚠️ Recovery: nessuna session_id trovata nel recovery_info")
        
        self.log_recovery_action("CONTINUING_NORMAL_OPERATION", 
                               {'saved_phase': recovery_info['saved_state_summary']['operational_phase'],
                                'correct_phase': correct_phase,
                                'session_id': saved_session_id}, 
                               status="SUCCESS")
        
        # Marca recovery come completato
        self.state_manager.mark_successful_recovery()
        
        return True, correct_phase, bot_status

    def _switch_to_managing_positions(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Il bot aveva posizioni aperte ma era in fase SEEKING_ENTRY"""
        real_positions = recovery_info.get('real_positions_summary', {})
        
        self.log_recovery_action("SWITCHING_TO_MANAGING_POSITIONS", 
                               {'positions': real_positions['positions']}, 
                               status="SUCCESS")
        
        # Aggiorna lo stato per riflettere le posizioni reali
        if self.trading_wrapper:
            try:
                # Sincronizza il trading wrapper con le posizioni reali
                self.trading_wrapper.sync_with_exchange_positions()
                
                # Aggiorna bot_status
                bot_status['total_trades'] = bot_status.get('total_trades', 0) + len(real_positions['positions'])
                
            except Exception as e:
                self.log_recovery_action("SYNC_POSITIONS_ERROR", 
                                       {'error': str(e)}, 
                                       status="WARNING")
        
        # Salva nuovo stato
        self._save_recovered_state(bot_status, 'MANAGING_POSITIONS')
        
        return True, 'MANAGING_POSITIONS', bot_status
    
    def _update_position_tracking(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Aggiorna tracking posizioni con dati reali"""
        
        self.log_recovery_action("UPDATING_POSITION_TRACKING", status="SUCCESS")
        
        # Sincronizza con posizioni reali
        if self.trading_wrapper:
            try:
                self.trading_wrapper.sync_with_exchange_positions()
            except Exception as e:
                self.log_recovery_action("POSITION_SYNC_ERROR", 
                                       {'error': str(e)}, 
                                       status="WARNING")
        
        # Salva stato aggiornato
        self._save_recovered_state(bot_status, 'MANAGING_POSITIONS')
        
        return True, 'MANAGING_POSITIONS', bot_status
    
    def _switch_to_seeking_entry(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Le posizioni sono state chiuse, torna a cercare entry"""
        
        self.log_recovery_action("SWITCHING_TO_SEEKING_ENTRY", 
                               {'reason': 'Reconciling positions with exchange'}, 
                               status="SUCCESS")
        
        # Pulisci stato posizioni e sincronizza con l'exchange
        final_positions = {}
        if self.trading_wrapper:
            try:
                self.trading_wrapper.cleanup_closed_positions()
                # Dopo il cleanup, ricontrolla le posizioni reali
                final_positions = self.trading_wrapper.get_active_trades()
                print(f"🔄 Dopo sincronizzazione: {len(final_positions)} posizioni trovate")
            except Exception as e:
                self.log_recovery_action("CLEANUP_POSITIONS_ERROR", 
                                       {'error': str(e)}, 
                                       status="WARNING")
        
        # Determina la fase finale basata sulle posizioni reali dopo sync
        if len(final_positions) > 0:
            print(f"📊 {len(final_positions)} posizioni ancora attive")
            final_phase = 'MANAGING_POSITIONS'
        else:
            print(f"🎯 Nessuna posizione attiva - passaggio a SEEKING_ENTRY")
            final_phase = 'SEEKING_ENTRY'
        
        # Salva nuovo stato
        self._save_recovered_state(bot_status, final_phase)
        
        return True, final_phase, bot_status
    
    def _continue_seeking_entry(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Continua a cercare entry - tutto normale"""
        
        self.log_recovery_action("CONTINUING_SEEKING_ENTRY", status="SUCCESS")
        
        # Marca recovery completato
        self.state_manager.mark_successful_recovery()
        
        return True, 'SEEKING_ENTRY', bot_status
    
    def _handle_manual_review_case(self, bot_status: Dict, recovery_info: Dict) -> Tuple[bool, str, Dict]:
        """Situazione complessa che richiede revisione manuale"""
        
        self.log_recovery_action("MANUAL_REVIEW_NEEDED", 
                               recovery_info, 
                               status="WARNING")
        
        # Per sicurezza, vai in modalità conservativa (SEEKING_ENTRY)
        # e loggha tutto per revisione manuale
        print("⚠️ ATTENZIONE: Situazione recovery complessa rilevata!")
        print("📊 Dettagli salvati nei log di recovery")
        print("🔄 Bot avviato in modalità conservativa (SEEKING_ENTRY)")
        
        self._save_recovered_state(bot_status, 'SEEKING_ENTRY')
        
        return True, 'SEEKING_ENTRY', bot_status
    
    def _save_recovered_state(self, bot_status: Dict, operational_phase: str):
        """Salva il nuovo stato dopo recovery"""
        try:
            # Ottieni posizioni reali aggiornate
            active_trades = {}
            if self.trading_wrapper:
                try:
                    active_trades = self.trading_wrapper.get_active_trades()
                except:
                    pass
            
            # Salva stato con la fase operativa corretta
            self.state_manager.save_bot_running_state(
                bot_status, 
                active_trades, 
                self.trading_wrapper
            )
            
            # Marca recovery come completato
            self.state_manager.mark_successful_recovery()
            
            self.log_recovery_action("RECOVERED_STATE_SAVED", 
                                   {'operational_phase': operational_phase,
                                    'active_trades_count': len(active_trades)}, 
                                   status="SUCCESS")
            
        except Exception as e:
            self.log_recovery_action("SAVE_RECOVERED_STATE_ERROR", 
                                   {'error': str(e)}, 
                                   status="ERROR")
    
    def get_recovery_logs(self, limit: int = 20) -> List[Dict]:
        """Ottieni ultimi log di recovery"""
        try:
            if not self.recovery_log_file.exists():
                return []
            
            with open(self.recovery_log_file, 'r') as f:
                logs = json.load(f)
            
            return logs[-limit:] if logs else []
            
        except Exception as e:
            print(f"⚠️ Errore lettura recovery logs: {e}")
            return []
    
    def clear_recovery_logs(self):
        """Pulisci log di recovery"""
        try:
            if self.recovery_log_file.exists():
                self.recovery_log_file.unlink()
            
            self.log_recovery_action("RECOVERY_LOGS_CLEARED", status="INFO")
            
        except Exception as e:
            print(f"⚠️ Errore pulizia recovery logs: {e}")


def create_crash_recovery_system(state_manager=None, trading_wrapper=None):
    """Factory function per creare il sistema di crash recovery"""
    return CrashRecoveryManager(state_manager, trading_wrapper)
