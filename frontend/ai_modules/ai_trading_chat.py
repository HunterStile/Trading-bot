"""
Sistema di Chat AI per Trading Assistant
Permette conversazioni interattive sui segnali di trading
"""
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

# Aggiungi path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_trading_assistant import AITradingAssistant
    from gemini_trading_assistant import GeminiTradingAssistant
except ImportError:
    AITradingAssistant = None
    GeminiTradingAssistant = None

class AITradingChat:
    """Sistema di chat interattiva con AI Trading Assistant"""
    
    def __init__(self, ai_assistant, market_analyzer=None):
        self.ai_assistant = ai_assistant
        self.market_analyzer = market_analyzer
        self.chat_history = []
        self.current_trading_context = {}
        
    def start_trading_discussion(self, symbol: str, ai_signal: Dict, market_data: Dict = None):
        """Inizia una discussione su un segnale di trading specifico"""
        self.current_trading_context = {
            'symbol': symbol,
            'ai_signal': ai_signal,
            'market_data': market_data,
            'discussion_started': datetime.now().isoformat(),
            'user_notes': []
        }
        
        # Messaggio di benvenuto personalizzato
        welcome_msg = self._generate_welcome_message(symbol, ai_signal)
        self.chat_history.append({
            'role': 'assistant',
            'content': welcome_msg,
            'timestamp': datetime.now().isoformat(),
            'type': 'welcome'
        })
        
        return welcome_msg
    
    def send_message(self, user_message: str, message_type: str = 'question') -> Dict:
        """
        Invia un messaggio all'AI e ricevi risposta nel contesto del trading
        
        message_type può essere:
        - 'question': domanda generale
        - 'opinion': condivisione di opinione personale
        - 'scenario': richiesta di scenario alternativo
        - 'update': aggiornamento condizioni di mercato
        """
        
        # Aggiungi messaggio utente alla cronologia
        self.chat_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat(),
            'type': message_type
        })
        
        try:
            # Costruisci il prompt contestuale
            conversation_prompt = self._build_conversation_prompt(user_message, message_type)
            
            # Invia alla AI
            if hasattr(self.ai_assistant, 'chat_about_trading'):
                # Metodo specifico per chat se esiste
                ai_response = self.ai_assistant.chat_about_trading(conversation_prompt)
            else:
                # Fallback usando metodo generale con flag chat_mode
                ai_response = self.ai_assistant.analyze_trading_opportunity({
                    'symbol': self.current_trading_context.get('symbol', ''),
                    'conversation_prompt': conversation_prompt,
                    'chat_mode': True,
                    'current_price': self.current_trading_context.get('market_data', {}).get('current_price', 0)
                })
            
            response_content = self._extract_response_content(ai_response)
            
            # Aggiungi risposta AI alla cronologia
            self.chat_history.append({
                'role': 'assistant',
                'content': response_content,
                'timestamp': datetime.now().isoformat(),
                'type': 'response'
            })
            
            return {
                'success': True,
                'response': response_content,
                'conversation_id': len(self.chat_history),
                'context': self.current_trading_context['symbol']
            }
            
        except Exception as e:
            error_msg = f"Errore nella chat AI: {str(e)}"
            self.chat_history.append({
                'role': 'system',
                'content': error_msg,
                'timestamp': datetime.now().isoformat(),
                'type': 'error'
            })
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def _generate_welcome_message(self, symbol: str, ai_signal: Dict) -> str:
        """Genera messaggio di benvenuto personalizzato"""
        action = ai_signal.get('action', 'ANALIZZA')
        confidence = ai_signal.get('confidence', 0)
        reasoning = ai_signal.get('reasoning', '')
        
        return f"""🤖 **Chat AI Trading - {symbol}**

Ho analizzato {symbol} e suggerisco: **{action}** (confidence: {confidence}%)

📊 **Il mio ragionamento:**
{reasoning}

💬 **Puoi chiedermi:**
• "Perché hai scelto questo entry point?"
• "Cosa succede se Bitcoin cala del 5%?"
• "La mia analisi dice che potrebbe salire, cosa ne pensi?"
• "Aggiorna l'analisi considerando che..."

**Cosa vuoi discutere di questa operazione?**"""
    
    def _build_conversation_prompt(self, user_message: str, message_type: str) -> str:
        """Costruisce il prompt per la conversazione"""
        
        symbol = self.current_trading_context.get('symbol', '')
        ai_signal = self.current_trading_context.get('ai_signal', {})
        market_data = self.current_trading_context.get('market_data', {})
        
        # Context base con dati tecnici dettagliati
        context = f"""
CONTESTO TRADING COMPLETO - {symbol}:

SEGNALE AI GENERATO:
- Azione: {ai_signal.get('action', 'N/A')}
- Entry Price: ${ai_signal.get('entry_price', 'N/A')}
- Stop Loss: ${ai_signal.get('stop_loss', 'N/A')}
- Take Profit 1: ${ai_signal.get('take_profit_1', 'N/A')}
- Take Profit 2: ${ai_signal.get('take_profit_2', 'N/A')}
- Confidence: {ai_signal.get('confidence', 0)}%
- Risk/Reward: {ai_signal.get('risk_reward_ratio', 'N/A')}
- Position Size: {ai_signal.get('position_size_percent', 'N/A')}%

PREZZO CORRENTE: ${market_data.get('current_price', ai_signal.get('entry_price', 'N/A'))}

ANALISI MULTI-TIMEFRAME:"""
        
        # Aggiungi dati dettagliati per timeframe se disponibili
        timeframes = market_data.get('timeframes', {})
        if timeframes:
            for tf_name, tf_data in timeframes.items():
                context += f"""
{tf_name.upper()}:
  - RSI: {tf_data.get('rsi', 'N/A')}
  - EMA 20: ${tf_data.get('ema_20', 'N/A')}
  - EMA 50: ${tf_data.get('ema_50', 'N/A')}
  - Trend: {tf_data.get('trend', 'N/A')}
  - Segnali: {', '.join(tf_data.get('reversal_signals', [])) if tf_data.get('reversal_signals') else 'Nessuno'}"""
        else:
            # Fallback con dati base se non abbiamo timeframes strutturati
            context += f"""
DATI TECNICI DISPONIBILI:
- RSI 14: {ai_signal.get('rsi', market_data.get('rsi', 'N/A'))}
- EMA 20: ${ai_signal.get('ema_20', market_data.get('ema_20', 'N/A'))}
- EMA 50: ${ai_signal.get('ema_50', market_data.get('ema_50', 'N/A'))}
- Volume 24h: {market_data.get('volume_24h', 'N/A')}"""
        
        # Aggiungi summary se disponibile
        summary = market_data.get('summary', {})
        if summary and summary.get('overall_trend') != 'N/A':
            context += f"""

RIASSUNTO TREND:
- Trend Generale (4h): {summary.get('overall_trend', 'N/A')}
- Trend Breve (15m): {summary.get('short_term_trend', 'N/A')}
- RSI Attuale: {summary.get('current_rsi', 'N/A')}
- Segnali Inversione: {', '.join(summary.get('all_reversal_signals', [])) if summary.get('all_reversal_signals') else 'Nessuno'}"""
        
        context += f"""

RAGIONAMENTO ORIGINALE AI:
{ai_signal.get('reasoning', 'Nessun ragionamento fornito')}

CRONOLOGIA CONVERSAZIONE:"""
        
        # Aggiungi ultimi 5 messaggi per contesto
        recent_messages = self.chat_history[-5:] if len(self.chat_history) > 5 else self.chat_history
        for msg in recent_messages:
            if msg['role'] != 'system':
                context += f"\n{msg['role'].upper()}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}"
        
        # Prompt specifico per tipo di messaggio
        if message_type == 'question':
            prompt_instruction = "L'utente ha una domanda sulla mia analisi. Rispondi usando i dati tecnici multi-timeframe forniti sopra. Sii specifico con i numeri."
        elif message_type == 'opinion':
            prompt_instruction = "L'utente condivide la sua opinione. Analizzala rispetto ai dati tecnici multi-timeframe sopra. Trova punti di accordo/disaccordo con dati specifici."
        elif message_type == 'scenario':
            prompt_instruction = "L'utente chiede uno scenario alternativo. Considera la nuova condizione usando tutti i dati tecnici forniti sopra."
        elif message_type == 'update':
            prompt_instruction = "L'utente fornisce informazioni aggiornate. Rivedi l'analisi considerando queste info + tutti i dati tecnici sopra."
        else:
            prompt_instruction = "Rispondi usando tutti i dati tecnici multi-timeframe forniti sopra."
        
        full_prompt = f"""{context}

ISTRUZIONE: {prompt_instruction}

REGOLE IMPORTANTI:
- Usa SEMPRE i dati tecnici specifici forniti sopra (prezzo, RSI, EMA per ogni timeframe)
- Fai riferimento a numeri concreti quando spieghi le tue decisioni
- Non dire mai "mancano dati" - lavora con quello che hai fornito sopra
- Se alcuni valori sono N/A, concentrati su quelli disponibili
- Mantieni il focus su {symbol} e l'operazione in discussione

MESSAGGIO UTENTE: {user_message}

RISPONDI in modo:
- Conversazionale e amichevole
- Specifico sui dati tecnici (usa i numeri sopra)
- Pratico con suggerimenti actionable
- Coerente con l'analisi originale ma aggiornabile se necessario
- Con emoji per rendere la chat più engaging 🤖📊📈"""

        return full_prompt
        
        # Prompt specifico per tipo di messaggio
        if message_type == 'question':
            prompt_instruction = "L'utente ha una domanda sulla mia analisi. Rispondi usando TUTTI i dati tecnici disponibili sopra."
        elif message_type == 'opinion':
            prompt_instruction = "L'utente condivide la sua opinione. Analizzala rispetto ai dati tecnici sopra e trova punti di accordo/disaccordo."
        elif message_type == 'scenario':
            prompt_instruction = "L'utente chiede uno scenario alternativo. Considera la nuova condizione con i dati tecnici attuali."
        elif message_type == 'update':
            prompt_instruction = "L'utente fornisce nuove informazioni. Rivedi l'analisi con questi dati aggiuntivi."
        else:
            prompt_instruction = "Rispondi usando i dati tecnici completi forniti sopra."
        
        full_prompt = f"""{context}

ISTRUZIONE: {prompt_instruction}

IMPORTANTE: 
- Usa SEMPRE i dati tecnici forniti sopra (prezzo, RSI, EMA, trend)
- NON dire mai "mancano dati" - tutti i dati necessari sono sopra
- Se alcuni valori sono N/A, concentrati su quelli disponibili
- Mantieni il contesto dell'analisi originale per {symbol}

MESSAGGIO UTENTE: {user_message}

RISPONDI:
- In modo conversazionale e dettagliato
- Riferendoti specificamente ai livelli tecnici
- Usando i dati sopra per supportare la tua risposta
- Considerando scenari di mercato realistici
- Con suggerimenti pratici per il trading"""

        return full_prompt
    
    def _extract_response_content(self, ai_response) -> str:
        """Estrae il contenuto della risposta dall'AI"""
        if isinstance(ai_response, dict):
            if 'response' in ai_response:
                return ai_response['response']
            elif 'signal' in ai_response and 'reasoning' in ai_response['signal']:
                return ai_response['signal']['reasoning']
            elif 'content' in ai_response:
                return ai_response['content']
        elif isinstance(ai_response, str):
            return ai_response
        
        return "Risposta ricevuta ma in formato non riconosciuto."
    
    def get_chat_history(self) -> List[Dict]:
        """Restituisce la cronologia completa della chat"""
        return self.chat_history
    
    def save_trading_notes(self, note: str):
        """Salva una nota personale sulla discussione"""
        if 'user_notes' not in self.current_trading_context:
            self.current_trading_context['user_notes'] = []
        
        self.current_trading_context['user_notes'].append({
            'note': note,
            'timestamp': datetime.now().isoformat()
        })
    
    def export_conversation(self) -> Dict:
        """Esporta l'intera conversazione per salvataggio"""
        return {
            'trading_context': self.current_trading_context,
            'chat_history': self.chat_history,
            'exported_at': datetime.now().isoformat()
        }
    
    def clear_chat(self):
        """Pulisce la chat corrente"""
        self.chat_history = []
        self.current_trading_context = {}

# Estensione per il GeminiTradingAssistant per supportare chat
class GeminiTradingAssistantWithChat(GeminiTradingAssistant):
    """Estende GeminiTradingAssistant con capacità di chat"""
    
    def chat_about_trading(self, conversation_prompt: str) -> Dict:
        """Metodo specifico per conversazioni di trading"""
        try:
            chat = self.model.start_chat(history=[])
            
            response = chat.send_message(
                f"Sei un esperto trader che sta discutendo una strategia. "
                f"Rispondi in modo conversazionale e pratico.\n\n{conversation_prompt}"
            )
            
            return {
                'success': True,
                'response': response.text,
                'type': 'chat_response'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Errore chat Gemini: {str(e)}",
                'response': "Mi dispiace, ho avuto un problema tecnico. Puoi riprovare?"
            }

if __name__ == "__main__":
    # Test del sistema di chat
    print("🧪 Test AI Trading Chat System")
    
    # Mock AI Assistant per test
    class MockAIAssistant:
        def analyze_trading_opportunity(self, data):
            if data.get('chat_mode'):
                return {
                    'success': True,
                    'response': f"Questa è una risposta di test alla tua domanda sul trading."
                }
            return {'success': True, 'signal': {'action': 'BUY', 'confidence': 85}}
    
    # Test chat
    mock_ai = MockAIAssistant()
    chat_system = AITradingChat(mock_ai)
    
    # Simula una discussione
    test_signal = {
        'action': 'BUY',
        'confidence': 85,
        'entry_price': 3.60,
        'stop_loss': 3.40,
        'take_profit_1': 3.90,
        'reasoning': 'Pattern bullish con confluenza su più timeframes'
    }
    
    welcome = chat_system.start_trading_discussion('ADAUSDT', test_signal)
    print("Welcome message:", welcome)
    
    response = chat_system.send_message("Perché hai scelto questo entry point?", "question")
    print("Chat response:", response)
    
    print("✅ Test chat completato!")
