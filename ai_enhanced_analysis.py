"""
Integrazione AI Trading Assistant nel sistema di Market Analysis
"""
import sys
import os
from datetime import datetime
from typing import Dict, List

# Aggiungi path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_trading_assistant import AITradingAssistant
    from gemini_trading_assistant import GeminiTradingAssistant
except ImportError:
    AITradingAssistant = None
    GeminiTradingAssistant = None
    print("⚠️ AI Trading Assistant non disponibile - installa dipendenze AI")

class AIEnhancedMarketAnalysis:
    """Estensione del MarketAnalyzer con capacità AI"""
    
    def __init__(self, market_analyzer, ai_api_key=None, ai_provider='openai'):
        self.market_analyzer = market_analyzer
        self.ai_enabled = False
        self.ai_assistant = None
        
        if ai_api_key and (AITradingAssistant or GeminiTradingAssistant):
            try:
                if ai_provider == 'openai' and AITradingAssistant:
                    self.ai_assistant = AITradingAssistant(ai_api_key)
                elif ai_provider == 'gemini' and GeminiTradingAssistant:
                    self.ai_assistant = GeminiTradingAssistant(ai_api_key)
                else:
                    print(f"❌ Provider {ai_provider} non supportato o libreria non disponibile")
                    return
                
                self.ai_enabled = True
                print(f"🤖 AI Trading Assistant attivato con {ai_provider.upper()}!")
            except Exception as e:
                print(f"❌ Errore inizializzazione AI: {e}")
    
    def analyze_with_ai_signals(self, symbols: List[str] = None) -> Dict:
        """
        Esegue analisi normale + genera segnali AI per simboli interessanti
        """
        # Esegui analisi normale
        normal_analysis = self.market_analyzer.analyze_market()
        
        print(f"📊 Analisi normale completata. Chiavi principali: {list(normal_analysis.keys())}")
        analyses = normal_analysis.get('analyses', {})
        print(f"🔍 Simboli trovati in 'analyses': {len(analyses)}")
        
        if not analyses:
            print("⚠️ Nessun simbolo trovato in 'analyses', controlliamo altre chiavi...")
            for key, value in normal_analysis.items():
                if isinstance(value, dict) and len(value) > 0:
                    print(f"  - {key}: {list(value.keys())[:5]} ({'...' if len(value) > 5 else ''})")
        
        if not self.ai_enabled:
            return normal_analysis
        
        # Aggiungi segnali AI per simboli con setup interessanti
        ai_signals = {}
        
        for symbol, data in analyses.items():
            print(f"🔍 Controllando setup per {symbol}...")
            print(f"  📊 Chiavi dati: {list(data.keys()) if isinstance(data, dict) else 'Non è dict'}")
            
            # Trasforma i dati da format market_analysis a format _is_interesting_setup
            transformed_data = self._transform_market_data_to_ai_format(symbol, data)
            
            if self._is_interesting_setup(transformed_data):
                print(f"🤖 Analizzando {symbol} con AI...")
                
                ai_result = self.ai_assistant.analyze_trading_opportunity(transformed_data)
                
                if ai_result['success']:
                    ai_signals[symbol] = ai_result['signal']
        
        # Aggiungi segnali AI ai risultati
        normal_analysis['ai_signals'] = ai_signals
        normal_analysis['ai_enabled'] = True
        
        return normal_analysis
    
    def _transform_market_data_to_ai_format(self, symbol: str, market_data: Dict) -> Dict:
        """
        Trasforma i dati da format analyze_market() a format per AI
        
        Input: {15: {analysis}, 60: {analysis}, 240: {analysis}, 1440: {analysis}}
        Output: {symbol, current_price, timeframes: {15m: {analysis}}, reversal_signals: [...]}
        """
        transformed = {
            'symbol': symbol,
            'current_price': 0,
            'timeframes': {},
            'reversal_signals': []
        }
        
        # Trasforma ogni timeframe
        for timeframe, tf_data in market_data.items():
            if isinstance(tf_data, dict):
                # Aggiorna current_price dal primo timeframe disponibile
                if transformed['current_price'] == 0 and 'current_price' in tf_data:
                    transformed['current_price'] = tf_data['current_price']
                
                # Aggiungi timeframe con suffisso 'm'
                transformed['timeframes'][f'{timeframe}m'] = tf_data
                
                # Raccogli segnali di inversione
                if 'reversal_signals' in tf_data:
                    transformed['reversal_signals'].extend(tf_data['reversal_signals'])
        
        # Rimuovi duplicati dai segnali
        transformed['reversal_signals'] = list(set(transformed['reversal_signals']))
        
        print(f"  🔄 Trasformazione per {symbol}: timeframes={list(transformed['timeframes'].keys())}, segnali={transformed['reversal_signals']}")
        
        return transformed
    
    def _is_interesting_setup(self, symbol_data: Dict) -> bool:
        """
        Determina se un simbolo ha setup interessante per analisi AI
        """
        timeframes = symbol_data.get('timeframes', {})
        reversal_signals = symbol_data.get('reversal_signals', [])
        
        # Criteri per setup interessante:
        interesting_signals = [
            'BEARISH_EMA_CROSSOVER', 
            'BULLISH_EMA_CROSSOVER',
            'RSI_OVERSOLD', 
            'RSI_OVERBOUGHT',
            'BULLISH_DIVERGENCE',
            'BEARISH_DIVERGENCE'
        ]
        
        # Ha segnali di inversione
        if any(signal in reversal_signals for signal in interesting_signals):
            found_signals = [s for s in interesting_signals if s in reversal_signals]
            print(f"  ✅ Setup interessante per segnali: {found_signals}")
            return True
        
        # Confluenza bearish/bullish su più timeframes
        trends = []
        for tf_data in timeframes.values():
            trend = tf_data.get('trend', {}).get('trend')
            if trend in ['BULLISH', 'BEARISH']:
                trends.append(trend)
        
        # Se 3+ timeframes hanno stesso trend
        if len(trends) >= 3:
            bullish_count = trends.count('BULLISH')
            bearish_count = trends.count('BEARISH')
            if bullish_count >= 3 or bearish_count >= 3:
                print(f"  ✅ Setup interessante per confluenza trend: {bullish_count}B/{bearish_count}B")
                return True
        
        print(f"  ❌ Setup non interessante: segnali={reversal_signals}, trends={trends}")
        return False
        
        return False
    
    def get_top_ai_opportunities(self, limit: int = 5) -> List[Dict]:
        """
        Ottieni top opportunità trading secondo AI
        """
        if not self.ai_enabled:
            print("⚠️ AI non abilitato per top opportunities")
            return []
        
        print(f"🔍 Cercando top {limit} opportunità AI...")
        analysis = self.analyze_with_ai_signals()
        ai_signals = analysis.get('ai_signals', {})
        
        print(f"🤖 Segnali AI trovati: {len(ai_signals)}")
        for symbol, signal in ai_signals.items():
            print(f"  - {symbol}: {signal.get('action')} (confidence: {signal.get('confidence', 0)}%)")
        
        # Ordina per confidence e risk/reward
        opportunities = []
        for symbol, signal in ai_signals.items():
            if signal.get('action') in ['BUY', 'SELL'] and signal.get('confidence', 0) > 70:
                opportunities.append({
                    'symbol': symbol,
                    'action': signal['action'],
                    'confidence': signal['confidence'],
                    'risk_reward': signal.get('risk_reward_ratio', 0),
                    'entry': signal.get('entry_price', 0),
                    'stop_loss': signal.get('stop_loss', 0),
                    'take_profit_1': signal.get('take_profit_1', 0),
                    'reasoning': signal.get('reasoning', ''),
                    'position_size': signal.get('position_size_percent', 2)
                })
        
        print(f"📊 Opportunità con confidence >70%: {len(opportunities)}")
        
        # Ordina per confidence * risk_reward
        opportunities.sort(
            key=lambda x: x['confidence'] * x['risk_reward'], 
            reverse=True
        )
        
        return opportunities[:limit]

# Esempio di utilizzo nel sistema esistente
def extend_market_analysis_with_ai(market_analyzer, openai_api_key=None):
    """
    Factory function per creare analisi potenziata con AI
    """
    return AIEnhancedMarketAnalysis(
        market_analyzer, 
        ai_api_key=openai_api_key,
        ai_provider='openai'
    )

if __name__ == "__main__":
    # Test esempio
    print("🧪 Test AI Enhanced Market Analysis")
    
    # Mock dell'analizzatore esistente
    class MockMarketAnalyzer:
        def analyze_market(self, symbols=None):
            return {
                'analyses': {
                    'ADAUSDT': {
                        'current_price': 3.6037,
                        'timeframes': {
                            '15': {'rsi': 41.4, 'trend': {'trend': 'BEARISH', 'duration': 6}},
                            '60': {'rsi': 46.1, 'trend': {'trend': 'BEARISH', 'duration': 11}},
                        },
                        'reversal_signals': ['BEARISH_EMA_CROSSOVER']
                    }
                }
            }
    
    mock_analyzer = MockMarketAnalyzer()
    
    # Test senza AI
    ai_enhanced = AIEnhancedMarketAnalysis(mock_analyzer, ai_api_key=None)
    result = ai_enhanced.analyze_with_ai_signals(['ADAUSDT'])
    print("✅ Test completato (AI disabilitato)")
    
    # Per test con AI reale, decommentare:
    # ai_enhanced = AIEnhancedMarketAnalysis(mock_analyzer, ai_api_key="your-openai-key")
    # result = ai_enhanced.analyze_with_ai_signals(['ADAUSDT'])
    # print("🤖 AI Analysis:", result.get('ai_signals', {}))
