"""
Notifications Module
====================

Contiene le classi per gestire:
- WebSocketManager: Gestione WebSocket
- TelegramNotifier: Notifiche Telegram (future)
- AlertSystem: Sistema di alert (future)
"""

from .websocket import WebSocketManager

# Questi saranno creati nei prossimi step
# from .telegram import TelegramNotifier
# from .alerts import AlertSystem

__all__ = [
    'WebSocketManager'
    # 'TelegramNotifier',
    # 'AlertSystem'
]
