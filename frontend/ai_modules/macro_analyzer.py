"""
Macro Economic Data Analyzer per AI Trading System
"""
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from .ai_config import AIConfig

logger = logging.getLogger(__name__)

class MacroAnalyzer:
    """Analizzatore di dati macro economici"""
    
    def __init__(self):
        self.config = AIConfig()
        self.session = requests.Session()
        
    def get_market_indicators(self) -> Dict:
        """Recupera indicatori di mercato chiave"""
        try:
            indicators_data = {}
            
            for symbol in self.config.KEY_INDICATORS:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d", interval="1d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                        change_pct = ((current_price - prev_price) / prev_price) * 100
                        
                        # Calcola volatilità (std degli ultimi 5 giorni)
                        volatility = hist['Close'].pct_change().std() * 100
                        
                        indicators_data[symbol] = {
                            'current_price': round(current_price, 4),
                            'change_24h': round(change_pct, 2),
                            'volatility': round(volatility, 2),
                            'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                            'last_updated': datetime.now().isoformat()
                        }
                        
                    logger.info(f"Dati recuperati per {symbol}")
                    
                except Exception as e:
                    logger.error(f"Errore nel recupero dati per {symbol}: {e}")
                    continue
            
            return indicators_data
            
        except Exception as e:
            logger.error(f"Errore nel recupero indicatori di mercato: {e}")
            return {}
    
    def get_crypto_correlations(self, symbol: str = "BTC-USD") -> Dict:
        """Calcola correlazioni tra crypto e asset tradizionali"""
        try:
            # Lista asset per correlazione
            assets = [symbol, "^GSPC", "^IXIC", "GC=F", "^TNX", "DX-Y.NYB"]
            
            # Recupera dati storici (30 giorni)
            data = {}
            for asset in assets:
                try:
                    ticker = yf.Ticker(asset)
                    hist = ticker.history(period="30d", interval="1d")
                    if not hist.empty:
                        data[asset] = hist['Close']
                except:
                    continue
            
            if len(data) < 2:
                return {'error': 'Dati insufficienti per calcolare correlazioni'}
            
            # Crea DataFrame e calcola correlazioni
            df = pd.DataFrame(data)
            df = df.dropna()
            
            correlations = df.corr()[symbol].to_dict()
            
            # Rimuovi auto-correlazione
            correlations.pop(symbol, None)
            
            # Interpreta correlazioni
            correlation_analysis = {}
            for asset, corr in correlations.items():
                if abs(corr) > 0.7:
                    strength = "strong"
                elif abs(corr) > 0.3:
                    strength = "moderate"
                else:
                    strength = "weak"
                
                direction = "positive" if corr > 0 else "negative"
                
                correlation_analysis[asset] = {
                    'correlation': round(corr, 3),
                    'strength': strength,
                    'direction': direction
                }
            
            return {
                'correlations': correlation_analysis,
                'analysis_period': '30 days',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nel calcolo correlazioni: {e}")
            return {'error': str(e)}
    
    def get_fed_data(self) -> Dict:
        """Recupera dati economici USA dalla FRED API"""
        try:
            if not self.config.FRED_API_KEY:
                return {'error': 'FRED API key non configurata'}
            
            base_url = "https://api.stlouisfed.org/fred/series/observations"
            
            # Indicatori chiave da monitorare
            indicators = {
                'FEDFUNDS': 'Federal Funds Rate',
                'UNRATE': 'Unemployment Rate',
                'CPIAUCSL': 'Consumer Price Index',
                'GDP': 'Gross Domestic Product'
            }
            
            fed_data = {}
            
            for series_id, description in indicators.items():
                try:
                    params = {
                        'series_id': series_id,
                        'api_key': self.config.FRED_API_KEY,
                        'file_type': 'json',
                        'limit': 1,
                        'sort_order': 'desc'
                    }
                    
                    response = self.session.get(base_url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        observations = data.get('observations', [])
                        
                        if observations:
                            latest = observations[0]
                            fed_data[series_id] = {
                                'description': description,
                                'value': float(latest['value']) if latest['value'] != '.' else None,
                                'date': latest['date'],
                                'units': data.get('units', 'N/A')
                            }
                    
                except Exception as e:
                    logger.error(f"Errore nel recupero {series_id}: {e}")
                    continue
            
            return {
                'fed_indicators': fed_data,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nel recupero dati FED: {e}")
            return {'error': str(e)}
    
    def analyze_macro_sentiment(self, indicators_data: Dict, correlations: Dict) -> Dict:
        """Analizza sentiment macro economico"""
        try:
            risk_factors = []
            bullish_factors = []
            bearish_factors = []
            
            # Analizza DXY (Dollar Index)
            if 'DXY' in indicators_data:
                dxy_change = indicators_data['DXY']['change_24h']
                if dxy_change > 1:
                    bearish_factors.append(f"DXY forte (+{dxy_change:.1f}%) - negativo per crypto")
                elif dxy_change < -1:
                    bullish_factors.append(f"DXY debole ({dxy_change:.1f}%) - positivo per crypto")
            
            # Analizza VIX (Fear Index)
            if '^VIX' in indicators_data:
                vix_price = indicators_data['^VIX']['current_price']
                if vix_price > 30:
                    bearish_factors.append(f"VIX elevato ({vix_price:.1f}) - alta volatilità mercati")
                elif vix_price < 20:
                    bullish_factors.append(f"VIX basso ({vix_price:.1f}) - mercati stabili")
            
            # Analizza Treasury Yields
            if '^TNX' in indicators_data:
                tnx_change = indicators_data['^TNX']['change_24h']
                if tnx_change > 3:
                    bearish_factors.append(f"Yields in rialzo (+{tnx_change:.1f}%) - pressione su risk assets")
                elif tnx_change < -3:
                    bullish_factors.append(f"Yields in calo ({tnx_change:.1f}%) - favorevole per risk assets")
            
            # Analizza Gold
            if 'GC=F' in indicators_data:
                gold_change = indicators_data['GC=F']['change_24h']
                if gold_change > 2:
                    risk_factors.append(f"Oro in rialzo (+{gold_change:.1f}%) - flight to safety")
                elif gold_change < -2:
                    bullish_factors.append(f"Oro in calo ({gold_change:.1f}%) - risk-on sentiment")
            
            # Calcola sentiment score
            bullish_score = len(bullish_factors)
            bearish_score = len(bearish_factors)
            risk_score = len(risk_factors)
            
            total_factors = bullish_score + bearish_score + risk_score
            
            if total_factors == 0:
                overall_sentiment = "neutral"
                confidence = 0.5
            else:
                net_score = (bullish_score - bearish_score - risk_score) / total_factors
                
                if net_score > 0.3:
                    overall_sentiment = "bullish"
                elif net_score < -0.3:
                    overall_sentiment = "bearish"
                else:
                    overall_sentiment = "neutral"
                
                confidence = min(abs(net_score) + 0.5, 1.0)
            
            return {
                'overall_sentiment': overall_sentiment,
                'confidence': round(confidence, 2),
                'bullish_factors': bullish_factors,
                'bearish_factors': bearish_factors,
                'risk_factors': risk_factors,
                'sentiment_score': round(net_score if total_factors > 0 else 0, 2),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nell'analisi sentiment macro: {e}")
            return {
                'overall_sentiment': 'neutral',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def get_macro_summary(self, symbol: str = "BTC") -> Dict:
        """Ottieni summary completo dei dati macro"""
        try:
            # Recupera dati
            indicators = self.get_market_indicators()
            correlations = self.get_crypto_correlations(f"{symbol}-USD")
            fed_data = self.get_fed_data()
            
            # Analizza sentiment
            macro_sentiment = self.analyze_macro_sentiment(indicators, correlations)
            
            return {
                'market_indicators': indicators,
                'correlations': correlations,
                'fed_data': fed_data,
                'macro_sentiment': macro_sentiment,
                'last_updated': datetime.now().isoformat(),
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Errore nel summary macro: {e}")
            return {
                'error': str(e),
                'macro_sentiment': {
                    'overall_sentiment': 'neutral',
                    'confidence': 0.0
                }
            }
