#!/usr/bin/env python3
"""
Telegram Bot Notifier per Trading Bot
Sistema di notifiche avanzato che monitora il trading bot e invia aggiornamenti via Telegram
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import threading
import time

try:
    import telegram
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot non installato. Installa con: pip install python-telegram-bot")

class TelegramNotifier:
    """Gestisce le notifiche Telegram per il trading bot"""
    
    def __init__(self, token: str, chat_id: str, dashboard_url: str = "http://localhost:5000"):
        self.token = token
        self.chat_id = chat_id
        self.dashboard_url = dashboard_url
        self.bot = None
        self.enabled = False
        
        # File per salvare lo stato delle notifiche
        self.state_file = Path(__file__).parent.parent / "data" / "telegram_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
        
        # Inizializza bot se Telegram è disponibile
        if TELEGRAM_AVAILABLE and token and chat_id:
            try:
                self.bot = Bot(token=token)
                self.enabled = True
                print("✅ Telegram Notifier inizializzato")
            except Exception as e:
                print(f"❌ Errore inizializzazione Telegram: {e}")
        else:
            print("⚠️ Telegram Notifier disabilitato (token/chat_id mancanti o libreria non installata)")
    
    def is_enabled(self) -> bool:
        """Verifica se le notifiche Telegram sono abilitate"""
        return self.enabled and self.bot is not None
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Invia un messaggio Telegram"""
        if not self.is_enabled():
            print(f"📱 Telegram OFF: {message}")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            print(f"📱 Telegram: {message}")
            return True
        except Exception as e:
            print(f"❌ Errore invio Telegram: {e}")
            return False
    
    def send_message_sync(self, message: str, parse_mode: str = "HTML") -> bool:
        """Versione sincrona per inviare messaggi"""
        if not self.is_enabled():
            print(f"📱 Telegram OFF: {message}")
            return False
        
        try:
            # Crea un nuovo loop se non esiste
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(self.send_message(message, parse_mode))
        except Exception as e:
            print(f"❌ Errore invio Telegram sync: {e}")
            return False
    
    # 🚀 NOTIFICHE TRADING
    
    def notify_bot_started(self, symbol: str, operation: str, config: Dict) -> bool:
        """Notifica avvio bot"""
        message = f"""
🚀 <b>Trading Bot AVVIATO</b>

💱 Simbolo: <code>{symbol}</code>
📈 Operazione: <b>{operation}</b>
⚙️ Configurazione:
  • EMA: {config.get('ema_period', 'N/A')}
  • Intervallo: {config.get('interval', 'N/A')}min
  • Quantità: ${config.get('quantity', 'N/A')}
  • Stop Candele: {config.get('stop_candles', 'N/A')}

🎯 Il bot è ora attivo e cerca opportunità di {operation.lower()}!
"""
        return self.send_message_sync(message)
    
    def notify_bot_stopped(self, reason: str = "Manuale") -> bool:
        """Notifica stop bot"""
        message = f"""
🛑 <b>Trading Bot FERMATO</b>

📄 Motivo: {reason}
⏰ Ora: {datetime.now().strftime('%H:%M:%S')}

💡 Usa /start per riavviare il bot
"""
        return self.send_message_sync(message)
    
    def notify_position_opened(self, trade_info: Dict) -> bool:
        """Notifica apertura posizione"""
        side_emoji = "📈" if trade_info.get('side') in ['BUY', 'Buy'] else "📉"
        side_text = "LONG" if trade_info.get('side') in ['BUY', 'Buy'] else "SHORT"
        
        message = f"""
{side_emoji} <b>POSIZIONE APERTA</b>

💱 {trade_info.get('symbol', 'N/A')}
📊 Tipo: <b>{side_text}</b>
💰 Quantità: {trade_info.get('quantity', 'N/A')}
💵 Prezzo: ${trade_info.get('price', 'N/A')}
💸 Valore: ${trade_info.get('value', 'N/A')}

🆔 Trade ID: <code>{trade_info.get('trade_id', 'N/A')}</code>
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message_sync(message)
    
    def notify_position_closed(self, trade_info: Dict, pnl: float = None, reason: str = "Strategy") -> bool:
        """Notifica chiusura posizione"""
        side_emoji = "📈" if trade_info.get('side') in ['BUY', 'Buy'] else "📉"
        side_text = "LONG" if trade_info.get('side') in ['BUY', 'Buy'] else "SHORT"
        
        # PnL emoji
        pnl_emoji = "💚" if pnl and pnl > 0 else "❤️" if pnl and pnl < 0 else "💙"
        pnl_text = f"{pnl:+.2f}" if pnl else "N/A"
        
        message = f"""
🔒 <b>POSIZIONE CHIUSA</b>

💱 {trade_info.get('symbol', 'N/A')}
📊 Tipo: <b>{side_text}</b>
💰 Quantità: {trade_info.get('quantity', 'N/A')}
💵 Prezzo chiusura: ${trade_info.get('close_price', 'N/A')}

{pnl_emoji} <b>PnL: ${pnl_text}</b>
📋 Motivo: {reason}

🆔 Trade ID: <code>{trade_info.get('trade_id', 'N/A')}</code>
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message_sync(message)
    
    # 🚨 NOTIFICHE SISTEMA
    
    def notify_crash_detected(self, error_info: str = "") -> bool:
        """Notifica crash rilevato"""
        message = f"""
🚨 <b>CRASH RILEVATO!</b>

⚠️ Il trading bot si è fermato inaspettatamente
⏰ {datetime.now().strftime('%H:%M:%S')}

🔄 Sistema di recovery in corso...
📊 Verifica posizioni in corso...

{f'❌ Dettagli: {error_info}' if error_info else ''}

💡 Controlla il dashboard: {self.dashboard_url}
"""
        return self.send_message_sync(message)
    
    def notify_recovery_completed(self, recovery_info: Dict) -> bool:
        """Notifica recovery completato"""
        phase = recovery_info.get('operational_phase', 'N/A')
        positions = recovery_info.get('positions_count', 0)
        action = recovery_info.get('recovery_action', 'N/A')
        
        message = f"""
✅ <b>RECOVERY COMPLETATO</b>

🎯 Fase operativa: <b>{phase}</b>
📊 Posizioni recuperate: <b>{positions}</b>
🔧 Azione: {action}

🚀 Il bot è tornato operativo!
⏰ {datetime.now().strftime('%H:%M:%S')}

💡 Dashboard: {self.dashboard_url}
"""
        return self.send_message_sync(message)
    
    def notify_error(self, error_type: str, error_msg: str) -> bool:
        """Notifica errore generico"""
        message = f"""
⚠️ <b>ERRORE SISTEMA</b>

🔧 Tipo: {error_type}
💬 Messaggio: {error_msg}
⏰ {datetime.now().strftime('%H:%M:%S')}

💡 Controlla il dashboard: {self.dashboard_url}
"""
        return self.send_message_sync(message)
    
    # 📊 NOTIFICHE STATISTICHE
    
    def notify_daily_summary(self, stats: Dict) -> bool:
        """Notifica riepilogo giornaliero"""
        total_trades = stats.get('total_trades', 0)
        total_pnl = stats.get('total_pnl', 0)
        win_rate = stats.get('win_rate', 0)
        
        pnl_emoji = "💚" if total_pnl > 0 else "❤️" if total_pnl < 0 else "💙"
        
        message = f"""
📊 <b>RIEPILOGO GIORNALIERO</b>

📈 Trades totali: <b>{total_trades}</b>
{pnl_emoji} PnL totale: <b>${total_pnl:+.2f}</b>
🎯 Win Rate: <b>{win_rate:.1f}%</b>

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
💡 Dashboard: {self.dashboard_url}
"""
        return self.send_message_sync(message)
    
    # 🔧 COMANDI BOT
    
    def get_status_message(self) -> str:
        """Ottieni messaggio di stato del bot"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/bot/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                running = "🟢 ATTIVO" if data.get('running') else "🔴 FERMO"
                symbol = data.get('symbol', 'N/A')
                phase = data.get('operational_phase', 'N/A')
                
                # Ottieni posizioni
                pos_response = requests.get(f"{self.dashboard_url}/api/trading/positions", timeout=5)
                positions_count = 0
                if pos_response.status_code == 200:
                    positions = pos_response.json()
                    positions_count = len(positions)
                
                message = f"""
🤖 <b>STATO TRADING BOT</b>

🔸 Stato: {running}
💱 Simbolo: <code>{symbol}</code>
🎯 Fase: {phase}
📊 Posizioni attive: <b>{positions_count}</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
💡 Dashboard: {self.dashboard_url}
"""
                return message
            else:
                return "❌ Errore nel recupero stato bot"
                
        except Exception as e:
            return f"❌ Errore connessione: {str(e)}"

# Istanza globale per le notifiche
telegram_notifier = None

def init_telegram_notifier(token: str, chat_id: str, dashboard_url: str = "http://localhost:5000") -> TelegramNotifier:
    """Inizializza il notificatore Telegram globale"""
    global telegram_notifier
    telegram_notifier = TelegramNotifier(token, chat_id, dashboard_url)
    return telegram_notifier

def get_telegram_notifier() -> Optional[TelegramNotifier]:
    """Ottieni l'istanza del notificatore Telegram"""
    return telegram_notifier

# Funzioni di utilità per notifiche rapide
def notify_trade_opened(trade_info: Dict) -> bool:
    """Notifica rapida apertura trade"""
    if telegram_notifier:
        return telegram_notifier.notify_position_opened(trade_info)
    return False

def notify_trade_closed(trade_info: Dict, pnl: float = None, reason: str = "Strategy") -> bool:
    """Notifica rapida chiusura trade"""
    if telegram_notifier:
        return telegram_notifier.notify_position_closed(trade_info, pnl, reason)
    return False

def notify_bot_crash(error_info: str = "") -> bool:
    """Notifica rapida crash"""
    if telegram_notifier:
        return telegram_notifier.notify_crash_detected(error_info)
    return False

def notify_bot_recovery(recovery_info: Dict) -> bool:
    """Notifica rapida recovery"""
    if telegram_notifier:
        return telegram_notifier.notify_recovery_completed(recovery_info)
    return False
