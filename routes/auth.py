"""
Authentication Routes per Sistema Multi-Tenant
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

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login utente e generazione JWT token"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email e password richiesti'
            }), 400
        
        # Autentica l'utente
        result = user_manager.authenticate_user(email, password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        }), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrazione nuovo utente"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email e password richiesti'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'Password deve essere di almeno 6 caratteri'
            }), 400
        
        # Registra l'utente
        result = user_manager.register_user(email, password)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        }), 500

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verifica validità JWT token"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token richiesto'
            }), 400
        
        # Verifica il token
        result = user_manager.verify_token(token)
        return jsonify(result), 200 if result['success'] else 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore interno: {str(e)}'
        }), 500