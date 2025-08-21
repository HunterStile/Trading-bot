"""
Trading Engine Module
====================

Contiene le classi per gestire:
- TradingEngine: Motore principale del trading
- TradingService: Service layer per coordinare trading e notifiche
- SessionManager: Gestione sessioni di trading (future)
- PositionManager: Gestione posizioni aperte (future)
- SignalProcessor: Elaborazione segnali di trading (future)
"""

from .engine import TradingEngine
from .service import TradingService

# Questi saranno creati nei prossimi step
# from .session_manager import SessionManager
# from .position_manager import PositionManager
# from .signal_processor import SignalProcessor

__all__ = [
    'TradingEngine',
    'TradingService'
    # 'SessionManager', 
    # 'PositionManager',
    # 'SignalProcessor'
]
