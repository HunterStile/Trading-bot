"""
User Configuration Routes per Sistema Multi-Tenant
"""
from flask import Blueprint, jsonify, request
import sys
import os

# Aggiungi il percorso per importare user_manager se necessario
try:
    from utils.user_manager import user_manager
except ImportError:
    # Aggiungi il percorso solo se l'import fallisce
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.user_manager import user_manager

user_config_bp = Blueprint('user_config', __name__, url_prefix='/api/user')

def get_user_from_token():
    """Estrae user_id dal JWT token nell'header Authorization"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    result = user_manager.verify_token(token)
    
    if result['success']:
        return result['user_id']
    else:
        return None

@user_config_bp.route('/config', methods=['GET'])
def get_config():
    """Ottieni configurazione utente"""
    try:
        user_id = get_user_from_token()
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Token non valido o scaduto'
            }), 401
        
        # Ottieni configurazione utente
        result = user_manager.get_user_config(user_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        }), 500

@user_config_bp.route('/config', methods=['POST'])
def update_config():
    """Aggiorna configurazione utente"""
    try:
        user_id = get_user_from_token()
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Token non valido o scaduto'
            }), 401
        
        config_data = request.get_json()
        
        # Validazione base
        required_fields = ['bybitApiKey', 'bybitSecretKey', 'telegramBotToken', 'telegramChatId']
        for field in required_fields:
            if field not in config_data:
                return jsonify({
                    'success': False,
                    'error': f'Campo {field} richiesto'
                }), 400
        
        # Converti nomi campi per il backend
        backend_config = {
            'bybit_api_key': config_data.get('bybitApiKey'),
            'bybit_secret_key': config_data.get('bybitSecretKey'),
            'telegram_bot_token': config_data.get('telegramBotToken'),
            'telegram_chat_id': config_data.get('telegramChatId'),
            'trading_strategy': config_data.get('tradingStrategy', 'ema_crossover'),
            'risk_percentage': config_data.get('riskPercentage', 2.0)
        }
        
        # Aggiorna configurazione
        result = user_manager.update_user_config(user_id, backend_config)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        }), 500

@user_config_bp.route('/test-telegram', methods=['POST'])
def test_telegram():
    """Testa configurazione Telegram bot"""
    try:
        user_id = get_user_from_token()
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Token non valido o scaduto'
            }), 401
        
        # Ottieni configurazione utente
        config_result = user_manager.get_user_config(user_id)
        
        if not config_result['success']:
            return jsonify({
                'success': False,
                'error': 'Configurazione non trovata'
            }), 404
        
        config = config_result['config']
        bot_token = config.get('telegram_bot_token')
        chat_id = config.get('telegram_chat_id')
        
        if not bot_token or not chat_id:
            return jsonify({
                'success': False,
                'error': 'Bot token e Chat ID richiesti'
            }), 400
        
        # Testa invio messaggio Telegram
        import requests
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        response = requests.post(telegram_url, json={
            'chat_id': chat_id,
            'text': '🤖 Test configurazione bot Telegram completato con successo!'
        }, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Test Telegram completato con successo!'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Errore invio messaggio Telegram. Verifica token e chat ID.'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore test Telegram: {str(e)}'
        }), 500