"""
API Routes per SaaS Frontend Integration
Wrappa le funzioni esistenti del trading bot per l'interfaccia Next.js
"""
from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
import json
import traceback
from datetime import datetime
import logging
import time

# Import delle funzioni core esistenti (NON le tocchiamo!)
try:
    from core.trading_functions import (
        mostra_saldo, vedi_prezzo_moneta, get_kline_data,
        analizza_prezzo_sopra_media, controlla_candele_sopra_ema,
        controlla_candele_sotto_ema, bot_open_position, bot_trailing_stop,
        media_esponenziale
    )
    from core.config import api, api_sec
except ImportError as e:
    print(f"⚠️ Errore import funzioni trading: {e}")

# Import database e wrapper esistenti
try:
    from utils.database import trading_db
    from utils.trading_wrapper import trading_wrapper
except ImportError as e:
    print(f"⚠️ Errore import database/wrapper: {e}")

# Blueprint per le API SaaS
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================
# 🤖 BOT CONTROL ENDPOINTS
# ===========================

@api_bp.route('/bot/status', methods=['GET', 'OPTIONS'])
@cross_origin(origins=["http://localhost:3000"], methods=["GET", "OPTIONS"], allow_headers=["Content-Type"])
def get_bot_status():
    """Ottiene lo status attuale del bot"""
    try:
        # Gestisci richiesta preflight
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'OK'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            return response
            
        # Usa le tue funzioni esistenti per ottenere stato
        saldo = mostra_saldo()  # Funzione esistente
        
        # Simuliamo stato bot (da implementare con i tuoi dati reali)
        status = {
            'running': False,  # Da collegare al tuo bot_state
            'strategy': 'EMA Crossover',
            'symbol': 'BTCUSDT',
            'balance': saldo if saldo else 0,
            'pnl': 0,  # Da calcolare dai tuoi dati
            'trades_today': 0,  # Da database
            'last_update': datetime.now().isoformat()
        }
        
        response = jsonify({
            'success': True,
            'data': status
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        return response
    
    except Exception as e:
        logger.error(f"Errore get_bot_status: {e}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        return response, 500

@api_bp.route('/bot/start', methods=['POST'])
@cross_origin()
def start_bot():
    """Avvia il bot usando le tue funzioni esistenti"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'BTCUSDT')
        strategy = data.get('strategy', 'EMA_CROSSOVER')
        
        # Qui chiamerai le tue funzioni di avvio bot esistenti
        # Per ora simuliamo la risposta
        result = {
            'message': f'Bot avviato su {symbol} con strategia {strategy}',
            'status': 'running',
            'symbol': symbol,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Bot avviato: {result}")
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.error(f"Errore start_bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/bot/stop', methods=['POST'])
@cross_origin()
def stop_bot():
    """Ferma il bot"""
    try:
        # Qui chiamerai le tue funzioni di stop bot esistenti
        result = {
            'message': 'Bot fermato con successo',
            'status': 'stopped',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("Bot fermato")
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.error(f"Errore stop_bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# 📊 MARKET DATA ENDPOINTS  
# ===========================

@api_bp.route('/market/price/<symbol>', methods=['GET'])
@cross_origin()
def get_price(symbol):
    """Ottiene prezzo usando la tua funzione esistente"""
    try:
        # Usa la tua funzione esistente
        price_data = vedi_prezzo_moneta(symbol)
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'price': price_data,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Errore get_price per {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/market/klines/<symbol>', methods=['GET'])
@cross_origin()
def get_klines(symbol):
    """Ottiene dati candele usando la tua funzione esistente"""
    try:
        timeframe = request.args.get('timeframe', '1h')
        limit = int(request.args.get('limit', 100))
        
        # Usa la tua funzione esistente
        klines = get_kline_data(symbol, timeframe, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'timeframe': timeframe,
                'klines': klines,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Errore get_klines per {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# 📈 ANALYSIS ENDPOINTS
# ===========================

@api_bp.route('/analysis/ema/<symbol>', methods=['GET'])
@cross_origin()
def get_ema_analysis(symbol):
    """Analisi EMA usando le tue funzioni esistenti"""
    try:
        timeframe = request.args.get('timeframe', '1h')
        
        # Usa le tue funzioni esistenti
        above_ema = controlla_candele_sopra_ema(symbol, timeframe)
        below_ema = controlla_candele_sotto_ema(symbol, timeframe)
        price_above_avg = analizza_prezzo_sopra_media(symbol, timeframe)
        
        analysis = {
            'symbol': symbol,
            'timeframe': timeframe,
            'above_ema': above_ema,
            'below_ema': below_ema,
            'price_above_average': price_above_avg,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': analysis
        })
    
    except Exception as e:
        logger.error(f"Errore EMA analysis per {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# 🎯 AI CO-TRADING ENDPOINTS
# ===========================

@api_bp.route('/ai/analysis/<symbol>', methods=['GET'])
@cross_origin()
def get_ai_analysis(symbol):
    """AI Analysis - Il tuo sistema di co-trading"""
    try:
        timeframe = request.args.get('timeframe', '1h')
        
        # Qui integrerai il tuo sistema AI di co-trading
        # Per ora simuliamo la risposta strutturata
        ai_analysis = {
            'symbol': symbol,
            'timeframe': timeframe,
            'ai_signal': 'BUY',  # Da tuo sistema AI
            'confidence': 0.85,  # Confidenza AI
            'reasoning': [
                'EMA 9 sopra EMA 21 - Trend rialzista',
                'Volume sopra media - Conferma movimento',
                'RSI in zona neutrale - Spazio per crescita'
            ],
            'human_analysis': 'In attesa di conferma umana',  # Da tua analisi
            'decision': 'PENDING',  # AI + Human decision
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': ai_analysis
        })
    
    except Exception as e:
        logger.error(f"Errore AI analysis per {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/ai/decision', methods=['POST'])
@cross_origin()
def ai_trading_decision():
    """Endpoint per decisioni AI + Human collaboration"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        human_input = data.get('human_decision')  # APPROVE, REJECT, MODIFY
        ai_signal = data.get('ai_signal')
        
        # Qui integrerai la logica di co-trading
        decision = {
            'symbol': symbol,
            'ai_signal': ai_signal,
            'human_input': human_input,
            'final_decision': 'EXECUTE' if human_input == 'APPROVE' else 'HOLD',
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': decision
        })
    
    except Exception as e:
        logger.error(f"Errore AI decision: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# 📋 TRADES & HISTORY
# ===========================

@api_bp.route('/trades/history', methods=['GET'])
@cross_origin()
def get_trades_history():
    """Storico operazioni del bot"""
    try:
        limit = int(request.args.get('limit', 50))
        
        # Qui userai il tuo database/storico esistente
        # Per ora simuliamo alcuni trade
        trades = [
            {
                'id': 1,
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'price': 43250.0,
                'quantity': 0.023,
                'pnl': 145.50,
                'timestamp': '2025-09-26T10:30:00Z',
                'strategy': 'EMA Crossover'
            },
            {
                'id': 2,
                'symbol': 'ETHUSDT', 
                'side': 'SELL',
                'price': 2680.50,
                'quantity': 1.5,
                'pnl': -23.40,
                'timestamp': '2025-09-26T10:25:00Z',
                'strategy': 'AI Co-trading'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'trades': trades,
                'total': len(trades),
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Errore trades history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# 🔔 ALERTS ENDPOINTS
# ===========================

@api_bp.route('/alerts/price', methods=['POST'])
@cross_origin()
def create_price_alert():
    """Crea alert prezzo personalizzato"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        target_price = data.get('target_price')
        alert_type = data.get('type', 'above')  # above, below
        
        # Qui integrerai il tuo sistema di alert esistente
        alert = {
            'id': 'alert_' + str(int(time.time())),
            'symbol': symbol,
            'target_price': target_price,
            'type': alert_type,
            'status': 'active',
            'created': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': alert
        })
    
    except Exception as e:
        logger.error(f"Errore create alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===========================
# ERROR HANDLERS
# ===========================

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500