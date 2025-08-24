#!/usr/bin/env python3
"""
Telegram Bot Interattivo per Trading Bot
Bot Telegram con comandi per controllare e monitorare il trading bot
"""

import asyncio
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot non installato. Installa con: pip install python-telegram-bot")

from .telegram_notifier import get_telegram_notifier

class TradingBotTelegram:
    """Bot Telegram per controllare il trading bot"""
    
    def __init__(self, token: str, dashboard_url: str = "http://localhost:5000"):
        self.token = token
        self.dashboard_url = dashboard_url
        self.application = None
        
        if TELEGRAM_AVAILABLE and token:
            self.application = Application.builder().token(token).build()
            self._setup_handlers()
            print("✅ Telegram Bot inizializzato")
        else:
            print("⚠️ Telegram Bot disabilitato")
    
    def _setup_handlers(self):
        """Configura i gestori dei comandi"""
        if not self.application:
            return
        
        # Comandi base
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Comandi controllo bot
        self.application.add_handler(CommandHandler("startbot", self.start_bot_command))
        self.application.add_handler(CommandHandler("stopbot", self.stop_bot_command))
        self.application.add_handler(CommandHandler("positions", self.positions_command))
        
        # Comandi info
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Gestori callback per bottoni
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status Bot", callback_data="status"),
                InlineKeyboardButton("💰 Posizioni", callback_data="positions")
            ],
            [
                InlineKeyboardButton("🚀 Avvia Bot", callback_data="start_bot"),
                InlineKeyboardButton("🛑 Ferma Bot", callback_data="stop_bot")
            ],
            [
                InlineKeyboardButton("📈 Statistiche", callback_data="stats"),
                InlineKeyboardButton("📋 Storico", callback_data="history")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """
🤖 <b>Trading Bot Controller</b>

Benvenuto nel controller del Trading Bot!
Usa i bottoni qui sotto o i comandi per gestire il bot.

🔸 <b>Comandi disponibili:</b>
/status - Stato attuale del bot
/startbot - Avvia il trading bot
/stopbot - Ferma il trading bot
/positions - Mostra posizioni attive
/history - Storico operazioni
/stats - Statistiche di trading
/help - Mostra questo messaggio

💡 Dashboard: <a href=\"""" + self.dashboard_url + """\">Apri Dashboard</a>
"""
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        await self.start_command(update, context)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/bot/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                running = "🟢 ATTIVO" if data.get('running') else "🔴 FERMO"
                symbol = data.get('symbol', 'N/A')
                operation = "LONG" if data.get('operation') else "SHORT"
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
📈 Operazione: <b>{operation}</b>
🎯 Fase: {phase}
📊 Posizioni attive: <b>{positions_count}</b>

⚙️ <b>Configurazione:</b>
• EMA: {data.get('ema_period', 'N/A')}
• Intervallo: {data.get('interval', 'N/A')}min
• Quantità: ${data.get('quantity', 'N/A')}
• Stop Candele: {data.get('stop_candles', 'N/A')}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Aggiorna", callback_data="status")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Errore nel recupero stato bot")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Errore connessione: {str(e)}")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /positions"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/trading/positions", timeout=10)
            if response.status_code == 200:
                positions = response.json()
                
                if not positions:
                    message = """
📊 <b>POSIZIONI ATTIVE</b>

🚫 Nessuna posizione attiva al momento

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                else:
                    message = f"📊 <b>POSIZIONI ATTIVE ({len(positions)})</b>\n\n"
                    
                    for pos in positions:
                        side_emoji = "📈" if pos.get('side') in ['BUY', 'Buy'] else "📉"
                        side_text = "LONG" if pos.get('side') in ['BUY', 'Buy'] else "SHORT"
                        
                        message += f"""
{side_emoji} <b>{pos.get('symbol', 'N/A')}</b>
📊 Tipo: {side_text}
💰 Quantità: {pos.get('quantity', 'N/A')}
💵 Prezzo medio: ${pos.get('avg_price', 'N/A')}
💸 Valore: ${pos.get('value', 'N/A')}
🆔 <code>{pos.get('trade_id', 'N/A')}</code>

"""
                    
                    message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Aggiorna", callback_data="positions")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Errore nel recupero posizioni")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Errore connessione: {str(e)}")
    
    async def start_bot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /startbot"""
        try:
            # Prima ottieni la configurazione corrente
            config_response = requests.get(f"{self.dashboard_url}/api/bot/config", timeout=10)
            if config_response.status_code != 200:
                await update.message.reply_text("❌ Errore nel recupero configurazione")
                return
            
            config = config_response.json()
            
            # Avvia il bot
            response = requests.post(f"{self.dashboard_url}/api/bot/start", json=config, timeout=15)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    message = f"""
✅ <b>BOT AVVIATO</b>

💱 Simbolo: <code>{config.get('symbol', 'N/A')}</code>
📈 Operazione: {'LONG' if config.get('operation') else 'SHORT'}
💰 Quantità: ${config.get('quantity', 'N/A')}

🚀 Il bot è ora attivo!
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                else:
                    message = f"❌ Errore nell'avvio: {result.get('error', 'Errore sconosciuto')}"
            else:
                message = "❌ Errore nell'avvio del bot"
            
            await update.message.reply_text(message, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore: {str(e)}")
    
    async def stop_bot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stopbot"""
        try:
            response = requests.post(f"{self.dashboard_url}/api/bot/stop", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    message = f"""
🛑 <b>BOT FERMATO</b>

✅ Il bot è stato fermato con successo
⏰ {datetime.now().strftime('%H:%M:%S')}

💡 Usa /startbot per riavviarlo
"""
                else:
                    message = f"❌ Errore nello stop: {result.get('error', 'Errore sconosciuto')}"
            else:
                message = "❌ Errore nello stop del bot"
            
            await update.message.reply_text(message, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore: {str(e)}")
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /history"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/history/trades?limit=10", timeout=10)
            if response.status_code == 200:
                trades = response.json()
                
                if not trades:
                    message = "📋 Nessuna operazione nello storico"
                else:
                    message = f"📋 <b>ULTIME {len(trades)} OPERAZIONI</b>\n\n"
                    
                    for trade in trades:
                        side_emoji = "📈" if trade.get('side') in ['BUY', 'Buy'] else "📉"
                        status_emoji = "✅" if trade.get('status') == 'CLOSED' else "🔄"
                        
                        pnl = trade.get('pnl', 0)
                        pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💙"
                        
                        message += f"""
{status_emoji}{side_emoji} <b>{trade.get('symbol', 'N/A')}</b>
💰 ${trade.get('quantity', 'N/A')} @ ${trade.get('avg_price', 'N/A')}
{pnl_emoji} PnL: ${pnl:+.2f}
📅 {trade.get('open_time', 'N/A')[:16]}

"""
                    
                    message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Aggiorna", callback_data="history")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Errore nel recupero storico")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Errore connessione: {str(e)}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats"""
        try:
            # Ottieni statistiche dalle sessioni
            response = requests.get(f"{self.dashboard_url}/api/history/sessions", timeout=10)
            if response.status_code == 200:
                sessions = response.json()
                
                total_trades = sum(s.get('total_trades', 0) for s in sessions)
                total_pnl = sum(s.get('total_pnl', 0) for s in sessions)
                
                # Calcola win rate
                trades_response = requests.get(f"{self.dashboard_url}/api/history/trades", timeout=10)
                win_trades = 0
                total_closed = 0
                
                if trades_response.status_code == 200:
                    trades = trades_response.json()
                    closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
                    total_closed = len(closed_trades)
                    win_trades = len([t for t in closed_trades if t.get('pnl', 0) > 0])
                
                win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0
                pnl_emoji = "💚" if total_pnl > 0 else "❤️" if total_pnl < 0 else "💙"
                
                message = f"""
📊 <b>STATISTICHE TRADING</b>

📈 Trades totali: <b>{total_trades}</b>
🎯 Trades chiusi: <b>{total_closed}</b>
✅ Trades vincenti: <b>{win_trades}</b>
❌ Trades perdenti: <b>{total_closed - win_trades}</b>

🏆 Win Rate: <b>{win_rate:.1f}%</b>
{pnl_emoji} PnL totale: <b>${total_pnl:+.2f}</b>

📅 Sessioni: <b>{len(sessions)}</b>
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Aggiorna", callback_data="stats")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Errore nel recupero statistiche")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Errore connessione: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i callback dei bottoni"""
        query = update.callback_query
        await query.answer()
        
        # Simula i comandi in base al callback
        if query.data == "status":
            await self.status_command(update, context)
        elif query.data == "positions":
            await self.positions_command(update, context)
        elif query.data == "start_bot":
            await self.start_bot_command(update, context)
        elif query.data == "stop_bot":
            await self.stop_bot_command(update, context)
        elif query.data == "history":
            await self.history_command(update, context)
        elif query.data == "stats":
            await self.stats_command(update, context)
    
    def run(self):
        """Avvia il bot Telegram"""
        if not self.application:
            print("❌ Impossibile avviare Telegram Bot")
            return
        
        print("🚀 Avvio Telegram Bot...")
        self.application.run_polling()

def create_telegram_bot(token: str, dashboard_url: str = "http://localhost:5000") -> TradingBotTelegram:
    """Crea un'istanza del bot Telegram"""
    return TradingBotTelegram(token, dashboard_url)

if __name__ == "__main__":
    # Test standalone
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from config import TELEGRAM_TOKEN
    
    if TELEGRAM_TOKEN:
        bot = create_telegram_bot(TELEGRAM_TOKEN)
        bot.run()
    else:
        print("❌ TELEGRAM_TOKEN non configurato")
