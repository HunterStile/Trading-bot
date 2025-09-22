from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Aggiungi path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from ai_enhanced_analysis import AIEnhancedMarketAnalysis
    from ai_trading_assistant import AITradingAssistant
    from ai_trading_chat import AITradingChat, GeminiTradingAssistantWithChat
except ImportError:
    AIEnhancedMarketAnalysis = None
    AITradingAssistant = None
    AITradingChat = None
    GeminiTradingAssistantWithChat = None

ai_trading_bp = Blueprint('ai_trading', __name__, url_prefix='/ai-trading')

# Variabile globale per l'AI assistant e chat
ai_enhanced_analyzer = None
ai_chat_system = None

def initialize_ai_trading(market_analyzer, api_key=None, provider='gemini'):
    """Inizializza AI Trading Assistant con Market Analyzer esistente"""
    global ai_enhanced_analyzer
    
    # Se non viene passata una API key, prova a leggerla dal file .env
    if not api_key:
        if provider == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY')
        elif provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key and api_key != 'inserisci_qui_la_tua_gemini_api_key':
            print(f"🔑 Usando {provider.upper()} API key dal file .env")
        else:
            print(f"⚠️ {provider.upper()} API key non trovata nel file .env")
            return False
    
    if AIEnhancedMarketAnalysis and api_key:
        try:
            ai_enhanced_analyzer = AIEnhancedMarketAnalysis(
                market_analyzer, 
                ai_api_key=api_key,
                ai_provider=provider
            )
            print(f"🤖 AI Trading Assistant inizializzato con {provider.upper()}!")
            return True
        except Exception as e:
            print(f"❌ Errore inizializzazione AI Trading: {e}")
            return False
    else:
        print(f"⚠️ AI Trading non disponibile - configurare {provider.upper()} API key")
        return False

@ai_trading_bp.route('/')
def ai_trading_dashboard():
    """Dashboard AI Trading"""
    return render_template('ai_trading.html')

@ai_trading_bp.route('/api/status', methods=['GET'])
def get_ai_status():
    """Stato del sistema AI"""
    global ai_enhanced_analyzer
    
    return jsonify({
        'success': True,
        'ai_enabled': ai_enhanced_analyzer is not None and ai_enhanced_analyzer.ai_enabled,
        'ai_provider': 'gemini' if ai_enhanced_analyzer and ai_enhanced_analyzer.ai_enabled else None,
        'timestamp': datetime.now().isoformat()
    })

@ai_trading_bp.route('/api/test-connection', methods=['POST'])
def test_ai_connection():
    """Testa la connessione AI"""
    global ai_enhanced_analyzer
    
    try:
        if not ai_enhanced_analyzer or not ai_enhanced_analyzer.ai_enabled:
            return jsonify({'success': False, 'error': 'AI non configurato'})
        
        if hasattr(ai_enhanced_analyzer.ai_assistant, 'test_connection'):
            success = ai_enhanced_analyzer.ai_assistant.test_connection()
            return jsonify({
                'success': success,
                'message': 'Test connessione completato',
                'connected': success
            })
        else:
            return jsonify({'success': False, 'error': 'Test non supportato'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/analyze-symbol', methods=['POST'])
def analyze_symbol_with_ai():
    """Analizza singolo simbolo con AI"""
    global ai_enhanced_analyzer
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Simbolo richiesto'})
        
        if not ai_enhanced_analyzer or not ai_enhanced_analyzer.ai_enabled:
            return jsonify({'success': False, 'error': 'AI Trading non disponibile'})
        
        # Ottieni dati dall'analisi normale - creiamo un'analisi su misura per il simbolo
        symbol_analysis = {}
        timeframes = [15, 60, 240, 1440]  # 15m, 1h, 4h, 1d
        
        for tf in timeframes:
            tf_data = ai_enhanced_analyzer.market_analyzer.analyze_symbol(symbol, tf)
            if tf_data:
                symbol_analysis[f'{tf}m'] = tf_data
        
        if not symbol_analysis:
            return jsonify({'success': False, 'error': f'Dati non disponibili per {symbol}'})
        
        # Prepara i dati per l'AI
        ai_input_data = {
            'symbol': symbol,
            'current_price': list(symbol_analysis.values())[0].get('current_price', 0) if symbol_analysis else 0,
            'timeframes': symbol_analysis,
            'reversal_signals': []
        }
        
        # Raccoglie segnali di inversione da tutti i timeframes
        for tf_name, tf_data in symbol_analysis.items():
            if tf_data and 'reversal_signals' in tf_data:
                ai_input_data['reversal_signals'].extend(tf_data['reversal_signals'])
        
        # Analizza con AI
        ai_result = ai_enhanced_analyzer.ai_assistant.analyze_trading_opportunity(ai_input_data)
        
        if ai_result['success']:
            return jsonify({
                'success': True,
                'symbol': symbol,
                'ai_signal': ai_result['signal'],
                'market_data': symbol_analysis,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Errore analisi AI: {ai_result.get("error", "Unknown")}'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/top-opportunities', methods=['GET'])
def get_top_opportunities():
    """Ottieni top opportunità trading AI"""
    global ai_enhanced_analyzer
    
    try:
        if not ai_enhanced_analyzer or not ai_enhanced_analyzer.ai_enabled:
            return jsonify({'success': False, 'error': 'AI Trading non disponibile'})
        
        limit = request.args.get('limit', 5, type=int)
        opportunities = ai_enhanced_analyzer.get_top_ai_opportunities(limit)
        
        return jsonify({
            'success': True,
            'opportunities': opportunities,
            'count': len(opportunities),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/analyze-all', methods=['POST'])
def analyze_all_with_ai():
    """Analizza tutti i simboli e genera segnali AI"""
    global ai_enhanced_analyzer
    
    try:
        if not ai_enhanced_analyzer or not ai_enhanced_analyzer.ai_enabled:
            return jsonify({'success': False, 'error': 'AI Trading non disponibile'})
        
        data = request.get_json() or {}
        symbols = data.get('symbols', None)  # None = tutti i simboli default
        
        # Analisi completa con AI
        analysis_result = ai_enhanced_analyzer.analyze_with_ai_signals(symbols)
        
        return jsonify({
            'success': True,
            'analysis': analysis_result,
            'ai_signals_count': len(analysis_result.get('ai_signals', {})),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/create-alert-from-ai', methods=['POST'])
def create_alert_from_ai_signal():
    """Crea alert automaticamente da segnale AI"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        ai_signal = data.get('ai_signal')
        
        if not symbol or not ai_signal:
            return jsonify({'success': False, 'error': 'Simbolo e segnale AI richiesti'})
        
        # Crea alert per stop loss
        stop_loss_alert = {
            'symbol': symbol,
            'alert_type': 'PRICE',
            'target_price': ai_signal.get('stop_loss'),
            'direction': 'ABOVE' if ai_signal.get('action') == 'SELL' else 'BELOW',
            'message': f"🤖 AI Stop Loss - {ai_signal.get('reasoning', '')[:50]}..."
        }
        
        # Crea alert per take profit
        tp1_alert = {
            'symbol': symbol,
            'alert_type': 'PRICE',
            'target_price': ai_signal.get('take_profit_1'),
            'direction': 'BELOW' if ai_signal.get('action') == 'SELL' else 'ABOVE',
            'message': f"🎯 AI Take Profit 1 - Confidence: {ai_signal.get('confidence')}%"
        }
        
        return jsonify({
            'success': True,
            'message': 'Alert AI creati automaticamente',
            'alerts_created': [stop_loss_alert, tp1_alert]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/configure', methods=['POST'])
def configure_ai_trading():
    """Configura API key e parametri AI"""
    global ai_enhanced_analyzer
    
    try:
        data = request.get_json()
        # Supporta sia OpenAI che Gemini
        api_key = data.get('gemini_api_key') or data.get('openai_api_key')
        provider = data.get('provider', 'gemini')  # Default a Gemini
        
        if not api_key:
            return jsonify({'success': False, 'error': f'API key {provider.upper()} richiesta'})
        
        # Salva la nuova API key nel file .env
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_path):
                # Leggi il file .env
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Aggiorna o aggiungi la chiave
                key_name = f'{provider.upper()}_API_KEY'
                key_found = False
                
                for i, line in enumerate(lines):
                    if line.startswith(f'{key_name}='):
                        lines[i] = f'{key_name}={api_key}\n'
                        key_found = True
                        break
                
                # Se non trovata, aggiungila
                if not key_found:
                    lines.append(f'{key_name}={api_key}\n')
                
                # Scrivi il file aggiornato
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                print(f"💾 API key {provider.upper()} salvata nel file .env")
            else:
                print(f"⚠️ File .env non trovato in {env_path}")
        except Exception as e:
            print(f"⚠️ Errore nel salvataggio dell'API key: {e}")
        
        # Ottieni market analyzer dall'app
        market_analyzer = current_app.config.get('MARKET_ANALYZER')
        
        if not market_analyzer:
            return jsonify({'success': False, 'error': 'Market Analyzer non disponibile'})
        
        # Inizializza AI
        success = initialize_ai_trading(market_analyzer, api_key, provider)
        
        if success:
            # Inizializza anche il sistema di chat
            global ai_chat_system
            if ai_enhanced_analyzer and ai_enhanced_analyzer.ai_assistant and AITradingChat:
                ai_chat_system = AITradingChat(
                    ai_enhanced_analyzer.ai_assistant, 
                    market_analyzer
                )
                print("💬 Sistema di chat AI inizializzato!")
            
            return jsonify({
                'success': True,
                'message': f'AI Trading configurato con successo usando {provider.upper()}',
                'ai_enabled': True,
                'chat_enabled': ai_chat_system is not None,
                'provider': provider
            })
        else:
            return jsonify({'success': False, 'error': 'Errore configurazione AI'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/chat/start', methods=['POST'])
def start_chat_discussion():
    """Inizia una chat su un segnale di trading specifico"""
    global ai_chat_system, ai_enhanced_analyzer
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        ai_signal = data.get('ai_signal', {})
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Simbolo richiesto'})
        
        # Ottieni dati di mercato aggiornati per il simbolo
        market_data = {}
        if ai_enhanced_analyzer and ai_enhanced_analyzer.market_analyzer:
            try:
                # Esegui analisi per ottenere dati tecnici aggiornati
                analysis = ai_enhanced_analyzer.market_analyzer.analyze_market([symbol])
                
                if 'analyses' in analysis and symbol in analysis['analyses']:
                    symbol_data = analysis['analyses'][symbol]
                    
                    # Estrai dati da tutti i timeframes
                    for tf, tf_data in symbol_data.items():
                        if isinstance(tf_data, dict):
                            market_data.update({
                                f'current_price': tf_data.get('current_price', ai_signal.get('entry_price', 0)),
                                f'rsi': tf_data.get('rsi', 'N/A'),
                                f'ema_20': tf_data.get('ema_20', 'N/A'),
                                f'ema_50': tf_data.get('ema_50', 'N/A'),
                                f'trend_{tf}m': tf_data.get('trend', {}).get('trend', 'N/A'),
                                f'volume_24h': tf_data.get('volume_24h', 'N/A')
                            })
                
                print(f"📊 Dati mercato ottenuti per {symbol}: {list(market_data.keys())}")
                
            except Exception as e:
                print(f"⚠️ Errore ottenimento dati mercato: {e}")
                # Usa dati dal segnale AI come fallback
                market_data = {
                    'current_price': ai_signal.get('entry_price', 0),
                    'rsi': 'N/A',
                    'ema_20': 'N/A', 
                    'ema_50': 'N/A'
                }
        
        welcome_message = ai_chat_system.start_trading_discussion(symbol, ai_signal, market_data)
        
        return jsonify({
            'success': True,
            'welcome_message': welcome_message,
            'chat_id': len(ai_chat_system.chat_history),
            'symbol': symbol,
            'market_data_loaded': len(market_data) > 0
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/chat/message', methods=['POST'])
def send_chat_message():
    """Invia un messaggio nella chat AI"""
    global ai_chat_system
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        message_type = data.get('type', 'question')  # question, opinion, scenario, update
        
        if not message:
            return jsonify({'success': False, 'error': 'Messaggio richiesto'})
        
        response = ai_chat_system.send_message(message, message_type)
        
        # Aggiungi la cronologia recente
        recent_history = ai_chat_system.get_chat_history()[-10:]  # Ultimi 10 messaggi
        
        return jsonify({
            'success': True,
            'ai_response': response.get('response', ''),
            'conversation_id': response.get('conversation_id', 0),
            'chat_history': recent_history,
            'context_symbol': response.get('context', '')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Ottieni cronologia completa della chat"""
    global ai_chat_system
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        history = ai_chat_system.get_chat_history()
        context = ai_chat_system.current_trading_context
        
        return jsonify({
            'success': True,
            'chat_history': history,
            'trading_context': context,
            'total_messages': len(history)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """Pulisce la chat corrente"""
    global ai_chat_system
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        ai_chat_system.clear_chat()
        
        return jsonify({
            'success': True,
            'message': 'Chat pulita con successo'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/chat/save-note', methods=['POST'])
def save_trading_note():
    """Salva una nota personale sulla discussione"""
    global ai_chat_system
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        data = request.get_json()
        note = data.get('note', '').strip()
        
        if not note:
            return jsonify({'success': False, 'error': 'Nota richiesta'})
        
        ai_chat_system.save_trading_notes(note)
        
        return jsonify({
            'success': True,
            'message': 'Nota salvata con successo'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
