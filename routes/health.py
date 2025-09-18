"""
Route per health check del Trading Bot
"""
from flask import Blueprint, jsonify
import os
import sys

health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health')
def health_check():
    """Endpoint per health check Docker"""
    try:
        # Check base
        status = {
            'status': 'healthy',
            'service': 'Trading Bot',
            'version': '1.0.0',
            'timestamp': None
        }
        
        # Check se i moduli principali sono importabili
        try:
            import requests
            import pybit
            status['api_modules'] = 'ok'
        except ImportError as e:
            status['api_modules'] = f'error: {e}'
            status['status'] = 'unhealthy'
        
        # Check file .env
        if os.path.exists('.env'):
            status['config'] = 'ok'
        else:
            status['config'] = 'missing .env'
            status['status'] = 'unhealthy'
        
        # Timestamp
        from datetime import datetime
        status['timestamp'] = datetime.now().isoformat()
        
        return jsonify(status), 200 if status['status'] == 'healthy' else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

@health_bp.route('/health')  
def health_simple():
    """Endpoint semplice per nginx health check"""
    return "OK", 200
