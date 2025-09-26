"""
Sistema di Analisi Automatica del Mercato Crypto
Modulo per analizzare automaticamente le crypto e inviare segnali di mercato
"""

import json
import threading
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

# Aggiungi il path per trading_functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trading_functions import vedi_prezzo_moneta, get_kline_data, media_esponenziale

def convert_timeframe_to_bybit(timeframe):
    """Converte timeframe in minuti al formato richiesto da Bybit"""
    if timeframe == 1440:
        return 'D'  # Daily
    elif timeframe == 10080:  # 7 giorni
        return 'W'  # Weekly
    elif timeframe == 43200:  # 30 giorni (approssimativo)
        return 'M'  # Monthly
    else:
        return str(timeframe)  # Per timeframe in minuti standard

class MarketAnalyzer:
    """Classe principale per l'analisi automatica del mercato"""
    
    def __init__(self):
        self.analysis_running = False
        self.analysis_thread = None
        self.last_analysis = {}
        self.analysis_history = []
        self.config = {
            'analysis_interval': 1800,  # 30 minuti
            'signal_interval': 3600,    # 1 ora per segnali periodici
            'timeframes': [15, 60, 240, 1440],  # 15m, 1h, 4h, 1d
            'ema_periods': [20, 50, 200],
            'rsi_period': 14,
            'strength_threshold': 5.0,  # % per considerare una crypto forte/debole vs BTC
            'trend_min_duration': 4,    # candele minime per confermare trend
            'selected_symbols': [],     # Simboli selezionati per l'analisi (vuoto = tutti)
        }
        self.telegram_notifier = None
    
    def set_telegram_notifier(self, notifier):
        """Imposta il notificatore Telegram"""
        self.telegram_notifier = notifier
    
    def get_symbols_to_analyze(self) -> List[str]:
        """Ottieni la lista di simboli da analizzare"""
        # Se ci sono simboli selezionati specificamente, usa quelli
        if self.config.get('selected_symbols'):
            selected = self.config['selected_symbols']
            # Assicurati che BTC sia sempre presente per i calcoli di forza relativa
            if 'BTCUSDT' not in selected:
                selected = ['BTCUSDT'] + selected
            return selected
        
        # Altrimenti usa tutti i simboli disponibili (comportamento originale)
        return self.get_all_available_symbols()
    
    def get_all_available_symbols(self) -> List[str]:
        """Ottieni tutti i simboli disponibili (default + custom)"""
        # Simboli di default
        default_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT',
            'LTCUSDT', 'BCHUSDT', 'FILUSDT', 'ETCUSDT', 'XLMUSDT',
            'VETUSDT', 'ICPUSDT', 'THETAUSDT', 'TRXUSDT', 'ATOMUSDT'
        ]
        
        # Aggiungi simboli custom se esistono
        try:
            custom_file = os.path.join(os.path.dirname(__file__), '..', 'custom_symbols.json')
            if os.path.exists(custom_file):
                with open(custom_file, 'r') as f:
                    custom_data = json.load(f)
                    custom_symbols = [item['symbol'] for item in custom_data if 'symbol' in item]
                    default_symbols.extend(custom_symbols)
        except Exception as e:
            print(f"⚠️ Errore caricamento simboli custom: {e}")
        
        # Rimuovi duplicati e assicurati che BTC sia sempre presente
        symbols = list(set(default_symbols))
        if 'BTCUSDT' not in symbols:
            symbols.insert(0, 'BTCUSDT')
        
        return sorted(symbols)
    
    def set_selected_symbols(self, symbols: List[str]):
        """Imposta i simboli selezionati per l'analisi"""
        if not symbols:
            # Se lista vuota, analizza tutti i simboli
            self.config['selected_symbols'] = []
        else:
            # Valida che i simboli esistano
            available_symbols = self.get_all_available_symbols()
            valid_symbols = [s for s in symbols if s in available_symbols]
            
            # Assicurati che BTC sia sempre presente
            if valid_symbols and 'BTCUSDT' not in valid_symbols:
                valid_symbols.insert(0, 'BTCUSDT')
            
            self.config['selected_symbols'] = valid_symbols
        
        print(f"🎯 Simboli selezionati aggiornati: {self.config['selected_symbols'] or 'TUTTI'}")
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcola l'RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Valore neutro se non abbastanza dati
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def detect_trend(self, prices: List[float], ema_values: List[float]) -> Dict:
        """Rileva il trend attuale e la sua durata"""
        if len(prices) < self.config['trend_min_duration'] or len(ema_values) < self.config['trend_min_duration']:
            return {'trend': 'NEUTRAL', 'duration': 0, 'strength': 0}
        
        recent_prices = prices[-self.config['trend_min_duration']:]
        recent_ema = ema_values[-self.config['trend_min_duration']:]
        
        # Conta candele sopra/sotto EMA
        above_ema = sum(1 for i in range(len(recent_prices)) if recent_prices[i] > recent_ema[i])
        below_ema = len(recent_prices) - above_ema
        
        # Determina trend
        if above_ema >= self.config['trend_min_duration'] * 0.75:
            trend = 'BULLISH'
        elif below_ema >= self.config['trend_min_duration'] * 0.75:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'
        
        # Calcola forza del trend (variazione % prezzo)
        price_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
        strength = abs(price_change)
        
        # Calcola durata approssimativa (quante candele consecutive nel trend)
        duration = 0
        current_price = prices[-1]
        current_ema = ema_values[-1]
        
        for i in range(len(prices) - 1, -1, -1):
            if trend == 'BULLISH' and prices[i] > ema_values[i]:
                duration += 1
            elif trend == 'BEARISH' and prices[i] < ema_values[i]:
                duration += 1
            else:
                break
        
        return {
            'trend': trend,
            'duration': duration,
            'strength': round(strength, 2),
            'price_change': round(price_change, 2)
        }
    
    def calculate_strength_vs_btc(self, symbol_price_change: float, btc_price_change: float) -> Dict:
        """Calcola la forza relativa di una crypto rispetto a BTC"""
        relative_strength = symbol_price_change - btc_price_change
        
        if relative_strength > self.config['strength_threshold']:
            strength_level = 'VERY_STRONG'
        elif relative_strength > 2.0:
            strength_level = 'STRONG'
        elif relative_strength > -2.0:
            strength_level = 'NEUTRAL'
        elif relative_strength > -self.config['strength_threshold']:
            strength_level = 'WEAK'
        else:
            strength_level = 'VERY_WEAK'
        
        return {
            'relative_strength': round(relative_strength, 2),
            'strength_level': strength_level,
            'symbol_change': round(symbol_price_change, 2),
            'btc_change': round(btc_price_change, 2)
        }
    
    def detect_reversal_signals(self, prices: List[float], ema_values: List[float], rsi: float) -> List[str]:
        """Rileva possibili segnali di inversione"""
        signals = []
        
        if len(prices) < 3 or len(ema_values) < 3:
            return signals
        
        current_price = prices[-1]
        prev_price = prices[-2]
        current_ema = ema_values[-1]
        prev_ema = ema_values[-2]
        
        # Crossover EMA
        if prev_price <= prev_ema and current_price > current_ema:
            signals.append('BULLISH_EMA_CROSSOVER')
        elif prev_price >= prev_ema and current_price < current_ema:
            signals.append('BEARISH_EMA_CROSSOVER')
        
        # Segnali RSI
        if rsi <= 30:
            signals.append('RSI_OVERSOLD')
        elif rsi >= 70:
            signals.append('RSI_OVERBOUGHT')
        
        # Divergenza prezzo (prezzo più alto ma EMA in discesa o viceversa)
        if current_price > prev_price and current_ema < prev_ema:
            signals.append('BEARISH_DIVERGENCE')
        elif current_price < prev_price and current_ema > prev_ema:
            signals.append('BULLISH_DIVERGENCE')
        
        return signals
    
    def analyze_symbol(self, symbol: str, timeframe: int) -> Dict:
        """Analizza un singolo simbolo su un timeframe specifico"""
        try:
            # Converti timeframe al formato corretto per Bybit
            bybit_timeframe = convert_timeframe_to_bybit(timeframe)
            
            # Ottieni dati kline
            kline_data = get_kline_data('linear', symbol, bybit_timeframe, limit=100)
            if not kline_data:
                return None
            
            # Estrai prezzi di chiusura (inverti ordine per cronologico)
            kline_data.reverse()
            prices = [float(candle[4]) for candle in kline_data]
            
            # Calcola indicatori tecnici
            ema_20 = media_esponenziale(prices, 20)
            ema_50 = media_esponenziale(prices, 50)
            rsi = self.calculate_rsi(prices)
            
            # Analizza trend
            trend_info = self.detect_trend(prices, ema_20)
            
            # Rileva segnali di inversione
            reversal_signals = self.detect_reversal_signals(prices, ema_20, rsi)
            
            # Calcola variazione prezzo recente (ultime 24 candele o disponibili)
            recent_prices = prices[-min(24, len(prices)):]
            price_change_24 = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
            
            current_price = prices[-1]
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': round(current_price, 6),
                'price_change_24h': round(price_change_24, 2),
                'rsi': round(rsi, 2),
                'ema_20': round(ema_20[-1], 6),
                'ema_50': round(ema_50[-1], 6),
                'trend': trend_info,
                'reversal_signals': reversal_signals,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Errore analisi {symbol} su {timeframe}m: {e}")
            return None
    
    def analyze_market(self) -> Dict:
        """Esegue analisi completa del mercato"""
        print("🔍 Avvio analisi automatica del mercato...")
        
        symbols = self.get_symbols_to_analyze()
        market_analysis = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': len(symbols),
            'timeframes': self.config['timeframes'],
            'analyses': {},
            'market_summary': {
                'strongest_performers': [],
                'weakest_performers': [],
                'reversal_candidates': [],
                'trending_symbols': []
            }
        }
        
        # Analizza BTC per calcoli di forza relativa
        btc_analysis = {}
        for tf in self.config['timeframes']:
            btc_data = self.analyze_symbol('BTCUSDT', tf)
            if btc_data:
                btc_analysis[tf] = btc_data
        
        # Analizza tutti i simboli
        for symbol in symbols:
            symbol_analysis = {}
            
            for timeframe in self.config['timeframes']:
                analysis = self.analyze_symbol(symbol, timeframe)
                if analysis:
                    # Calcola forza vs BTC se disponibile
                    if timeframe in btc_analysis and symbol != 'BTCUSDT':
                        btc_change = btc_analysis[timeframe]['price_change_24h']
                        symbol_change = analysis['price_change_24h']
                        strength_vs_btc = self.calculate_strength_vs_btc(symbol_change, btc_change)
                        analysis['strength_vs_btc'] = strength_vs_btc
                    
                    symbol_analysis[timeframe] = analysis
            
            if symbol_analysis:
                market_analysis['analyses'][symbol] = symbol_analysis
        
        # Genera sommario del mercato
        self.generate_market_summary(market_analysis)
        
        # Salva analisi
        self.last_analysis = market_analysis
        self.analysis_history.append(market_analysis)
        
        # Mantieni solo le ultime 24 analisi
        if len(self.analysis_history) > 24:
            self.analysis_history = self.analysis_history[-24:]
        
        print(f"✅ Analisi completata: {len(market_analysis['analyses'])} simboli analizzati")
        return market_analysis
    
    def generate_market_summary(self, analysis: Dict):
        """Genera sommario del mercato dall'analisi"""
        summary = analysis['market_summary']
        
        # Liste per raccogliere dati
        performers_1h = []
        reversal_candidates = []
        trending_symbols = []
        
        for symbol, timeframes in analysis['analyses'].items():
            # Analizza performance su 1h (timeframe 60)
            if 60 in timeframes:
                tf_data = timeframes[60]
                performers_1h.append({
                    'symbol': symbol,
                    'change': tf_data['price_change_24h'],
                    'rsi': tf_data['rsi'],
                    'trend': tf_data['trend']['trend']
                })
                
                # Candidati inversione (RSI estremi o segnali di inversione)
                if tf_data['reversal_signals'] or tf_data['rsi'] <= 30 or tf_data['rsi'] >= 70:
                    reversal_candidates.append({
                        'symbol': symbol,
                        'rsi': tf_data['rsi'],
                        'signals': tf_data['reversal_signals'],
                        'trend': tf_data['trend']['trend']
                    })
                
                # Simboli in trend forte
                if tf_data['trend']['strength'] > 3.0 and tf_data['trend']['duration'] > 5:
                    trending_symbols.append({
                        'symbol': symbol,
                        'trend': tf_data['trend']['trend'],
                        'strength': tf_data['trend']['strength'],
                        'duration': tf_data['trend']['duration']
                    })
        
        # Ordina per performance
        performers_1h.sort(key=lambda x: x['change'], reverse=True)
        
        # Top 5 migliori e peggiori
        summary['strongest_performers'] = performers_1h[:5]
        summary['weakest_performers'] = performers_1h[-5:]
        
        # Ordina candidati inversione per RSI estremi
        reversal_candidates.sort(key=lambda x: abs(50 - x['rsi']), reverse=True)
        summary['reversal_candidates'] = reversal_candidates[:5]
        
        # Ordina trending per forza
        trending_symbols.sort(key=lambda x: x['strength'], reverse=True)
        summary['trending_symbols'] = trending_symbols[:5]
    
    def send_market_signals(self, analysis: Dict):
        """Invia segnali di mercato via Telegram"""
        if not self.telegram_notifier:
            print("⚠️ Telegram notifier non configurato")
            return
        
        try:
            summary = analysis['market_summary']
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Messaggio principale di analisi
            message = f"""
🤖 <b>ANALISI AUTOMATICA MERCATO</b>

📊 <b>Sommario Mercato</b>
🔍 Simboli analizzati: <b>{analysis['symbols_analyzed']}</b>
⏰ {timestamp}

💪 <b>TOP PERFORMERS (1h)</b>
"""
            
            # Aggiungi top performers
            for i, perf in enumerate(summary['strongest_performers'][:3], 1):
                emoji = "🚀" if perf['change'] > 5 else "📈"
                message += f"{emoji} <b>{perf['symbol']}</b>: <code>{perf['change']:+.2f}%</code>\n"
            
            message += "\n📉 <b>WEAK PERFORMERS (1h)</b>\n"
            
            # Aggiungi worst performers
            for i, perf in enumerate(summary['weakest_performers'][:3], 1):
                emoji = "🔻" if perf['change'] < -5 else "📉"
                message += f"{emoji} <b>{perf['symbol']}</b>: <code>{perf['change']:+.2f}%</code>\n"
            
            # Segnali di inversione
            if summary['reversal_candidates']:
                message += "\n🔄 <b>POSSIBILI INVERSIONI</b>\n"
                for candidate in summary['reversal_candidates'][:2]:
                    rsi_emoji = "🟢" if candidate['rsi'] <= 30 else "🔴" if candidate['rsi'] >= 70 else "🟡"
                    signals_text = ", ".join(candidate['signals'][:2]) if candidate['signals'] else "RSI Estremo"
                    message += f"{rsi_emoji} <b>{candidate['symbol']}</b> - RSI: <code>{candidate['rsi']:.1f}</code>\n"
                    message += f"    └ {signals_text}\n"
            
            # Trend forti
            if summary['trending_symbols']:
                message += "\n📈 <b>TREND FORTI</b>\n"
                for trend in summary['trending_symbols'][:2]:
                    trend_emoji = "🚀" if trend['trend'] == 'BULLISH' else "🔻"
                    message += f"{trend_emoji} <b>{trend['symbol']}</b> - {trend['trend']}\n"
                    message += f"    └ Forza: <code>{trend['strength']:.1f}%</code>, Durata: <code>{trend['duration']} candele</code>\n"
            
            message += f"\n📊 <b>Dashboard:</b> http://localhost:5000/market-analysis"
            
            # Invia messaggio principale
            self.telegram_notifier.send_message_sync(message)
            
            # Invia alert specifici per segnali importanti
            self.send_specific_alerts(analysis)
            
        except Exception as e:
            print(f"❌ Errore invio segnali mercato: {e}")
    
    def send_specific_alerts(self, analysis: Dict):
        """Invia alert specifici per segnali importanti"""
        try:
            summary = analysis['market_summary']
            
            # Alert per performance estreme (>10% o <-10%)
            for perf in summary['strongest_performers']:
                if perf['change'] > 10:
                    alert_msg = f"""
🚨 <b>PERFORMANCE ESTREMA!</b> 🚀

💰 <b>{perf['symbol']}</b> ha guadagnato <b>{perf['change']:+.2f}%</b> nell'ultima ora!

📊 RSI: <code>{perf['rsi']:.1f}</code>
📈 Trend: <b>{perf['trend']}</b>

⚠️ Monitora per possibili prese di profitto!
"""
                    self.telegram_notifier.send_message_sync(alert_msg)
            
            for perf in summary['weakest_performers']:
                if perf['change'] < -10:
                    alert_msg = f"""
🚨 <b>CALO SIGNIFICATIVO!</b> 📉

💰 <b>{perf['symbol']}</b> ha perso <b>{perf['change']:+.2f}%</b> nell'ultima ora!

📊 RSI: <code>{perf['rsi']:.1f}</code>
📈 Trend: <b>{perf['trend']}</b>

💡 Possibile opportunità di acquisto se RSI < 30!
"""
                    self.telegram_notifier.send_message_sync(alert_msg)
            
            # Alert per crossover EMA importanti
            for symbol, timeframes in analysis['analyses'].items():
                if 60 in timeframes:  # Timeframe 1h
                    tf_data = timeframes[60]
                    if 'BULLISH_EMA_CROSSOVER' in tf_data['reversal_signals']:
                        alert_msg = f"""
🔄 <b>CROSSOVER BULLISH!</b> 📈

💰 <b>{symbol}</b> ha attraversato al rialzo l'EMA(20)!

💲 Prezzo: <code>${tf_data['current_price']:.6f}</code>
📊 RSI: <code>{tf_data['rsi']:.1f}</code>
🎯 EMA(20): <code>${tf_data['ema_20']:.6f}</code>

🚀 Possibile inizio trend rialzista!
"""
                        self.telegram_notifier.send_message_sync(alert_msg)
                    
                    elif 'BEARISH_EMA_CROSSOVER' in tf_data['reversal_signals']:
                        alert_msg = f"""
🔄 <b>CROSSOVER BEARISH!</b> 📉

💰 <b>{symbol}</b> ha attraversato al ribasso l'EMA(20)!

💲 Prezzo: <code>${tf_data['current_price']:.6f}</code>
📊 RSI: <code>{tf_data['rsi']:.1f}</code>
🎯 EMA(20): <code>${tf_data['ema_20']:.6f}</code>

⚠️ Possibile inizio trend ribassista!
"""
                        self.telegram_notifier.send_message_sync(alert_msg)
            
        except Exception as e:
            print(f"❌ Errore invio alert specifici: {e}")
    
    def start_analysis_monitor(self):
        """Avvia il monitor di analisi automatica"""
        if self.analysis_running:
            return
        
        self.analysis_running = True
        self.analysis_thread = threading.Thread(target=self.analysis_loop, daemon=True)
        self.analysis_thread.start()
        print("🤖 Monitor analisi automatica avviato")
    
    def stop_analysis_monitor(self):
        """Ferma il monitor di analisi"""
        self.analysis_running = False
        print("🛑 Monitor analisi automatica fermato")
    
    def analysis_loop(self):
        """Loop principale di analisi"""
        last_analysis_time = 0
        last_signal_time = 0
        
        while self.analysis_running:
            try:
                current_time = time.time()
                
                # Esegui analisi ogni analysis_interval secondi
                if current_time - last_analysis_time >= self.config['analysis_interval']:
                    analysis = self.analyze_market()
                    last_analysis_time = current_time
                    
                    # Invia segnali ogni signal_interval secondi
                    if current_time - last_signal_time >= self.config['signal_interval']:
                        self.send_market_signals(analysis)
                        last_signal_time = current_time
                
                # Pausa tra controlli
                time.sleep(60)  # Controlla ogni minuto
                
            except Exception as e:
                print(f"❌ Errore nel loop di analisi: {e}")
                time.sleep(300)  # Pausa più lunga in caso di errore
    
    def get_analysis_status(self) -> Dict:
        """Ottieni stato del sistema di analisi"""
        return {
            'running': self.analysis_running,
            'last_analysis': self.last_analysis.get('timestamp', 'Mai eseguita'),
            'total_analyses': len(self.analysis_history),
            'config': self.config,
            'symbols_count': len(self.get_symbols_to_analyze())
        }
    
    def update_config(self, new_config: Dict):
        """Aggiorna configurazione del sistema"""
        self.config.update(new_config)
        print(f"⚙️ Configurazione aggiornata: {new_config}")


# Istanza globale del sistema di analisi
market_analyzer = MarketAnalyzer()

def init_market_analysis(app, telegram_notifier=None):
    """Inizializza il sistema di analisi mercato"""
    global market_analyzer
    
    if telegram_notifier:
        market_analyzer.set_telegram_notifier(telegram_notifier)
    
    print("🤖 Sistema Analisi Mercato inizializzato")
    return market_analyzer
