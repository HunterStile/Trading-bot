"""
News Analysis Module per AI Trading System
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from .ai_config import AIConfig

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    """Analizzatore di notizie crypto e macro"""
    
    def __init__(self):
        self.config = AIConfig()
        self.session = requests.Session()
        
    def get_crypto_news(self, symbol: str = "BTC", hours_back: int = 24) -> List[Dict]:
        """Recupera notizie crypto da CryptoPanic"""
        try:
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': self.config.CRYPTOPANIC_TOKEN,
                'public': 'true',
                'currencies': symbol.replace('USDT', ''),
                'filter': 'hot',
                'kind': 'news'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                news_items = []
                
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                for item in data.get('results', [])[:self.config.MAX_NEWS_ARTICLES]:
                    created_at = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
                    
                    if created_at >= cutoff_time:
                        news_items.append({
                            'title': item['title'],
                            'url': item['url'],
                            'published_at': item['created_at'],
                            'votes': item.get('votes', {}).get('positive', 0),
                            'source': item.get('source', {}).get('domain', 'cryptopanic'),
                            'kind': item.get('kind', 'news')
                        })
                
                logger.info(f"Recuperate {len(news_items)} notizie per {symbol}")
                return news_items
                
            else:
                logger.error(f"Errore CryptoPanic API: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Errore nel recupero notizie crypto: {e}")
            return []
    
    def get_general_news(self, query: str = "bitcoin cryptocurrency", hours_back: int = 24) -> List[Dict]:
        """Recupera notizie generali da NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            
            from_date = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
            
            params = {
                'apiKey': self.config.NEWS_API_KEY,
                'q': query,
                'from': from_date,
                'sortBy': 'popularity',
                'language': 'en',
                'pageSize': 20
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                news_items = []
                
                for item in data.get('articles', []):
                    if item.get('title') and item.get('description'):
                        news_items.append({
                            'title': item['title'],
                            'description': item['description'],
                            'url': item['url'],
                            'published_at': item['publishedAt'],
                            'source': item['source']['name'],
                            'kind': 'general_news'
                        })
                
                logger.info(f"Recuperate {len(news_items)} notizie generali")
                return news_items
                
            else:
                logger.error(f"Errore NewsAPI: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Errore nel recupero notizie generali: {e}")
            return []
    
    def analyze_sentiment(self, news_items: List[Dict]) -> Dict:
        """Analizza sentiment delle notizie"""
        if not news_items:
            return {
                'overall_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_articles': 0
            }
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        sentiment_scores = []
        
        for item in news_items:
            text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            
            # Conta keywords bullish/bearish
            bullish_matches = sum(1 for keyword in self.config.BULLISH_KEYWORDS if keyword in text)
            bearish_matches = sum(1 for keyword in self.config.BEARISH_KEYWORDS if keyword in text)
            
            # Calcola sentiment score per articolo
            if bullish_matches > bearish_matches:
                sentiment_scores.append(1)
                positive_count += 1
            elif bearish_matches > bullish_matches:
                sentiment_scores.append(-1)
                negative_count += 1
            else:
                sentiment_scores.append(0)
                neutral_count += 1
        
        # Calcola sentiment complessivo
        overall_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        if overall_score > 0.2:
            overall_sentiment = 'bullish'
        elif overall_score < -0.2:
            overall_sentiment = 'bearish'
        else:
            overall_sentiment = 'neutral'
        
        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_score': round(overall_score, 2),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_articles': len(news_items),
            'confidence': min(abs(overall_score) * 2, 1.0)  # Confidenza basata su intensità sentiment
        }
    
    def get_news_summary(self, symbol: str = "BTC") -> Dict:
        """Ottieni summary completo delle notizie"""
        try:
            # Recupera notizie crypto e generali
            crypto_news = self.get_crypto_news(symbol, self.config.NEWS_LOOKBACK_HOURS)
            general_news = self.get_general_news(f"{symbol} bitcoin cryptocurrency", self.config.NEWS_LOOKBACK_HOURS)
            
            all_news = crypto_news + general_news
            
            # Analizza sentiment
            sentiment_analysis = self.analyze_sentiment(all_news)
            
            # Top headlines
            top_headlines = []
            for item in all_news[:5]:
                top_headlines.append({
                    'title': item['title'],
                    'source': item['source'],
                    'published_at': item['published_at']
                })
            
            return {
                'total_articles': len(all_news),
                'crypto_articles': len(crypto_news),
                'general_articles': len(general_news),
                'sentiment_analysis': sentiment_analysis,
                'top_headlines': top_headlines,
                'last_updated': datetime.now().isoformat(),
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Errore nel summary notizie: {e}")
            return {
                'total_articles': 0,
                'sentiment_analysis': {
                    'overall_sentiment': 'neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0
                },
                'error': str(e)
            }
