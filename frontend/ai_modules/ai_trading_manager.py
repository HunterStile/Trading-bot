"""
AI Trading Manager - Orchestratore principale del sistema AI
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading
import time

from .ai_config import AIConfig
from .news_analyzer import NewsAnalyzer
from .macro_analyzer import MacroAnalyzer
from .openai_engine import OpenAIDecisionEngine

logger = logging.getLogger(__name__)

class AITradingManager:
    """Manager principale per il sistema AI di trading"""
    
    def __init__(self, trading_bot_instance=None):
        self.config = AIConfig()
        self.trading_bot = trading_bot_instance
        
        # Inizializza i moduli AI
        self.news_analyzer = NewsAnalyzer()
        self.macro_analyzer = MacroAnalyzer()
        self.openai_engine = OpenAIDecisionEngine()
        
        # Cache per evitare chiamate API eccessive
        self.cache = {}
        self.cache_ttl = 300  # 5 minuti
        
        # Flag per controllo
        self.is_running = False
        self.last_analysis_time = None
        
        logger.info("AI Trading Manager inizializzato")
    
    def validate_configuration(self) -> Dict:
        """Valida la configurazione AI"""
        missing_keys = self.config.validate_api_keys()
        
        validation_result = {
            'is_valid': len(missing_keys) == 0,
            'missing_keys': missing_keys,
            'modules_status': {
                'news_analyzer': True,
                'macro_analyzer': True,
                'openai_engine': bool(self.config.OPENAI_API_KEY)
            }
        }
        
        if missing_keys:
            logger.warning(f"Configurazione AI incompleta. Chiavi mancanti: {missing_keys}")
        else:
            logger.info("Configurazione AI validata con successo")
        
        return validation_result
    
    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Recupera dati dalla cache se ancora validi"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
        return None
    
    def set_cached_data(self, key: str, data: Dict):
        """Salva dati in cache"""
        self.cache[key] = (data, datetime.now())
    
    def analyze_market_conditions(self, symbol: str = "BTCUSDT") -> Dict:
        """Analisi completa delle condizioni di mercato"""
        try:
            logger.info(f"Inizio analisi AI per {symbol}")
            
            # Pulisci il simbolo per le API
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            
            analysis_results = {}
            
            # 1. Analisi Tecnica (dai dati del bot)
            technical_data = self._get_technical_data(symbol)
            analysis_results['technical_analysis'] = technical_data
            
            # 2. Analisi News
            cache_key_news = f"news_{clean_symbol}"
            news_data = self.get_cached_data(cache_key_news)
            if news_data is None:
                logger.info("Recupero dati news...")
                news_data = self.news_analyzer.get_news_summary(clean_symbol)
                self.set_cached_data(cache_key_news, news_data)
            analysis_results['news_analysis'] = news_data
            
            # 3. Analisi Macro
            cache_key_macro = "macro_data"
            macro_data = self.get_cached_data(cache_key_macro)
            if macro_data is None:
                logger.info("Recupero dati macro...")
                macro_data = self.macro_analyzer.get_macro_summary(clean_symbol)
                self.set_cached_data(cache_key_macro, macro_data)
            analysis_results['macro_analysis'] = macro_data
            
            # 4. Decisione AI
            logger.info("Generazione decisione AI...")
            ai_decision = self.openai_engine.analyze_trading_data(
                technical_data, news_data, macro_data, symbol
            )
            analysis_results['ai_decision'] = ai_decision
            
            # 5. Risk Assessment
            risk_assessment = self.openai_engine.get_risk_assessment(
                technical_data, news_data, macro_data
            )
            analysis_results['risk_assessment'] = risk_assessment
            
            # 6. Summary finale
            final_decision = self._generate_final_decision(analysis_results)
            analysis_results['final_decision'] = final_decision
            
            analysis_results['timestamp'] = datetime.now().isoformat()
            analysis_results['symbol'] = symbol
            
            self.last_analysis_time = datetime.now()
            
            logger.info(f"Analisi AI completata per {symbol}. Decisione: {final_decision['action']}")
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Errore nell'analisi AI: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'final_decision': {
                    'action': 'HOLD',
                    'confidence': 0,
                    'reasoning': f'Errore nell\'analisi: {e}'
                }
            }
    
    def _get_technical_data(self, symbol: str) -> Dict:
        """Recupera dati tecnici dal bot di trading"""
        try:
            if self.trading_bot and hasattr(self.trading_bot, 'get_technical_analysis'):
                return self.trading_bot.get_technical_analysis(symbol)
            
            # Dati di fallback se il bot non è disponibile
            return {
                'ema_trend': 'unknown',
                'current_price': 0,
                'candles_above_ema': 0,
                'candles_below_ema': 0,
                'volatility': 0,
                'volume_analysis': 'N/A',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nel recupero dati tecnici: {e}")
            return {
                'error': str(e),
                'ema_trend': 'unknown',
                'current_price': 0
            }
    
    def _generate_final_decision(self, analysis_results: Dict) -> Dict:
        """Genera la decisione finale combinando tutti gli input"""
        try:
            # Estrai decisioni dai vari moduli
            ai_decision = analysis_results.get('ai_decision', {})
            risk_assessment = analysis_results.get('risk_assessment', {})
            technical_analysis = analysis_results.get('technical_analysis', {})
            
            # Decisione base dall'AI
            base_decision = ai_decision.get('decision', 'HOLD')
            ai_confidence = ai_decision.get('confidence', 0) / 100.0
            
            # Applica pesi dalla configurazione
            technical_signal = 1 if technical_analysis.get('ema_trend') == 'bullish' else -1 if technical_analysis.get('ema_trend') == 'bearish' else 0
            
            news_sentiment = analysis_results.get('news_analysis', {}).get('sentiment_analysis', {})
            news_signal = 1 if news_sentiment.get('overall_sentiment') == 'bullish' else -1 if news_sentiment.get('overall_sentiment') == 'bearish' else 0
            
            macro_sentiment = analysis_results.get('macro_analysis', {}).get('macro_sentiment', {})
            macro_signal = 1 if macro_sentiment.get('overall_sentiment') == 'bullish' else -1 if macro_sentiment.get('overall_sentiment') == 'bearish' else 0
            
            # Calcola score pesato
            weighted_score = (
                technical_signal * self.config.TECHNICAL_WEIGHT +
                news_signal * self.config.SENTIMENT_WEIGHT +
                macro_signal * self.config.FUNDAMENTAL_WEIGHT
            )
            
            # Applica fattore rischio
            risk_level = risk_assessment.get('risk_level', 'MEDIUM')
            risk_multiplier = 0.5 if risk_level == 'HIGH' else 0.75 if risk_level == 'MEDIUM' else 1.0
            
            final_confidence = ai_confidence * risk_multiplier
            
            # Determina azione finale
            if base_decision == 'HOLD' or final_confidence < self.config.MIN_CONFIDENCE:
                final_action = 'HOLD'
                action_reasoning = "Confidenza insufficiente o segnale neutro"
            elif base_decision == 'BUY' and weighted_score > 0 and final_confidence >= self.config.MIN_CONFIDENCE:
                final_action = 'BUY'
                action_reasoning = "Segnali convergenti bullish con confidenza sufficiente"
            elif base_decision == 'SELL' and weighted_score < 0 and final_confidence >= self.config.MIN_CONFIDENCE:
                final_action = 'SELL'
                action_reasoning = "Segnali convergenti bearish con confidenza sufficiente"
            else:
                final_action = 'HOLD'
                action_reasoning = "Segnali contrastanti o rischio elevato"
            
            return {
                'action': final_action,
                'confidence': round(final_confidence * 100, 1),
                'reasoning': action_reasoning,
                'weighted_score': round(weighted_score, 2),
                'risk_level': risk_level,
                'component_signals': {
                    'technical': technical_signal,
                    'news': news_signal,
                    'macro': macro_signal,
                    'ai_base': base_decision
                },
                'position_size_recommendation': risk_assessment.get('max_position_size', 0.5),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nella generazione decisione finale: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Errore nel calcolo: {e}',
                'error': str(e)
            }
    
    def get_ai_status(self) -> Dict:
        """Ottieni stato del sistema AI"""
        config_validation = self.validate_configuration()
        
        return {
            'is_running': self.is_running,
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'configuration': config_validation,
            'cache_size': len(self.cache),
            'modules': {
                'news_analyzer': 'active',
                'macro_analyzer': 'active',
                'openai_engine': 'active' if self.config.OPENAI_API_KEY else 'disabled'
            }
        }
    
    def start_background_analysis(self, symbol: str = "BTCUSDT", interval_minutes: int = 15):
        """Avvia analisi AI in background"""
        if self.is_running:
            logger.warning("Analisi AI già in esecuzione")
            return
        
        self.is_running = True
        
        def background_worker():
            logger.info(f"Avviata analisi AI in background per {symbol} (ogni {interval_minutes} min)")
            
            while self.is_running:
                try:
                    analysis = self.analyze_market_conditions(symbol)
                    
                    # Log decisione importante
                    final_decision = analysis.get('final_decision', {})
                    if final_decision.get('action') != 'HOLD':
                        logger.info(f"🤖 AI SIGNAL: {final_decision['action']} {symbol} "
                                  f"(confidenza: {final_decision['confidence']}%) - "
                                  f"{final_decision['reasoning']}")
                    
                    # Attendi prima della prossima analisi
                    time.sleep(interval_minutes * 60)
                    
                except Exception as e:
                    logger.error(f"Errore nell'analisi background: {e}")
                    time.sleep(60)  # Attesa ridotta in caso di errore
        
        # Avvia il worker in un thread separato
        thread = threading.Thread(target=background_worker, daemon=True)
        thread.start()
        
        logger.info("Thread di analisi AI avviato")
    
    def stop_background_analysis(self):
        """Ferma l'analisi in background"""
        self.is_running = False
        logger.info("Analisi AI in background fermata")
