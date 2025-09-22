import openai
import json
from datetime import datetime
from typing import Dict, List

class AITradingAssistant:
    """AI Trading Assistant usando OpenAI GPT-4"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4"
        
    def analyze_trading_opportunity(self, symbol_data: Dict) -> Dict:
        """
        Analizza dati di mercato e genera segnali trading AI
        
        Args:
            symbol_data: Dati dall'analisi automatica
            
        Returns:
            Segnale trading con entry, TP, SL, reasoning
        """
        
        prompt = self._build_trading_prompt(symbol_data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Sei un esperto trader quantitativo specializzato in analisi tecnica multi-timeframe. Fornisci sempre risposte in formato JSON valido."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Bassa per consistenza
                max_tokens=1000
            )
            
            ai_analysis = response.choices[0].message.content
            trading_signal = self._parse_ai_response(ai_analysis)
            
            return {
                'success': True,
                'signal': trading_signal,
                'raw_analysis': ai_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _build_trading_prompt(self, data: Dict) -> str:
        """Costruisce prompt ottimizzato per analisi trading"""
        
        symbol = data.get('symbol', 'Unknown')
        timeframes = data.get('timeframes', {})
        
        prompt = f"""
ANALISI TRADING MULTI-TIMEFRAME per {symbol}

DATI TECNICI CORRENTI:
Prezzo Attuale: ${data.get('current_price', 0):.6f}

TIMEFRAME 15 MINUTI:
- RSI: {timeframes.get('15', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('15', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('15', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('15', {}).get('ema_50', 'N/A')}
- Durata Trend: {timeframes.get('15', {}).get('trend', {}).get('duration', 'N/A')} candele

TIMEFRAME 1 ORA:
- RSI: {timeframes.get('60', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('60', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('60', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('60', {}).get('ema_50', 'N/A')}
- Durata Trend: {timeframes.get('60', {}).get('trend', {}).get('duration', 'N/A')} candele

TIMEFRAME 4 ORE:
- RSI: {timeframes.get('240', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('240', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('240', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('240', {}).get('ema_50', 'N/A')}
- Durata Trend: {timeframes.get('240', {}).get('trend', {}).get('duration', 'N/A')} candele

TIMEFRAME 1 GIORNO:
- RSI: {timeframes.get('1440', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('1440', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('1440', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('1440', {}).get('ema_50', 'N/A')}
- Durata Trend: {timeframes.get('1440', {}).get('trend', {}).get('duration', 'N/A')} candele

SEGNALI RILEVATI:
{', '.join(data.get('reversal_signals', []))}

FORZA vs BTC:
- 15m: {timeframes.get('15', {}).get('strength_vs_btc', 'N/A')}
- 1h: {timeframes.get('60', {}).get('strength_vs_btc', 'N/A')}
- 4h: {timeframes.get('240', {}).get('strength_vs_btc', 'N/A')}
- 1d: {timeframes.get('1440', {}).get('strength_vs_btc', 'N/A')}

REGOLE DI TRADING:
1. Analizza confluenza tra timeframes
2. Considera momentum e segnali di inversione
3. Valuta forza relativa vs BTC
4. Risk/Reward minimo 1:2
5. Position size max 5% per trade ad alto rischio

FORNISCI RISPOSTA IN QUESTO FORMATO JSON:
{{
    "action": "BUY/SELL/HOLD",
    "confidence": 85,
    "entry_price": 3.6037,
    "stop_loss": 3.6450,
    "take_profit_1": 3.5500,
    "take_profit_2": 3.5000,
    "risk_reward_ratio": 2.5,
    "position_size_percent": 3,
    "timeframe_focus": "1h",
    "reasoning": "Setup bearish confermato da confluenza 15m/1h/4h. BEARISH_EMA_CROSSOVER attivo, prezzo sotto tutte le EMA principali, RSI in zona neutrale con spazio per scendere. Forza debole vs BTC conferma momentum ribassista.",
    "confluence_score": 8,
    "risk_level": "MEDIUM",
    "expected_duration": "2-6 ore",
    "invalidation_level": 3.6500,
    "key_levels": [3.5500, 3.5000, 3.4500]
}}
"""
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse della risposta AI e validazione"""
        try:
            # Cerca JSON nella risposta
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                # Validazione campi richiesti
                required_fields = ['action', 'confidence', 'entry_price', 'stop_loss', 'reasoning']
                for field in required_fields:
                    if field not in parsed:
                        raise ValueError(f"Campo mancante: {field}")
                
                return parsed
            else:
                raise ValueError("Formato JSON non trovato nella risposta")
                
        except Exception as e:
            return {
                'action': 'HOLD',
                'confidence': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'reasoning': f'Errore parsing AI: {str(e)}',
                'error': True
            }

# Esempio di utilizzo
if __name__ == "__main__":
    # Test con dati mock
    test_data = {
        'symbol': 'ADAUSDT',
        'current_price': 3.6037,
        'timeframes': {
            '15': {'rsi': 41.4, 'trend': {'trend': 'BEARISH', 'duration': 6}, 'ema_20': 3.6192},
            '60': {'rsi': 46.1, 'trend': {'trend': 'BEARISH', 'duration': 11}, 'ema_20': 3.6335},
            '240': {'rsi': 42.8, 'trend': {'trend': 'BEARISH', 'duration': 17}, 'ema_20': 3.6635},
            '1440': {'rsi': 53.9, 'trend': {'trend': 'BULLISH', 'duration': 0}, 'ema_20': 3.6060}
        },
        'reversal_signals': ['BEARISH_EMA_CROSSOVER'],
    }
    
    # ai_assistant = AITradingAssistant(api_key="your-openai-key")
    # result = ai_assistant.analyze_trading_opportunity(test_data)
    # print(json.dumps(result, indent=2))
