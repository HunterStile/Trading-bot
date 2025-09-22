from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import sys
import os

# Aggiungi path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from ai_enhanced_analysis import AIEnhancedMarketAnalysis
    from ai_trading_assistant import AITradingAssistant
except ImportError:
    AIEnhancedMarketAnalysis = None
    AITradingAssistant = None

ai_trading_bp = Blueprint('ai_trading', __name__, url_prefix='/ai-trading')

# Variabile globale per l'AI assistant
ai_enhanced_analyzer = None

def initialize_ai_trading(market_analyzer, api_key=None, provider='gemini'):
    """Inizializza AI Trading Assistant con Market Analyzer esistente"""
    global ai_enhanced_analyzer
    
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
        
        # Ottieni market analyzer dall'app
        market_analyzer = current_app.config.get('MARKET_ANALYZER')
        
        if not market_analyzer:
            return jsonify({'success': False, 'error': 'Market Analyzer non disponibile'})
        
        # Inizializza AI
        success = initialize_ai_trading(market_analyzer, api_key, provider)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'AI Trading configurato con successo usando {provider.upper()}',
                'ai_enabled': True,
                'provider': provider
            })
        else:
            return jsonify({'success': False, 'error': 'Errore configurazione AI'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
