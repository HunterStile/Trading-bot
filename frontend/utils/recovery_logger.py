#!/usr/bin/env python3
"""
Recovery Logger - Utilità per logging e debugging del crash recovery
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from termcolor import colored

from .simple_bot_state import EnhancedBotState
from .crash_recovery import create_crash_recovery_system


class RecoveryLogger:
    """Sistema di logging avanzato per debugging crash recovery"""
    
    def __init__(self):
        self.log_dir = Path(__file__).parent.parent / "data" / "recovery_logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # File di log principali
        self.main_log = self.log_dir / "recovery.log"
        self.positions_log = self.log_dir / "positions.log"
        self.state_history = self.log_dir / "state_history.json"
    
    def log_recovery_event(self, event_type: str, data: Dict, level: str = "INFO"):
        """Log dettagliato di un evento di recovery"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "level": level,
            "data": data
        }
        
        # Scrivi nel log principale
        with open(self.main_log, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {level}: {event_type} - {json.dumps(data, indent=2)}\n")
        
        # Se è un evento relativo alle posizioni, loggalo anche nel file specifico
        if "position" in event_type.lower() or "trade" in event_type.lower():
            with open(self.positions_log, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {event_type}: {json.dumps(data)}\n")
    
    def save_state_snapshot(self, state_data: Dict, reason: str):
        """Salva uno snapshot dello stato del bot"""
        timestamp = datetime.now().isoformat()
        
        snapshot = {
            "timestamp": timestamp,
            "reason": reason,
            "state": state_data
        }
        
        # Carica storico esistente
        history = []
        if self.state_history.exists():
            try:
                with open(self.state_history, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Aggiungi nuovo snapshot
        history.append(snapshot)
        
        # Mantieni solo gli ultimi 50 snapshot
        if len(history) > 50:
            history = history[-50:]
        
        # Salva
        with open(self.state_history, 'w') as f:
            json.dump(history, f, indent=2)
    
    def analyze_recovery_patterns(self) -> Dict:
        """Analizza i pattern di crash recovery dal log"""
        if not self.main_log.exists():
            return {"error": "Nessun log di recovery trovato"}
        
        analysis = {
            "total_recovery_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recovery_types": {},
            "common_errors": {},
            "last_24h_events": 0
        }
        
        try:
            with open(self.main_log, 'r') as f:
                lines = f.readlines()
            
            last_24h = datetime.now() - timedelta(hours=24)
            
            for line in lines:
                if "CRASH_RECOVERY" in line:
                    analysis["total_recovery_attempts"] += 1
                    
                    # Estrai timestamp
                    if line.startswith('['):
                        timestamp_str = line.split(']')[0][1:]
                        try:
                            event_time = datetime.fromisoformat(timestamp_str)
                            if event_time >= last_24h:
                                analysis["last_24h_events"] += 1
                        except:
                            pass
                
                if "RECOVERY_COMPLETATO" in line:
                    analysis["successful_recoveries"] += 1
                elif "RECOVERY_FALLITO" in line or "Recovery fallito" in line:
                    analysis["failed_recoveries"] += 1
                
                # Analizza tipi di recovery
                for recovery_type in ["SWITCH_TO_MANAGING", "SWITCH_TO_SEEKING", "CONTINUE_NORMAL"]:
                    if recovery_type in line:
                        if recovery_type not in analysis["recovery_types"]:
                            analysis["recovery_types"][recovery_type] = 0
                        analysis["recovery_types"][recovery_type] += 1
                
                # Analizza errori comuni
                if "ERROR" in line or "Errore" in line:
                    # Estrai tipo di errore
                    if "sincronizzazione" in line.lower():
                        error_type = "Errore sincronizzazione"
                    elif "posizioni" in line.lower():
                        error_type = "Errore posizioni"
                    elif "network" in line.lower() or "connessione" in line.lower():
                        error_type = "Errore rete"
                    else:
                        error_type = "Errore generico"
                    
                    if error_type not in analysis["common_errors"]:
                        analysis["common_errors"][error_type] = 0
                    analysis["common_errors"][error_type] += 1
        
        except Exception as e:
            analysis["error"] = f"Errore analisi: {e}"
        
        return analysis
    
    def get_recent_recovery_logs(self, hours: int = 24) -> List[Dict]:
        """Ottieni log di recovery recenti"""
        if not self.main_log.exists():
            return []
        
        recent_logs = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.main_log, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.startswith('['):
                    try:
                        timestamp_str = line.split(']')[0][1:]
                        event_time = datetime.fromisoformat(timestamp_str)
                        
                        if event_time >= cutoff_time:
                            # Parsing semplice del log
                            parts = line.split(' - ', 1)
                            if len(parts) >= 2:
                                header = parts[0]
                                content = parts[1].strip()
                                
                                recent_logs.append({
                                    "timestamp": timestamp_str,
                                    "header": header,
                                    "content": content
                                })
                    except:
                        continue
        
        except Exception as e:
            print(f"Errore lettura log: {e}")
        
        return recent_logs
    
    def print_recovery_status(self):
        """Stampa un report colorato dello stato del recovery"""
        print(colored("\n🔍 RECOVERY STATUS REPORT", "cyan", attrs=["bold"]))
        print("=" * 50)
        
        # Stato corrente
        state_manager = EnhancedBotState()
        current_state = state_manager.get_bot_state()
        
        if current_state:
            print(colored(f"🤖 Bot Status:", "yellow"))
            print(f"  Running: {current_state.get('is_running', 'Unknown')}")
            print(f"  Phase: {current_state.get('operational_phase', 'Unknown')}")
            print(f"  Positions: {current_state.get('has_open_positions', 'Unknown')}")
            print(f"  Session ID: {current_state.get('current_session_id', 'None')}")
            
            if current_state.get('crash_recovery_needed'):
                print(colored("  ⚠️ CRASH RECOVERY NEEDED!", "red", attrs=["bold"]))
            else:
                print(colored("  ✅ No recovery needed", "green"))
        else:
            print(colored("❌ No bot state found", "red"))
        
        # Analisi log
        print(colored(f"\n📊 Recovery Analytics:", "yellow"))
        analysis = self.analyze_recovery_patterns()
        
        if "error" not in analysis:
            print(f"  Total Attempts: {analysis['total_recovery_attempts']}")
            print(f"  Successful: {colored(str(analysis['successful_recoveries']), 'green')}")
            print(f"  Failed: {colored(str(analysis['failed_recoveries']), 'red')}")
            print(f"  Last 24h Events: {analysis['last_24h_events']}")
            
            if analysis['recovery_types']:
                print(f"\n  Recovery Types:")
                for recovery_type, count in analysis['recovery_types'].items():
                    print(f"    {recovery_type}: {count}")
            
            if analysis['common_errors']:
                print(f"\n  Common Errors:")
                for error_type, count in analysis['common_errors'].items():
                    print(f"    {colored(error_type, 'red')}: {count}")
        else:
            print(colored(f"  Error: {analysis['error']}", "red"))
        
        # Log recenti
        print(colored(f"\n📝 Recent Events (last 2 hours):", "yellow"))
        recent_logs = self.get_recent_recovery_logs(2)
        
        if recent_logs:
            for log in recent_logs[-5:]:  # Ultimi 5
                timestamp = log["timestamp"].split('T')[1][:8]  # Solo HH:MM:SS
                level_color = "red" if "ERROR" in log["header"] else "green" if "SUCCESS" in log["header"] else "white"
                print(f"  [{colored(timestamp, 'blue')}] {colored(log['header'].split(': ')[1], level_color)}")
        else:
            print("  No recent events")
        
        print("=" * 50)
    
    def clear_logs(self):
        """Pulisce tutti i log di recovery"""
        try:
            if self.main_log.exists():
                self.main_log.unlink()
            if self.positions_log.exists():
                self.positions_log.unlink()
            if self.state_history.exists():
                self.state_history.unlink()
            
            print(colored("✅ Log di recovery cancellati", "green"))
        except Exception as e:
            print(colored(f"❌ Errore cancellazione log: {e}", "red"))
    
    def export_recovery_report(self) -> str:
        """Esporta un report completo in formato JSON"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "analysis": self.analyze_recovery_patterns(),
            "recent_events": self.get_recent_recovery_logs(24),
            "current_state": None
        }
        
        # Aggiungi stato corrente
        try:
            state_manager = EnhancedBotState()
            report["current_state"] = state_manager.get_recovery_summary()
        except:
            report["current_state"] = {"error": "Cannot read current state"}
        
        # Salva report
        report_file = self.log_dir / f"recovery_report_{int(datetime.now().timestamp())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_file)


def main():
    """Funzione principale per testing"""
    logger = RecoveryLogger()
    
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "status":
            logger.print_recovery_status()
        elif action == "clear":
            logger.clear_logs()
        elif action == "export":
            report_file = logger.export_recovery_report()
            print(colored(f"📄 Report esportato: {report_file}", "green"))
        elif action == "test":
            # Test di logging
            logger.log_recovery_event("TEST_EVENT", {"test": True, "value": 123})
            logger.save_state_snapshot({"test_state": True}, "Test snapshot")
            print(colored("✅ Test logging completato", "green"))
        else:
            print(colored("❌ Azione non riconosciuta. Usa: status, clear, export, test", "red"))
    else:
        logger.print_recovery_status()


if __name__ == "__main__":
    main()
