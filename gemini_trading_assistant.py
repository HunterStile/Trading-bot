import google.generativeai as genai
import json
from datetime import datetime
from typing import Dict

class GeminiTradingAssistant:
    """AI Trading Assistant usando Google Gemini (Gratuito)"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
        # Lista dei modelli da provare in ordine di preferenza
        models_to_try = [
            'gemini-1.5-flash',
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro',
            'gemini-pro',
            'gemini-1.0-pro'
        ]
        
        self.model = None
        
        # Prima lista i modelli disponibili
        try:
            available_models = genai.list_models()
            available_names = []
            print("📋 Modelli Gemini disponibili:")
            for model in available_models:
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    available_names.append(model_name)
                    print(f"  - {model_name}")
        except Exception as e:
            print(f"⚠️ Impossibile listare modelli: {e}")
            available_names = models_to_try  # Fallback alla lista predefinita
        
        # Prova ogni modello finché uno non funziona
        for model_name in models_to_try:
            try:
                if model_name in available_names or not available_names:
                    self.model = genai.GenerativeModel(model_name)
                    print(f"🤖 {model_name} inizializzato con successo")
                    break
            except Exception as e:
                print(f"⚠️ {model_name} non disponibile: {e}")
                continue
        
        if not self.model:
            raise Exception("❌ Nessun modello Gemini compatibile trovato")
    
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
            # Se il test fallisce, prova a reinizializzare
            if "404" in str(e) or "not found" in str(e).lower():
                print("🔄 Tentativo di reinizializzazione modello...")
                return self._reinitialize_model()
            return False
    
    def _reinitialize_model(self) -> bool:
        """Reinizializza il modello con la lista aggiornata"""
        try:
            # Ottieni modelli attualmente disponibili
            available_models = genai.list_models()
            available_names = []
            for model in available_models:
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    available_names.append(model_name)
            
            # Prova il primo modello disponibile
            models_to_try = [
                'gemini-1.5-flash',
                'gemini-1.5-flash-latest', 
                'gemini-1.5-pro',
                'gemini-pro',
                'gemini-1.0-pro'
            ]
            
            for model_name in models_to_try:
                if model_name in available_names:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        print(f"🔄 Modello reinizializzato: {model_name}")
                        return True
                    except:
                        continue
            
            return False
        except Exception as e:
            print(f"❌ Errore reinizializzazione: {e}")
            return False
        
    def analyze_trading_opportunity(self, symbol_data: Dict) -> Dict:
        """Analizza con Gemini con gestione errori migliorata"""
        
        prompt = self._build_trading_prompt(symbol_data)
        symbol = symbol_data.get('symbol', 'Unknown')
        
        print(f"🤖 Inviando richiesta Gemini per {symbol}...")
        
        try:
            # Retry logic per errori temporanei
            max_retries = 2
            response = None
            
            for attempt in range(max_retries + 1):
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.3,
                            max_output_tokens=1000,
                        )
                    )
                    break  # Se arriva qui, la richiesta è riuscita
                    
                except Exception as e:
                    if attempt < max_retries and ("404" in str(e) or "not found" in str(e).lower()):
                        print(f"🔄 Tentativo {attempt + 1}/{max_retries + 1} - Errore modello, reinizializzando...")
                        if self._reinitialize_model():
                            continue  # Riprova con il nuovo modello
                    
                    # Se tutti i tentativi falliscono o è un errore diverso, rilancia
                    if attempt == max_retries:
                        raise e
            
            print(f"✅ Risposta ricevuta da Gemini per {symbol}")
            
            if not response or not response.text:
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
            if "quota" in error_msg.lower() or "resource exhausted" in error_msg.lower():
                error_msg = "Quota Gemini esaurita - riprova più tardi"
            elif "timeout" in error_msg.lower():
                error_msg = "Timeout connessione Gemini - riprova"
            elif "api" in error_msg.lower() and "key" in error_msg.lower():
                error_msg = "API key Gemini non valida"
            elif "404" in error_msg or "not found" in error_msg.lower():
                error_msg = "Modello Gemini non disponibile - prova a riavviare il bot"
            elif "publisher model" in error_msg.lower():
                error_msg = "Errore versione modello Gemini - riavvia il bot per aggiornare"
            elif "permission" in error_msg.lower() or "access" in error_msg.lower():
                error_msg = "Permessi insufficienti per accedere a Gemini"
            
            return {
                'success': False,
                'error': error_msg,
                'raw_error': str(e),
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
    
    def chat_about_trading(self, conversation_prompt: str) -> Dict:
        """Metodo specifico per conversazioni di trading"""
        try:
            print("💬 Gemini: Elaborando messaggio chat...")
            
            # Configurazione per conversazione
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,  # Un po' più creativa per conversazioni
                max_output_tokens=1000,
                candidate_count=1,
            )
            
            # Prompt per conversazione naturale
            chat_prompt = f"""Sei un esperto trader professionista che sta discutendo strategie di trading con un cliente.

{conversation_prompt}

ISTRUZIONI PER LA RISPOSTA:
- Rispondi in modo conversazionale e professionale
- Usa i dati tecnici forniti nel contesto
- Sii specifico sui livelli di prezzo e indicatori
- Considera diversi scenari di mercato
- Fornisci consigli pratici e actionable
- Mantieni un tono amichevole ma professionale
- Se l'utente condivide la sua opinione, analizzala rispetto ai dati
- Non dire mai che mancano dati - usa quelli forniti nel contesto

Rispondi in italiano in modo dettagliato e utile:"""
            
            response = self.model.generate_content(
                chat_prompt,
                generation_config=generation_config
            )
            
            if response.text:
                return {
                    'success': True,
                    'response': response.text.strip(),
                    'type': 'chat_response'
                }
            else:
                return {
                    'success': False,
                    'error': 'Risposta vuota da Gemini',
                    'response': 'Mi dispiace, non sono riuscito a elaborare una risposta. Puoi riprovare?'
                }
                
        except Exception as e:
            error_msg = f"Errore chat Gemini: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'response': 'Mi dispiace, ho avuto un problema tecnico. Puoi riprovare la domanda?'
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
