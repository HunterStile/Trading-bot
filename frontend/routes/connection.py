"""
Route per il monitoraggio della connessione
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime

connection_bp = Blueprint('connection', __name__)

@connection_bp.route('/status')
def connection_status():
    """Restituisce lo stato della connessione internet"""
    try:
        monitor = current_app.config.get('CONNECTION_MONITOR')
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor di connessione non disponibile'
            }), 500
        
        status = monitor.get_status()
        return jsonify({
            'success': True,
            'connection_status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/check')
def force_connection_check():
    """Forza un controllo immediato della connessione"""
    try:
        monitor = current_app.config.get('CONNECTION_MONITOR')
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor di connessione non disponibile'
            }), 500
        
        check_result = monitor.force_check()
        return jsonify({
            'success': True,
            'check_result': check_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/toggle-monitoring', methods=['POST'])
def toggle_monitoring():
    """Avvia o ferma il monitoraggio della connessione"""
    try:
        monitor = current_app.config.get('CONNECTION_MONITOR')
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor di connessione non disponibile'
            }), 500
        
        if monitor.is_monitoring:
            monitor.stop_monitoring()
            action = 'stopped'
        else:
            monitor.start_monitoring()
            action = 'started'
        
        return jsonify({
            'success': True,
            'action': action,
            'is_monitoring': monitor.is_monitoring
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
