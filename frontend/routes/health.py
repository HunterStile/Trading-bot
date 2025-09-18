from flask import Blueprint, jsonify
import datetime
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health():
    """Endpoint di health check semplice"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'service': 'trading-bot'
    })

@health_bp.route('/api/health')
def api_health():
    """Endpoint di health check API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'service': 'trading-bot'
    })

@health_bp.route('/ready')
def ready():
    """Endpoint di readiness check"""
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.datetime.now().isoformat(),
        'service': 'trading-bot'
    })
