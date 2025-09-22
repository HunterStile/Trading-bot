from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import sys
import os
import threading
import time
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
ai_telegram_notifier = None  # Notifier Telegram per AI

# Variabili per sistema automatico AI
ai_auto_analysis_thread = None
ai_auto_analysis_active = False
ai_auto_config = {
    'analysis_interval': 30,  # minuti
    'signal_interval': 60,    # minuti
    'enabled': False,
    'telegram_enabled': True,
    'min_confidence': 70,     # confidenza minima per inviare segnali
    'max_signals_per_hour': 5  # limite segnali per ora
}

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

def set_ai_telegram_notifier(notifier):
    """Imposta il notificatore Telegram per AI"""
    global ai_telegram_notifier
    ai_telegram_notifier = notifier
    print(f"✅ Telegram notifier configurato per AI Trading: {notifier is not None}")
    print(f"🔧 Notifier type: {type(notifier) if notifier else 'None'}")

def init_ai_trading_system(app):
    """Inizializza il sistema AI Trading con il notifier Telegram dell'app"""
    telegram_notifier = app.config.get('TELEGRAM_NOTIFIER')
    if telegram_notifier:
        print(f"🔧 Configurando AI Trading notifier: {type(telegram_notifier)}")
        set_ai_telegram_notifier(telegram_notifier)
        print("✅ AI Trading sistema inizializzato con Telegram")
    else:
        print("⚠️ AI Trading inizializzato senza Telegram notifier")

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
        provided_market_data = data.get('market_data', {})
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Simbolo richiesto'})
        
        print(f"🔍 Chat start per {symbol}")
        print(f"📊 AI Signal ricevuto: {list(ai_signal.keys())}")
        print(f"📈 Market data forniti: {list(provided_market_data.keys())}")
        
        # Usa i dati forniti dal frontend se disponibili, altrimenti raccogli nuovi dati
        if provided_market_data and len(provided_market_data) > 2:
            print("✅ Usando dati di mercato forniti dal frontend")
            market_data = provided_market_data
        else:
            print("🔄 Raccogliendo nuovi dati di mercato...")
            market_data = {}
            if ai_enhanced_analyzer and ai_enhanced_analyzer.market_analyzer:
                try:
                    # Esegui analisi completa e filtra per il simbolo richiesto
                    analysis = ai_enhanced_analyzer.market_analyzer.analyze_market()
                    
                    if 'analyses' in analysis and symbol in analysis['analyses']:
                        symbol_data = analysis['analyses'][symbol]
                        
                        # Costruisci dati completi multi-timeframe
                        market_data = {
                            'symbol': symbol,
                            'current_price': 0,
                            'timeframes': {},
                            'summary': {}
                        }
                        
                        # Estrai dati da tutti i timeframes
                        for tf, tf_data in symbol_data.items():
                            if isinstance(tf_data, dict) and str(tf).isdigit():
                                # Aggiorna prezzo corrente dal primo timeframe disponibile
                                if market_data['current_price'] == 0 and 'current_price' in tf_data:
                                    market_data['current_price'] = tf_data['current_price']
                                
                                # Aggiungi dati per questo timeframe
                                tf_name = f"{tf}m"
                                market_data['timeframes'][tf_name] = {
                                    'rsi': tf_data.get('rsi', 'N/A'),
                                    'ema_20': tf_data.get('ema_20', 'N/A'),
                                    'ema_50': tf_data.get('ema_50', 'N/A'),
                                    'trend': tf_data.get('trend', {}).get('trend', 'N/A'),
                                    'current_price': tf_data.get('current_price', 'N/A'),
                                    'volume_24h': tf_data.get('volume_24h', 'N/A'),
                                    'reversal_signals': tf_data.get('reversal_signals', [])
                                }
                        
                        # Crea summary con dati più utilizzati
                        market_data['summary'] = {
                            'overall_trend': market_data['timeframes'].get('240m', {}).get('trend', 'N/A'),
                            'short_term_trend': market_data['timeframes'].get('15m', {}).get('trend', 'N/A'),
                            'current_rsi': market_data['timeframes'].get('60m', {}).get('rsi', 'N/A'),
                            'all_reversal_signals': []
                        }
                        
                        # Raccogli tutti i segnali di inversione
                        for tf_data in market_data['timeframes'].values():
                            if isinstance(tf_data.get('reversal_signals'), list):
                                market_data['summary']['all_reversal_signals'].extend(tf_data['reversal_signals'])
                        
                        print(f"💾 Dati di mercato completi per {symbol}: {len(market_data['timeframes'])} timeframes")
                    
                except Exception as e:
                    print(f"⚠️ Errore ottenimento dati mercato: {e}")
                    # Fallback con dati minimi dal segnale AI
                    market_data = {
                        'current_price': ai_signal.get('entry_price', 0),
                        'summary': {'note': 'Dati limitati - solo dal segnale AI'}
                    }
            
            print(f"📊 Dati mercato ottenuti per {symbol}: {list(market_data.keys())}")
        
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

@ai_trading_bp.route('/api/chat/refresh-analysis', methods=['POST'])
def refresh_analysis_for_chat():
    """Aggiorna l'analisi per un simbolo specifico e invia i dati alla chat"""
    global ai_chat_system, ai_enhanced_analyzer
    
    if not ai_chat_system:
        return jsonify({'success': False, 'error': 'Sistema di chat non disponibile'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Simbolo richiesto'})
        
        print(f"🔄 Refresh analisi per {symbol}")
        
        # Ottieni analisi aggiornata
        market_data = {}
        if ai_enhanced_analyzer and ai_enhanced_analyzer.market_analyzer:
            try:
                # Esegui analisi completa e filtra per il simbolo richiesto
                analysis = ai_enhanced_analyzer.market_analyzer.analyze_market()
                
                if 'analyses' in analysis and symbol in analysis['analyses']:
                    symbol_data = analysis['analyses'][symbol]
                    
                    # Costruisci dati completi multi-timeframe
                    market_data = {
                        'symbol': symbol,
                        'current_price': 0,
                        'timeframes': {},
                        'summary': {}
                    }
                    
                    # Estrai dati da tutti i timeframes
                    for tf, tf_data in symbol_data.items():
                        if isinstance(tf_data, dict) and str(tf).isdigit():
                            # Aggiorna prezzo corrente dal primo timeframe disponibile
                            if market_data['current_price'] == 0 and 'current_price' in tf_data:
                                market_data['current_price'] = tf_data['current_price']
                            
                            # Aggiungi dati per questo timeframe
                            tf_name = f"{tf}m"
                            market_data['timeframes'][tf_name] = {
                                'rsi': tf_data.get('rsi', 'N/A'),
                                'ema_20': tf_data.get('ema_20', 'N/A'),
                                'ema_50': tf_data.get('ema_50', 'N/A'),
                                'trend': tf_data.get('trend', {}).get('trend', 'N/A'),
                                'current_price': tf_data.get('current_price', 'N/A'),
                                'volume_24h': tf_data.get('volume_24h', 'N/A'),
                                'reversal_signals': tf_data.get('reversal_signals', [])
                            }
                    
                    # Crea summary con dati più utilizzati
                    market_data['summary'] = {
                        'overall_trend': market_data['timeframes'].get('240m', {}).get('trend', 'N/A'),
                        'short_term_trend': market_data['timeframes'].get('15m', {}).get('trend', 'N/A'),
                        'current_rsi': market_data['timeframes'].get('60m', {}).get('rsi', 'N/A'),
                        'all_reversal_signals': []
                    }
                    
                    # Raccogli tutti i segnali di inversione
                    for tf_data in market_data['timeframes'].values():
                        if isinstance(tf_data.get('reversal_signals'), list):
                            market_data['summary']['all_reversal_signals'].extend(tf_data['reversal_signals'])
                    
                    print(f"💾 Analisi aggiornata per {symbol}: {len(market_data['timeframes'])} timeframes")
                    
                    # Invia messaggio di analisi aggiornata alla chat
                    analysis_summary = f"""📊 **ANALISI AGGIORNATA per {symbol}**

💰 **Prezzo attuale:** ${market_data['current_price']:.4f}

📈 **Trend Analysis:**
• Trend generale (4h): {market_data['summary']['overall_trend']}
• Trend breve termine (15m): {market_data['summary']['short_term_trend']}

📊 **Indicatori Tecnici:**"""
                    
                    # Aggiungi dettagli per ogni timeframe
                    for tf_name, tf_data in market_data['timeframes'].items():
                        analysis_summary += f"""
**{tf_name}:**
  - RSI: {tf_data['rsi']}
  - EMA 20: {tf_data['ema_20']}
  - EMA 50: {tf_data['ema_50']}
  - Volume 24h: {tf_data['volume_24h']}"""
                    
                    # Aggiungi segnali di inversione se presenti
                    if market_data['summary']['all_reversal_signals']:
                        analysis_summary += f"\n\n🔄 **Segnali di inversione:** {', '.join(market_data['summary']['all_reversal_signals'])}"
                    
                    analysis_summary += f"\n\n⏰ Aggiornato: {datetime.now().strftime('%H:%M:%S')}"
                    
                    return jsonify({
                        'success': True,
                        'message': analysis_summary,
                        'market_data': market_data,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Simbolo {symbol} non trovato nell\'analisi corrente'
                    })
                    
            except Exception as e:
                print(f"⚠️ Errore refresh analisi: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Errore durante l\'aggiornamento dell\'analisi: {str(e)}'
                })
        else:
            return jsonify({
                'success': False,
                'error': 'Analizzatore di mercato non disponibile'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== SISTEMA AUTOMATICO AI =====

def ai_auto_analysis_loop():
    """Loop principale per analisi automatica AI"""
    global ai_auto_analysis_active, ai_enhanced_analyzer, ai_auto_config
    
    last_analysis_time = 0
    last_signal_time = 0
    signals_sent_this_hour = 0
    current_hour = datetime.now().hour
    
    print("🤖 Sistema automatico AI avviato!")
    
    while ai_auto_analysis_active:
        try:
            current_time = time.time()
            now = datetime.now()
            
            # Reset contatore segnali ogni ora
            if now.hour != current_hour:
                signals_sent_this_hour = 0
                current_hour = now.hour
                print(f"🔄 Reset contatore segnali AI per ora {current_hour}")
            
            # Verifica se è tempo di fare analisi
            if (current_time - last_analysis_time) >= (ai_auto_config['analysis_interval'] * 60):
                print(f"🔍 Esecuzione analisi automatica AI...")
                
                if ai_enhanced_analyzer and ai_enhanced_analyzer.ai_enabled:
                    try:
                        # Esegui analisi completa con AI
                        analysis_result = ai_enhanced_analyzer.analyze_with_ai_signals()
                        ai_signals = analysis_result.get('ai_signals', {})
                        
                        print(f"📊 Analisi completata: {len(ai_signals)} segnali AI trovati")
                        
                        # Verifica se è tempo di inviare segnali
                        if ((current_time - last_signal_time) >= (ai_auto_config['signal_interval'] * 60) and
                            ai_auto_config['telegram_enabled'] and
                            signals_sent_this_hour < ai_auto_config['max_signals_per_hour']):
                            
                            # Filtra segnali per confidenza minima e aggiungi simbolo
                            high_confidence_signals = []
                            for symbol, signal in ai_signals.items():
                                if signal.get('confidence', 0) >= ai_auto_config['min_confidence']:
                                    # Aggiungi il simbolo al segnale se manca
                                    signal['symbol'] = symbol
                                    high_confidence_signals.append(signal)
                            
                            if high_confidence_signals:
                                # Ordina per confidenza e prendi i migliori
                                high_confidence_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
                                signals_to_send = high_confidence_signals[:2]  # Max 2 segnali per volta
                                
                                for signal in signals_to_send:
                                    if signals_sent_this_hour < ai_auto_config['max_signals_per_hour']:
                                        send_ai_signal_telegram(signal)
                                        signals_sent_this_hour += 1
                                        time.sleep(2)  # Pausa tra messaggi
                                
                                last_signal_time = current_time
                                print(f"✅ Inviati {len(signals_to_send)} segnali AI via Telegram")
                        
                        last_analysis_time = current_time
                        
                    except Exception as e:
                        print(f"❌ Errore durante analisi automatica AI: {e}")
                
            # Pausa prima del prossimo ciclo
            time.sleep(30)  # Controlla ogni 30 secondi
            
        except Exception as e:
            print(f"❌ Errore nel loop automatico AI: {e}")
            time.sleep(60)  # Pausa più lunga in caso di errore

def send_ai_signal_telegram(signal):
    """Invia segnale AI via Telegram"""
    global ai_telegram_notifier
    
    try:
        if ai_telegram_notifier:
            # Estrai dati con le chiavi corrette dall'AI
            symbol = signal.get('symbol', 'N/A')  # Questo campo potrebbe mancare
            action = signal.get('action', 'N/A')
            confidence = signal.get('confidence', 0)
            entry = signal.get('entry_price', 0)  # Corretto: entry_price
            stop_loss = signal.get('stop_loss', 0)
            take_profit_1 = signal.get('take_profit_1', 0)
            risk_reward = signal.get('risk_reward_ratio', 0)  # Corretto: risk_reward_ratio
            position_size = signal.get('position_size_percent', 0)  # Corretto: position_size_percent
            reasoning = signal.get('reasoning', '')
            
            # Debug per trovare il simbolo
            print(f"🔍 Debug simbolo: {symbol}")
            if symbol == 'N/A':
                print(f"⚠️ Simbolo mancante nel segnale! Chiavi disponibili: {list(signal.keys())}")
                # Il simbolo potrebbe essere nella struttura parent, proviamo a recuperarlo
            
            action_emoji = "🚀" if action == "BUY" else "📉"
            confidence_emoji = "🔥" if confidence >= 80 else "⚡" if confidence >= 70 else "💡"
            
            message = f"""🤖 **SEGNALE AI AUTOMATICO** {action_emoji}

**{symbol}** - {action}
{confidence_emoji} Confidenza: {confidence}%

💰 **Entry:** ${entry:.4f}
🛡️ **Stop Loss:** ${stop_loss:.4f}
🎯 **Take Profit 1:** ${take_profit_1:.4f}
📊 **Risk/Reward:** {risk_reward:.1f}:1
📈 **Position Size:** {position_size}%

🧠 **Analisi AI:**
{reasoning[:200]}{'...' if len(reasoning) > 200 else ''}

⏰ {datetime.now().strftime('%H:%M:%S')}"""
            
            ai_telegram_notifier.send_message_sync(message)
            print(f"📤 Segnale AI inviato per {symbol}")
        else:
            print("⚠️ Telegram notifier non configurato per AI")
            
    except Exception as e:
        print(f"❌ Errore invio Telegram AI: {e}")

@ai_trading_bp.route('/api/auto/status', methods=['GET'])
def get_ai_auto_status():
    """Stato del sistema automatico AI"""
    global ai_auto_analysis_active, ai_auto_config
    
    return jsonify({
        'success': True,
        'active': ai_auto_analysis_active,
        'config': ai_auto_config,
        'timestamp': datetime.now().isoformat()
    })

@ai_trading_bp.route('/api/auto/config', methods=['POST'])
def update_ai_auto_config():
    """Aggiorna configurazione sistema automatico AI"""
    global ai_auto_config
    
    try:
        data = request.get_json()
        
        # Aggiorna configurazione
        if 'analysis_interval' in data:
            ai_auto_config['analysis_interval'] = max(5, int(data['analysis_interval']))
        if 'signal_interval' in data:
            ai_auto_config['signal_interval'] = max(10, int(data['signal_interval']))
        if 'telegram_enabled' in data:
            ai_auto_config['telegram_enabled'] = bool(data['telegram_enabled'])
        if 'min_confidence' in data:
            ai_auto_config['min_confidence'] = max(50, min(95, int(data['min_confidence'])))
        if 'max_signals_per_hour' in data:
            ai_auto_config['max_signals_per_hour'] = max(1, min(10, int(data['max_signals_per_hour'])))
        
        print(f"⚙️ Configurazione AI automatico aggiornata: {ai_auto_config}")
        
        return jsonify({
            'success': True,
            'config': ai_auto_config
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/auto/start', methods=['POST'])
def start_ai_auto_analysis():
    """Avvia sistema automatico AI"""
    global ai_auto_analysis_thread, ai_auto_analysis_active, ai_enhanced_analyzer
    
    try:
        if not ai_enhanced_analyzer or not ai_enhanced_analyzer.ai_enabled:
            return jsonify({'success': False, 'error': 'AI Trading non disponibile'})
        
        if ai_auto_analysis_active:
            return jsonify({'success': False, 'error': 'Sistema automatico AI già attivo'})
        
        ai_auto_analysis_active = True
        ai_auto_analysis_thread = threading.Thread(target=ai_auto_analysis_loop, daemon=True)
        ai_auto_analysis_thread.start()
        
        print("🚀 Sistema automatico AI avviato!")
        
        return jsonify({
            'success': True,
            'message': 'Sistema automatico AI avviato',
            'config': ai_auto_config
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@ai_trading_bp.route('/api/auto/stop', methods=['POST'])
def stop_ai_auto_analysis():
    """Ferma sistema automatico AI"""
    global ai_auto_analysis_active
    
    try:
        ai_auto_analysis_active = False
        print("⏹️ Sistema automatico AI fermato!")
        
        return jsonify({
            'success': True,
            'message': 'Sistema automatico AI fermato'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
