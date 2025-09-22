import google.generativeai as genai
import json
from datetime import datetime
from typing import Dict

class GeminiTradingAssistant:
    """AI Trading Assistant usando Google Gemini (Gratuito)"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
        # Prova prima gemini-1.5-flash (gratuito e veloce)
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("🤖 Gemini 1.5 Flash inizializzato")
        except Exception as e:
            print(f"⚠️ Gemini 1.5 Flash non disponibile: {e}")
            try:
                # Fallback a gemini-pro se disponibile
                self.model = genai.GenerativeModel('gemini-pro')
                print("🤖 Gemini Pro inizializzato")
            except Exception as e2:
                print(f"❌ Nessun modello Gemini disponibile: {e2}")
                # Lista modelli disponibili per debug
                try:
                    available_models = genai.list_models()
                    print("📋 Modelli disponibili:")
                    for model in available_models:
                        if 'generateContent' in model.supported_generation_methods:
                            print(f"  - {model.name}")
                except:
                    pass
                raise Exception("Nessun modello Gemini compatibile trovato")
    
    def test_connection(self) -> bool:
        """Testa la connessione a Gemini con una richiesta semplice"""
        try:
            print("🧪 Testando connessione Gemini...")
            response = self.model.generate_content(
                "Rispondi solo con: OK",
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=10,
                )
            )
            
            if response.text and "OK" in response.text:
                print("✅ Test connessione Gemini riuscito")
                return True
            else:
                print(f"⚠️ Test Gemini: risposta inaspettata: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Test connessione Gemini fallito: {e}")
            return False
        
    def analyze_trading_opportunity(self, symbol_data: Dict) -> Dict:
        """Analizza con Gemini con gestione errori migliorata"""
        
        prompt = self._build_trading_prompt(symbol_data)
        symbol = symbol_data.get('symbol', 'Unknown')
        
        print(f"🤖 Inviando richiesta Gemini per {symbol}...")
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )
            
            print(f"✅ Risposta ricevuta da Gemini per {symbol}")
            
            if not response.text:
                raise Exception("Risposta vuota da Gemini")
            
            ai_analysis = response.text
            trading_signal = self._parse_ai_response(ai_analysis)
            
            print(f"📊 Segnale AI generato per {symbol}: {trading_signal.get('action', 'N/A')}")
            
            return {
                'success': True,
                'signal': trading_signal,
                'raw_analysis': ai_analysis,
                'timestamp': datetime.now().isoformat(),
                'cost': 'FREE'  # Gemini ha piano gratuito generoso
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Errore Gemini per {symbol}: {error_msg}")
            
            # Gestione errori specifici
            if "quota" in error_msg.lower():
                error_msg = "Quota Gemini esaurita - riprova più tardi"
            elif "timeout" in error_msg.lower():
                error_msg = "Timeout connessione Gemini - riprova"
            elif "api" in error_msg.lower() and "key" in error_msg.lower():
                error_msg = "API key Gemini non valida"
            elif "404" in error_msg or "not found" in error_msg.lower():
                error_msg = "Modello Gemini non disponibile"
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
- RSI: {timeframes.get('15m', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('15m', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('15m', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('15m', {}).get('ema_50', 'N/A')}

TIMEFRAME 1 ORA:
- RSI: {timeframes.get('60m', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('60m', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('60m', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('60m', {}).get('ema_50', 'N/A')}

TIMEFRAME 4 ORE:
- RSI: {timeframes.get('240m', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('240m', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('240m', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('240m', {}).get('ema_50', 'N/A')}

TIMEFRAME 1 GIORNO:
- RSI: {timeframes.get('1440m', {}).get('rsi', 'N/A')}
- Trend: {timeframes.get('1440m', {}).get('trend', {}).get('trend', 'N/A')}
- EMA(20): ${timeframes.get('1440m', {}).get('ema_20', 'N/A')}
- EMA(50): ${timeframes.get('1440m', {}).get('ema_50', 'N/A')}

SEGNALI RILEVATI:
{', '.join(data.get('reversal_signals', []))}

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
    "reasoning": "Setup bearish confermato da confluenza 15m/1h/4h. BEARISH_EMA_CROSSOVER attivo, prezzo sotto tutte le EMA principali, RSI in zona neutrale con spazio per scendere.",
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

# Test con Gemini
if __name__ == "__main__":
    test_data = {
        'symbol': 'ADAUSDT',
        'current_price': 3.6037,
        'timeframes': {
            '15m': {'rsi': 41.4, 'trend': {'trend': 'BEARISH', 'duration': 6}, 'ema_20': 3.6192},
            '60m': {'rsi': 46.1, 'trend': {'trend': 'BEARISH', 'duration': 11}, 'ema_20': 3.6335},
        },
        'reversal_signals': ['BEARISH_EMA_CROSSOVER'],
    }
    
    # assistant = GeminiTradingAssistant("your-gemini-api-key")
    # result = assistant.analyze_trading_opportunity(test_data)
    # print(json.dumps(result, indent=2))
