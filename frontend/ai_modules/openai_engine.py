"""
OpenAI Decision Engine per AI Trading System
"""
import openai
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging
from .ai_config import AIConfig

logger = logging.getLogger(__name__)

class OpenAIDecisionEngine:
    """Engine di decisione basato su OpenAI GPT"""
    
    def __init__(self):
        self.config = AIConfig()
        if self.config.OPENAI_API_KEY:
            openai.api_key = self.config.OPENAI_API_KEY
        else:
            logger.warning("OpenAI API key non configurata")
    
    def analyze_trading_data(self, 
                           technical_data: Dict,
                           news_data: Dict,
                           macro_data: Dict,
                           symbol: str) -> Dict:
        """Analizza tutti i dati e fornisce decisione di trading"""
        
        if not self.config.OPENAI_API_KEY:
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'reasoning': 'OpenAI API non configurata',
                'error': 'Missing API key'
            }
        
        try:
            # Prepara i dati per il prompt
            prompt_data = self._prepare_prompt_data(technical_data, news_data, macro_data, symbol)
            
            # Crea il prompt usando il template
            prompt = self.config.get_analysis_prompt_template().format(**prompt_data)
            
            logger.info(f"Invio richiesta a OpenAI per analisi di {symbol}")
            
            # Chiamata a OpenAI
            response = openai.ChatCompletion.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un esperto trader quantitativo con 20 anni di esperienza. Analizza i dati forniti e dai una raccomandazione precisa e motivata."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.config.MAX_TOKENS,
                temperature=0.3  # Bassa temperatura per risposte più consistenti
            )
            
            # Estrai la risposta
            ai_response = response.choices[0].message.content
            
            # Prova a parsare come JSON
            try:
                decision_data = json.loads(ai_response)
            except json.JSONDecodeError:
                # Se non è JSON valido, prova a estrarre informazioni
                decision_data = self._parse_text_response(ai_response)
            
            # Valida e normalizza la risposta
            validated_decision = self._validate_decision(decision_data)
            
            # Aggiungi metadati
            validated_decision.update({
                'timestamp': datetime.now().isoformat(),
                'model_used': self.config.OPENAI_MODEL,
                'symbol': symbol,
                'input_data_summary': {
                    'technical_trend': technical_data.get('ema_trend', 'unknown'),
                    'news_sentiment': news_data.get('sentiment_analysis', {}).get('overall_sentiment', 'neutral'),
                    'macro_sentiment': macro_data.get('macro_sentiment', {}).get('overall_sentiment', 'neutral')
                }
            })
            
            logger.info(f"Decisione AI per {symbol}: {validated_decision['decision']} (confidenza: {validated_decision['confidence']}%)")
            
            return validated_decision
            
        except Exception as e:
            logger.error(f"Errore nell'analisi OpenAI: {e}")
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'reasoning': f'Errore nell\'analisi AI: {str(e)}',
                'risk_level': 'HIGH',
                'time_horizon': 'SHORT',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_prompt_data(self, technical_data: Dict, news_data: Dict, macro_data: Dict, symbol: str) -> Dict:
        """Prepara i dati per il prompt di OpenAI"""
        
        # Dati tecnici
        ema_trend = technical_data.get('ema_trend', 'unknown')
        current_price = technical_data.get('current_price', 0)
        candles_above_ema = technical_data.get('candles_above_ema', 0)
        candles_below_ema = technical_data.get('candles_below_ema', 0)
        
        # Sentiment notizie
        news_sentiment = news_data.get('sentiment_analysis', {})
        news_summary = f"Sentiment: {news_sentiment.get('overall_sentiment', 'neutral')} " \
                      f"(Score: {news_sentiment.get('sentiment_score', 0)}, " \
                      f"Articoli: {news_data.get('total_articles', 0)})"
        
        # Dati macro
        macro_sentiment_data = macro_data.get('macro_sentiment', {})
        macro_summary = f"Sentiment: {macro_sentiment_data.get('overall_sentiment', 'neutral')} " \
                       f"(Confidenza: {macro_sentiment_data.get('confidence', 0)})"
        
        # Indicatori macro chiave
        indicators = macro_data.get('market_indicators', {})
        dxy_change = indicators.get('DXY', {}).get('change_24h', 0)
        vix_price = indicators.get('^VIX', {}).get('current_price', 0)
        
        return {
            'symbol': symbol,
            'ema_trend': ema_trend,
            'current_price': current_price,
            'candles_data': f"Sopra EMA: {candles_above_ema}, Sotto EMA: {candles_below_ema}",
            'levels': "Da implementare", # TODO: aggiungi supporti/resistenze
            'news_summary': news_summary,
            'sentiment_score': news_sentiment.get('sentiment_score', 0),
            'macro_data': f"{macro_summary}, DXY: {dxy_change:+.1f}%, VIX: {vix_price:.1f}",
            'volatility': technical_data.get('volatility', 'N/A'),
            'volume_data': technical_data.get('volume_analysis', 'N/A'),
            'correlations': "Da implementare" # TODO: aggiungi correlazioni
        }
    
    def _parse_text_response(self, response_text: str) -> Dict:
        """Cerca di estrarre decisione da risposta testuale"""
        response_lower = response_text.lower()
        
        # Cerca decisione
        decision = 'HOLD'
        if 'buy' in response_lower or 'long' in response_lower:
            decision = 'BUY'
        elif 'sell' in response_lower or 'short' in response_lower:
            decision = 'SELL'
        
        # Cerca confidenza (pattern come "80%" o "confidenza: 75")
        import re
        confidence_match = re.search(r'(\d{1,3})%', response_text)
        confidence = int(confidence_match.group(1)) if confidence_match else 50
        
        # Cerca livello di rischio
        risk_level = 'MEDIUM'
        if 'low risk' in response_lower or 'basso rischio' in response_lower:
            risk_level = 'LOW'
        elif 'high risk' in response_lower or 'alto rischio' in response_lower:
            risk_level = 'HIGH'
        
        return {
            'decision': decision,
            'confidence': confidence,
            'reasoning': response_text[:200] + "..." if len(response_text) > 200 else response_text,
            'risk_level': risk_level,
            'time_horizon': 'SHORT'
        }
    
    def _validate_decision(self, decision_data: Dict) -> Dict:
        """Valida e normalizza la decisione AI"""
        
        # Decisione valida
        valid_decisions = ['BUY', 'SELL', 'HOLD']
        decision = decision_data.get('decision', 'HOLD').upper()
        if decision not in valid_decisions:
            decision = 'HOLD'
        
        # Confidenza valida (0-100)
        confidence = decision_data.get('confidence', 50)
        try:
            confidence = max(0, min(100, int(confidence)))
        except:
            confidence = 50
        
        # Risk level valido
        valid_risk_levels = ['LOW', 'MEDIUM', 'HIGH']
        risk_level = decision_data.get('risk_level', 'MEDIUM').upper()
        if risk_level not in valid_risk_levels:
            risk_level = 'MEDIUM'
        
        # Time horizon valido
        valid_horizons = ['SHORT', 'MEDIUM', 'LONG']
        time_horizon = decision_data.get('time_horizon', 'SHORT').upper()
        if time_horizon not in valid_horizons:
            time_horizon = 'SHORT'
        
        return {
            'decision': decision,
            'confidence': confidence,
            'reasoning': decision_data.get('reasoning', 'Analisi AI completata'),
            'risk_level': risk_level,
            'time_horizon': time_horizon,
            'key_factors': decision_data.get('key_factors', [])
        }
    
    def get_risk_assessment(self, 
                          technical_data: Dict, 
                          news_data: Dict, 
                          macro_data: Dict) -> Dict:
        """Valutazione del rischio separata"""
        
        try:
            risk_factors = []
            risk_score = 0
            
            # Rischio tecnico
            volatility = technical_data.get('volatility', 0)
            if volatility > 5:  # Alta volatilità
                risk_factors.append(f"Alta volatilità tecnica: {volatility:.1f}%")
                risk_score += 2
            
            # Rischio news
            news_sentiment = news_data.get('sentiment_analysis', {})
            if news_sentiment.get('confidence', 0) < 0.3:
                risk_factors.append("Sentiment news incerto")
                risk_score += 1
            
            # Rischio macro
            macro_sentiment = macro_data.get('macro_sentiment', {})
            bearish_factors = len(macro_sentiment.get('bearish_factors', []))
            if bearish_factors > 2:
                risk_factors.append(f"Molteplici fattori macro negativi: {bearish_factors}")
                risk_score += 2
            
            # Determina livello di rischio
            if risk_score >= 4:
                risk_level = 'HIGH'
            elif risk_score >= 2:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'max_position_size': 0.5 if risk_level == 'HIGH' else 0.75 if risk_level == 'MEDIUM' else 1.0
            }
            
        except Exception as e:
            logger.error(f"Errore nella valutazione rischio: {e}")
            return {
                'risk_level': 'HIGH',
                'risk_score': 5,
                'risk_factors': [f"Errore nel calcolo rischio: {e}"],
                'max_position_size': 0.25
            }
