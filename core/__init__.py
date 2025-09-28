"""
🤖 Trading Bot Core Package

Questo package contiene la logica business centrale del trading bot,
ottimizzata per l'architettura multi-tenant SaaS.

Modules:
    config: Configurazioni API e parametri sistema
    trading_functions: Funzioni principali di trading e analisi
"""

from .config import *
# from .trading_functions import *  # Disabled for dashboard containers (requires selenium)

__version__ = "2.0.0"
__author__ = "Trading Bot Team"
__description__ = "Core trading logic for multi-tenant SaaS platform"