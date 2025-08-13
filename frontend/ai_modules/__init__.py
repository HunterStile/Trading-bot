"""
AI Trading Modules
Sistema di trading basato su AI che combina analisi tecnica, fondamentale e sentiment
"""

__version__ = "1.0.0"
__author__ = "HunterStile Trading Bot"

# Import dei moduli principali
from .ai_config import AIConfig
from .news_analyzer import NewsAnalyzer
from .macro_analyzer import MacroAnalyzer
from .openai_engine import OpenAIDecisionEngine
from .ai_trading_manager import AITradingManager

# Esporta le classi principali
__all__ = [
    'AIConfig',
    'NewsAnalyzer', 
    'MacroAnalyzer',
    'OpenAIDecisionEngine',
    'AITradingManager'
]
