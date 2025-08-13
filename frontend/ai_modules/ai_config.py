"""
Configurazione AI Trading System
"""
import os
from datetime import datetime

class AIConfig:
    """Configurazione per il sistema AI"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = "gpt-4"
    MAX_TOKENS = 1000
    
    # News APIs
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
    CRYPTOPANIC_TOKEN = os.getenv('CRYPTOPANIC_TOKEN', '')
    
    # Economic Data APIs  
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')
    FRED_API_KEY = os.getenv('FRED_API_KEY', '')
    
    # AI Decision Weights
    TECHNICAL_WEIGHT = 0.4      # Peso analisi tecnica (EMA)
    FUNDAMENTAL_WEIGHT = 0.3    # Peso analisi fondamentale
    SENTIMENT_WEIGHT = 0.2      # Peso sentiment analysis
    RISK_WEIGHT = 0.1          # Peso risk assessment
    
    # AI Confidence Thresholds
    MIN_CONFIDENCE = 0.6       # Confidenza minima per trade
    HIGH_CONFIDENCE = 0.8      # Confidenza alta
    
    # News Analysis Settings
    NEWS_LOOKBACK_HOURS = 24   # Ore di news da analizzare
    MAX_NEWS_ARTICLES = 20     # Max articoli per analisi
    
    # Sentiment Keywords
    BULLISH_KEYWORDS = [
        'pump', 'moon', 'bullish', 'buy', 'green', 'up', 'rise',
        'adoption', 'institutional', 'etf', 'breakout', 'support'
    ]
    
    BEARISH_KEYWORDS = [
        'dump', 'crash', 'bearish', 'sell', 'red', 'down', 'fall',
        'regulation', 'ban', 'hack', 'breakdown', 'resistance'
    ]
    
    # Economic Indicators
    KEY_INDICATORS = [
        'DXY',           # US Dollar Index
        '^VIX',          # Volatility Index
        '^TNX',          # 10Y Treasury Yield
        'GC=F',          # Gold Futures
        'CL=F'           # Oil Futures
    ]
    
    @classmethod
    def validate_api_keys(cls):
        """Valida che le API keys siano configurate"""
        missing_keys = []
        
        if not cls.OPENAI_API_KEY:
            missing_keys.append('OPENAI_API_KEY')
        if not cls.NEWS_API_KEY:
            missing_keys.append('NEWS_API_KEY')
            
        return missing_keys
    
    @classmethod
    def get_analysis_prompt_template(cls):
        """Template per il prompt di analisi AI"""
        return """
        Sei un esperto trader quantitativo. Analizza questi dati per {symbol}:

        ANALISI TECNICA:
        - Trend EMA: {ema_trend}
        - Prezzo corrente: ${current_price}
        - Candele sopra/sotto EMA: {candles_data}
        - Supporti/Resistenze: {levels}

        ANALISI FONDAMENTALE:
        - Notizie recenti: {news_summary}
        - Sentiment score: {sentiment_score}
        - Indicatori macro: {macro_data}

        ANALISI RISCHIO:
        - Volatilità: {volatility}
        - Volumi: {volume_data}
        - Correlazioni: {correlations}

        Fornisci:
        1. DECISIONE: BUY/SELL/HOLD
        2. CONFIDENZA: 0-100%
        3. REASONING: Spiegazione breve
        4. RISK_LEVEL: LOW/MEDIUM/HIGH
        5. TIME_HORIZON: SHORT/MEDIUM/LONG

        Rispondi in formato JSON:
        {{
            "decision": "BUY/SELL/HOLD",
            "confidence": 75,
            "reasoning": "Analisi tecnica bullish supportata da sentiment positivo...",
            "risk_level": "MEDIUM",
            "time_horizon": "SHORT",
            "key_factors": ["ema_trend", "news_sentiment", "macro_data"]
        }}
        """
