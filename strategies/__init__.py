"""
Strategies Package
Contiene tutte le strategie di trading
"""

from .base_strategy import BaseStrategy
from .ema_strategy import EMAStrategy

__all__ = ['BaseStrategy', 'EMAStrategy']
