"""
Route Flask per il Sistema di Analisi Automatica del Mercato
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime, timedelta
import json

# Import del sistema di analisi
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_analysis import market_analyzer

market_analysis_bp = Blueprint('market_analysis', __name__)

@market_analysis_bp.route('/')
def market_analysis_page():
    """Pagina principale per l'analisi automatica del mercato"""
    return render_template('market_analysis.html')

@market_analysis_bp.route('/api/status', methods=['GET'])
def get_analysis_status():
    """Ottieni stato del sistema di analisi"""
    try:
        status = market_analyzer.get_analysis_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/start', methods=['POST'])
def start_analysis():
    """Avvia il sistema di analisi automatica"""
    try:
        # Imposta il notificatore Telegram se disponibile
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            market_analyzer.set_telegram_notifier(telegram_notifier)
        
        market_analyzer.start_analysis_monitor()
        
        return jsonify({
            'success': True,
            'message': 'Sistema di analisi automatica avviato'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/stop', methods=['POST'])
def stop_analysis():
    """Ferma il sistema di analisi automatica"""
    try:
        market_analyzer.stop_analysis_monitor()
        
        return jsonify({
            'success': True,
            'message': 'Sistema di analisi automatica fermato'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/analyze-now', methods=['POST'])
def analyze_now():
    """Esegui analisi immediata del mercato"""
    try:
        # Imposta il notificatore Telegram se disponibile
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            market_analyzer.set_telegram_notifier(telegram_notifier)
        
        analysis = market_analyzer.analyze_market()
        
        return jsonify({
            'success': True,
            'message': 'Analisi completata',
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/last-analysis', methods=['GET'])
def get_last_analysis():
    """Ottieni l'ultima analisi eseguita"""
    try:
        if not market_analyzer.last_analysis:
            return jsonify({
                'success': False,
                'error': 'Nessuna analisi disponibile'
            })
        
        return jsonify({
            'success': True,
            'analysis': market_analyzer.last_analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/analysis-history', methods=['GET'])
def get_analysis_history():
    """Ottieni cronologia delle analisi"""
    try:
        # Limita il numero di analisi per non sovraccaricare la risposta
        limit = request.args.get('limit', 10, type=int)
        history = market_analyzer.analysis_history[-limit:] if market_analyzer.analysis_history else []
        
        return jsonify({
            'success': True,
            'history': history,
            'total_count': len(market_analyzer.analysis_history)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/config', methods=['GET'])
def get_config():
    """Ottieni configurazione attuale"""
    try:
        return jsonify({
            'success': True,
            'config': market_analyzer.config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/config', methods=['POST'])
def update_config():
    """Aggiorna configurazione del sistema"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dati di configurazione mancanti'
            })
        
        # Validazione campi numerici
        numeric_fields = ['analysis_interval', 'signal_interval', 'rsi_period', 
                         'strength_threshold', 'trend_min_duration']
        
        for field in numeric_fields:
            if field in data:
                try:
                    data[field] = float(data[field])
                    if data[field] <= 0:
                        return jsonify({
                            'success': False,
                            'error': f'{field} deve essere un numero positivo'
                        })
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': f'{field} deve essere un numero valido'
                    })
        
        # Validazione timeframes
        if 'timeframes' in data:
            if not isinstance(data['timeframes'], list):
                return jsonify({
                    'success': False,
                    'error': 'timeframes deve essere una lista'
                })
            
            valid_timeframes = [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440]
            for tf in data['timeframes']:
                if tf not in valid_timeframes:
                    return jsonify({
                        'success': False,
                        'error': f'Timeframe {tf} non valido. Valori supportati: {valid_timeframes}'
                    })
        
        # Validazione EMA periods
        if 'ema_periods' in data:
            if not isinstance(data['ema_periods'], list):
                return jsonify({
                    'success': False,
                    'error': 'ema_periods deve essere una lista'
                })
            
            for period in data['ema_periods']:
                if not isinstance(period, (int, float)) or period <= 0:
                    return jsonify({
                        'success': False,
                        'error': 'Tutti i periodi EMA devono essere numeri positivi'
                    })
        
        # Aggiorna configurazione
        market_analyzer.update_config(data)
        
        # Notifica Telegram se disponibile
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            config_summary = []
            for key, value in data.items():
                config_summary.append(f"• {key}: <code>{value}</code>")
            
            message = f"""
⚙️ <b>Configurazione Analisi Aggiornata</b>

{chr(10).join(config_summary)}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_notifier.send_message_sync(message)
        
        return jsonify({
            'success': True,
            'message': 'Configurazione aggiornata',
            'config': market_analyzer.config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/symbols', methods=['GET'])
def get_analyzed_symbols():
    """Ottieni lista simboli da analizzare"""
    try:
        symbols = market_analyzer.get_symbols_to_analyze()
        
        return jsonify({
            'success': True,
            'symbols': symbols,
            'count': len(symbols)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/symbol/<symbol>', methods=['GET'])
def get_symbol_analysis(symbol):
    """Ottieni analisi specifica per un simbolo"""
    try:
        if not market_analyzer.last_analysis:
            return jsonify({
                'success': False,
                'error': 'Nessuna analisi disponibile'
            })
        
        symbol = symbol.upper()
        analyses = market_analyzer.last_analysis.get('analyses', {})
        
        if symbol not in analyses:
            return jsonify({
                'success': False,
                'error': f'Simbolo {symbol} non trovato nell\'ultima analisi'
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'analysis': analyses[symbol],
            'timestamp': market_analyzer.last_analysis.get('timestamp')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/market-summary', methods=['GET'])
def get_market_summary():
    """Ottieni sommario del mercato dall'ultima analisi"""
    try:
        if not market_analyzer.last_analysis:
            return jsonify({
                'success': False,
                'error': 'Nessuna analisi disponibile'
            })
        
        summary = market_analyzer.last_analysis.get('market_summary', {})
        
        return jsonify({
            'success': True,
            'summary': summary,
            'timestamp': market_analyzer.last_analysis.get('timestamp')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/send-signals', methods=['POST'])
def send_market_signals():
    """Invia segnali di mercato manualmente"""
    try:
        if not market_analyzer.last_analysis:
            return jsonify({
                'success': False,
                'error': 'Nessuna analisi disponibile per inviare segnali'
            })
        
        # Imposta il notificatore Telegram se disponibile
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if not telegram_notifier:
            return jsonify({
                'success': False,
                'error': 'Sistema notifiche Telegram non configurato'
            })
        
        market_analyzer.set_telegram_notifier(telegram_notifier)
        market_analyzer.send_market_signals(market_analyzer.last_analysis)
        
        return jsonify({
            'success': True,
            'message': 'Segnali di mercato inviati'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@market_analysis_bp.route('/api/test-telegram', methods=['POST'])
def test_telegram_analysis():
    """Testa invio notifica Telegram per analisi"""
    try:
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        
        if not telegram_notifier:
            return jsonify({
                'success': False,
                'error': 'Sistema notifiche Telegram non configurato'
            })
        
        # Messaggio di test
        test_message = f"""
🧪 <b>Test Sistema Analisi Automatica</b>

🤖 Il sistema di analisi del mercato è funzionante!
📊 Analisi automatiche e segnali attivi
⏰ {datetime.now().strftime('%H:%M:%S')}

💡 Questo è un messaggio di test dal sistema di analisi automatica.
"""
        
        success = telegram_notifier.send_message_sync(test_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notifica di test analisi inviata con successo!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nell\'invio della notifica'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore: {str(e)}'
        })

@market_analysis_bp.route('/api/performance-report', methods=['GET'])
def get_performance_report():
    """Genera report di performance delle crypto"""
    try:
        if not market_analyzer.last_analysis:
            return jsonify({
                'success': False,
                'error': 'Nessuna analisi disponibile'
            })
        
        analyses = market_analyzer.last_analysis.get('analyses', {})
        
        # Genera report per timeframe 1h
        performance_data = []
        
        for symbol, timeframes in analyses.items():
            if 60 in timeframes:  # Timeframe 1h
                tf_data = timeframes[60]
                
                # Calcola score performance
                score = 0
                
                # Performance prezzo (peso 40%)
                price_change = tf_data['price_change_24h']
                if price_change > 5:
                    score += 40
                elif price_change > 2:
                    score += 30
                elif price_change > -2:
                    score += 20
                elif price_change > -5:
                    score += 10
                else:
                    score += 0
                
                # RSI (peso 20%)
                rsi = tf_data['rsi']
                if 40 <= rsi <= 60:  # RSI neutro
                    score += 20
                elif 30 <= rsi <= 70:  # RSI buono
                    score += 15
                else:  # RSI estremo
                    score += 5
                
                # Trend (peso 30%)
                trend = tf_data['trend']
                if trend['trend'] == 'BULLISH' and trend['strength'] > 3:
                    score += 30
                elif trend['trend'] == 'BULLISH':
                    score += 20
                elif trend['trend'] == 'NEUTRAL':
                    score += 15
                elif trend['trend'] == 'BEARISH':
                    score += 5
                
                # Segnali di inversione (peso 10%)
                if tf_data['reversal_signals']:
                    if any('BULLISH' in signal for signal in tf_data['reversal_signals']):
                        score += 10
                    elif any('BEARISH' in signal for signal in tf_data['reversal_signals']):
                        score += 5
                else:
                    score += 7  # Nessun segnale = stabilità
                
                performance_data.append({
                    'symbol': symbol,
                    'score': score,
                    'price_change': price_change,
                    'rsi': rsi,
                    'trend': trend['trend'],
                    'trend_strength': trend['strength'],
                    'reversal_signals': tf_data['reversal_signals'],
                    'strength_vs_btc': tf_data.get('strength_vs_btc', {})
                })
        
        # Ordina per score
        performance_data.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'success': True,
            'report': performance_data,
            'timestamp': market_analyzer.last_analysis.get('timestamp'),
            'total_symbols': len(performance_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Funzione per inizializzare il sistema di analisi mercato
def init_market_analysis_routes(app, telegram_notifier=None):
    """Inizializza le route per l'analisi del mercato"""
    
    # Imposta il notificatore Telegram se disponibile
    if telegram_notifier:
        market_analyzer.set_telegram_notifier(telegram_notifier)
    
    print("🤖 Route Analisi Mercato inizializzate")
    return market_analysis_bp
