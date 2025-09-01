import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from textblob import TextBlob
import time
import json
from typing import Dict, List, Tuple, Optional

class AutomatedCoinSelector:
    """Sistema automatico per selezione e attivazione trading bot"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.coin_pool = config.get('coin_pool', ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'MATIC', 'DOT', 'AVAX'])
        self.min_score_threshold = config.get('min_score_threshold', 75)
        self.max_concurrent_bots = config.get('max_concurrent_bots', 3)
        self.scan_interval = config.get('scan_interval', 300)  # 5 minuti
        
        # Pesi per scoring
        self.weights = {
            'volume_spike': 0.25,
            'price_momentum': 0.20,
            'social_sentiment': 0.20,
            'technical_setup': 0.15,
            'volatility_score': 0.10,
            'news_sentiment': 0.10
        }
        
        self.active_bots = {}
        
    def scan_and_select_coins(self) -> List[Tuple[str, float]]:
        """Scansiona il pool di monete e restituisce quelle con score più alto"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scansione pool di {len(self.coin_pool)} monete...")
        
        coin_scores = []
        
        for symbol in self.coin_pool:
            try:
                score = self.calculate_coin_score(symbol)
                if score >= self.min_score_threshold:
                    coin_scores.append((symbol, score))
                    print(f"[SCANNER] {symbol}: Score {score:.1f}")
                
            except Exception as e:
                print(f"[SCANNER] Errore analisi {symbol}: {e}")
        
        # Ordina per score decrescente
        coin_scores.sort(key=lambda x: x[1], reverse=True)
        return coin_scores
    
    def calculate_coin_score(self, symbol: str) -> float:
        """Calcola score complessivo per una moneta"""
        scores = {
            'volume_spike': self.analyze_volume_spike(symbol),
            'price_momentum': self.analyze_price_momentum(symbol),
            'social_sentiment': self.analyze_social_sentiment(symbol),
            'technical_setup': self.analyze_technical_setup(symbol),
            'volatility_score': self.analyze_volatility(symbol),
            'news_sentiment': self.analyze_news_sentiment(symbol)
        }
        
        # Calcola score ponderato
        total_score = sum(scores[key] * self.weights[key] for key in scores.keys())
        
        print(f"[SCORE] {symbol} - Volume: {scores['volume_spike']:.1f}, "
              f"Momentum: {scores['price_momentum']:.1f}, "
              f"Social: {scores['social_sentiment']:.1f}, "
              f"Tech: {scores['technical_setup']:.1f} = {total_score:.1f}")
        
        return total_score
    
    def analyze_volume_spike(self, symbol: str) -> float:
        """Analizza spike di volume (0-100)"""
        try:
            # Ottieni dati volume ultimi 24h vs media 7 giorni
            current_volume = self.get_current_volume(symbol)
            avg_volume = self.get_average_volume(symbol, days=7)
            
            if avg_volume == 0:
                return 0
            
            volume_ratio = current_volume / avg_volume
            
            # Scoring basato su ratio
            if volume_ratio >= 3.0:
                return 100
            elif volume_ratio >= 2.0:
                return 80
            elif volume_ratio >= 1.5:
                return 60
            elif volume_ratio >= 1.2:
                return 40
            else:
                return 20
                
        except Exception:
            return 0
    
    def analyze_price_momentum(self, symbol: str) -> float:
        """Analizza momentum prezzo (0-100)"""
        try:
            # Ottieni variazioni prezzo su diversi timeframe
            price_1h = self.get_price_change(symbol, '1h')
            price_4h = self.get_price_change(symbol, '4h')
            price_24h = self.get_price_change(symbol, '24h')
            
            # Score basato su momentum positivo crescente
            momentum_score = 0
            
            if price_1h > 0 and price_4h > 0 and price_24h > 0:
                # Momentum positivo su tutti i timeframe
                momentum_score = 80 + min(20, abs(price_4h) * 2)
            elif price_4h > 3:  # Strong 4h momentum
                momentum_score = 70
            elif price_24h > 5:  # Strong daily momentum
                momentum_score = 60
            elif price_1h > 2:  # Short term spike
                momentum_score = 50
            else:
                momentum_score = max(0, 30 + price_24h)
            
            return min(100, max(0, momentum_score))
            
        except Exception:
            return 0
    
    def analyze_social_sentiment(self, symbol: str) -> float:
        """Analizza sentiment social media (0-100)"""
        try:
            # Simula analisi sentiment da Twitter/Reddit
            # In realtà useresti API come LunarCrush, CoinGecko Social, etc.
            
            mentions_count = self.get_social_mentions(symbol)
            sentiment_score = self.get_social_sentiment_score(symbol)
            
            # Combina menzioni e sentiment
            if mentions_count > 1000 and sentiment_score > 0.6:
                return 90
            elif mentions_count > 500 and sentiment_score > 0.4:
                return 70
            elif mentions_count > 100:
                return 50
            else:
                return 30
                
        except Exception:
            return 50  # Neutrale se non disponibile
    
    def analyze_technical_setup(self, symbol: str) -> float:
        """Analizza setup tecnico per EMA strategy (0-100)"""
        try:
            # Ottieni dati candele per analisi tecnica
            klines = self.get_kline_data(symbol, '4h', 50)
            if not klines:
                return 0
            
            closes = [float(k[4]) for k in klines]
            current_price = closes[-1]
            
            # Calcola EMA
            ema_10 = self.calculate_ema(closes, 10)
            ema_20 = self.calculate_ema(closes, 20)
            
            if not ema_10 or not ema_20:
                return 0
            
            ema_10_current = ema_10[-1]
            ema_20_current = ema_20[-1]
            
            score = 0
            
            # Trend alignment
            if ema_10_current > ema_20_current:  # Uptrend
                score += 40
            
            # Distanza da EMA ottimale
            distance_from_ema = abs((current_price - ema_10_current) / ema_10_current * 100)
            if distance_from_ema <= 2:  # Vicino alla EMA
                score += 30
            elif distance_from_ema <= 5:
                score += 20
            
            # Volume pattern
            volumes = [float(k[5]) for k in klines[-5:]]
            if volumes[-1] > np.mean(volumes[:-1]):
                score += 30
            
            return min(100, score)
            
        except Exception:
            return 0
    
    def analyze_volatility(self, symbol: str) -> float:
        """Analizza volatilità ottimale (0-100)"""
        try:
            # Calcola ATR% per valutare volatilità
            klines = self.get_kline_data(symbol, '4h', 20)
            if not klines:
                return 0
            
            atr_values = []
            for i in range(1, len(klines)):
                high = float(klines[i][2])
                low = float(klines[i][3])
                prev_close = float(klines[i-1][4])
                
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                atr_values.append(tr)
            
            if not atr_values:
                return 0
            
            avg_atr = np.mean(atr_values)
            current_price = float(klines[-1][4])
            atr_percent = (avg_atr / current_price) * 100
            
            # Score basato su volatilità ottimale per trading
            if 1.5 <= atr_percent <= 4.0:  # Sweet spot
                return 90
            elif 1.0 <= atr_percent <= 6.0:
                return 70
            elif atr_percent <= 8.0:
                return 50
            else:
                return 20  # Troppo volatile
                
        except Exception:
            return 50
    
    def analyze_news_sentiment(self, symbol: str) -> float:
        """Analizza sentiment notizie recenti (0-100)"""
        try:
            # Simula analisi notizie (useresti NewsAPI, CoinGecko News, etc.)
            recent_news = self.get_recent_news(symbol)
            
            if not recent_news:
                return 50  # Neutrale se no news
            
            sentiments = []
            for news in recent_news:
                sentiment = TextBlob(news['title'] + " " + news.get('description', '')).sentiment.polarity
                sentiments.append(sentiment)
            
            avg_sentiment = np.mean(sentiments)
            
            # Converti in score 0-100
            if avg_sentiment > 0.3:
                return 85
            elif avg_sentiment > 0.1:
                return 70
            elif avg_sentiment > -0.1:
                return 50
            else:
                return 30
                
        except Exception:
            return 50
    
    def should_activate_bot(self, symbol: str, score: float) -> bool:
        """Determina se attivare bot per questa moneta"""
        # Non attivare se già abbiamo troppi bot attivi
        if len(self.active_bots) >= self.max_concurrent_bots:
            return False
        
        # Non attivare se bot già attivo su questo symbol
        if symbol in self.active_bots:
            return False
        
        # Score sopra soglia
        if score < self.min_score_threshold:
            return False
        
        # Verifica condizioni aggiuntive specifiche
        return self.additional_activation_checks(symbol)
    
    def additional_activation_checks(self, symbol: str) -> bool:
        """Controlli aggiuntivi prima di attivare bot"""
        try:
            # Controlla se c'è momentum sufficiente
            price_change_4h = self.get_price_change(symbol, '4h')
            if abs(price_change_4h) < 2:  # Movimento troppo piccolo
                return False
            
            # Controlla liquidità
            current_volume_usd = self.get_volume_usd(symbol)
            if current_volume_usd < 1000000:  # Min 1M USD volume
                return False
            
            return True
            
        except Exception:
            return False
    
    def activate_trading_bot(self, symbol: str, score: float) -> bool:
        """Attiva bot di trading per symbol specifico"""
        try:
            print(f"[BOT_ACTIVATION] Attivando bot per {symbol} (Score: {score:.1f})")
            
            # Configurazione bot specifica per questo symbol
            bot_config = self.create_bot_config(symbol, score)
            
            # Qui integreresti con il tuo sistema di trading bot esistente
            # trading_wrapper.start_bot(symbol, bot_config)
            
            self.active_bots[symbol] = {
                'start_time': datetime.now(),
                'score': score,
                'config': bot_config,
                'status': 'ACTIVE'
            }
            
            print(f"[BOT_ACTIVATION] Bot {symbol} attivato con successo")
            return True
            
        except Exception as e:
            print(f"[BOT_ACTIVATION] Errore attivazione {symbol}: {e}")
            return False
    
    def create_bot_config(self, symbol: str, score: float) -> Dict:
        """Crea configurazione bot personalizzata basata su score"""
        base_config = self.config.get('base_bot_config', {})
        
        # Personalizza parametri basati su score e caratteristiche symbol
        if score >= 90:
            # High confidence - parametri più aggressivi
            config = base_config.copy()
            config.update({
                'ema_period': 8,
                'distance_threshold': 1.5,
                'trailing_percent': 3.0,
                'position_size_multiplier': 1.2
            })
        elif score >= 80:
            # Medium-high confidence
            config = base_config.copy()
            config.update({
                'ema_period': 10,
                'distance_threshold': 1.0,
                'trailing_percent': 4.0,
                'position_size_multiplier': 1.0
            })
        else:
            # Standard configuration
            config = base_config.copy()
        
        config['symbol'] = symbol
        config['activation_score'] = score
        config['activation_time'] = datetime.now().isoformat()
        
        return config
    
    def run_continuous_scan(self):
        """Loop principale di scansione continua"""
        print(f"[SCANNER] Avvio scansione continua ogni {self.scan_interval} secondi")
        
        while True:
            try:
                # Scansiona monete
                top_coins = self.scan_and_select_coins()
                
                # Attiva bot per le migliori
                for symbol, score in top_coins[:self.max_concurrent_bots]:
                    if self.should_activate_bot(symbol, score):
                        self.activate_trading_bot(symbol, score)
                
                # Gestisci bot attivi (stop se non performanti)
                self.manage_active_bots()
                
                # Pausa prima del prossimo scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                print(f"[SCANNER] Errore nel loop principale: {e}")
                time.sleep(60)  # Pausa più lunga in caso di errore
    
    def manage_active_bots(self):
        """Gestisce bot attivi - stop se non performanti"""
        for symbol in list(self.active_bots.keys()):
            bot_info = self.active_bots[symbol]
            
            # Controlla se il bot deve essere stoppato
            if self.should_stop_bot(symbol, bot_info):
                self.stop_trading_bot(symbol)
    
    def should_stop_bot(self, symbol: str, bot_info: Dict) -> bool:
        """Determina se stoppare un bot attivo"""
        # Runtime troppo lungo senza posizioni
        runtime = datetime.now() - bot_info['start_time']
        if runtime.total_seconds() > 3600:  # 1 ora senza trades
            return True
        
        # Score deteriorato
        current_score = self.calculate_coin_score(symbol)
        if current_score < self.min_score_threshold * 0.8:
            return True
        
        return False
    
    def stop_trading_bot(self, symbol: str):
        """Ferma bot di trading per symbol"""
        print(f"[BOT_STOP] Fermando bot per {symbol}")
        
        # Qui integreresti con il sistema di stop
        # trading_wrapper.stop_bot(symbol)
        
        del self.active_bots[symbol]
    
    # === METODI DI INTEGRAZIONE API (da implementare) ===
    
    def get_current_volume(self, symbol: str) -> float:
        """Ottieni volume corrente"""
        # Implementa con API Binance/Bybit
        return 1000000  # Placeholder
    
    def get_average_volume(self, symbol: str, days: int) -> float:
        """Ottieni volume medio"""
        return 800000  # Placeholder
    
    def get_price_change(self, symbol: str, timeframe: str) -> float:
        """Ottieni cambio prezzo in %"""
        return 2.5  # Placeholder
    
    def get_social_mentions(self, symbol: str) -> int:
        """Ottieni numero menzioni social"""
        return 500  # Placeholder
    
    def get_social_sentiment_score(self, symbol: str) -> float:
        """Ottieni sentiment score 0-1"""
        return 0.6  # Placeholder
    
    def get_kline_data(self, symbol: str, interval: str, limit: int) -> List:
        """Ottieni dati candele"""
        return []  # Placeholder
    
    def get_recent_news(self, symbol: str) -> List[Dict]:
        """Ottieni notizie recenti"""
        return []  # Placeholder
    
    def get_volume_usd(self, symbol: str) -> float:
        """Ottieni volume in USD"""
        return 2000000  # Placeholder
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calcola EMA"""
        if len(prices) < period:
            return []
        
        ema = [np.mean(prices[:period])]
        multiplier = 2 / (period + 1)
        
        for price in prices[period:]:
            ema.append(price * multiplier + ema[-1] * (1 - multiplier))
        
        return ema


# === CONFIGURAZIONE ESEMPIO ===
CONFIG_EXAMPLE = {
    'coin_pool': [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
        'MATICUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'UNIUSDT',
        'ATOMUSDT', 'NEARUSDT', 'ALGOUSDT', 'XRPUSDT', 'CROUSDT'
    ],
    'min_score_threshold': 75,
    'max_concurrent_bots': 3,
    'scan_interval': 300,  # 5 minuti
    
    'base_bot_config': {
        'ema_period': 10,
        'open_candles': 2,
        'stop_candles': 2,
        'distance_threshold': 1.0,
        'spike_threshold': 4.0,
        'trailing_percent': 4.0,
        'stop_loss_percent': 3.0,
        'operation_type': 'BOTH'
    }
}

# === USO ===
if __name__ == "__main__":
    selector = AutomatedCoinSelector(CONFIG_EXAMPLE)
    
    # Test singola scansione
    top_coins = selector.scan_and_select_coins()
    print(f"Top coins found: {top_coins}")
    
    # Avvia scansione continua
    # selector.run_continuous_scan()