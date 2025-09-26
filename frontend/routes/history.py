from flask import Blueprint, request, jsonify, current_app, render_template
from core.trading_functions import vedi_prezzo_moneta

history_bp = Blueprint('history', __name__)

@history_bp.route('/')
def history():
    """Dashboard principale per la cronologia"""
    return render_template('history.html')

@history_bp.route('/sessions')
def get_session_history():
    """Ottieni storico delle sessioni di trading"""
    try:
        trading_db = current_app.config['TRADING_DB']
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 50, type=int)

        sessions = trading_db.get_session_history(limit)

        return jsonify({
            'success': True,
            'sessions': sessions,
            'total': len(sessions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@history_bp.route('/trades')
def get_trade_history():
    """Ottieni storico dei trade con PnL calcolato in tempo reale"""
    try:
        trading_db = current_app.config['TRADING_DB']
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', 100, type=int)
        
        if session_id:
            trades = trading_db.get_trade_history(session_id=session_id, limit=limit)
        else:
            trades = trading_db.get_trade_history(limit=limit)
        
        # Calcola PnL in tempo reale per trade aperti
        for trade in trades:
            if trade.get('status') == 'OPEN' and trade.get('entry_price') and trade.get('symbol'):
                try:
                    current_price = vedi_prezzo_moneta('linear', trade['symbol'])
                    if current_price and trade['entry_price']:
                        quantity = trade.get('quantity', 0)
                        entry_price = trade['entry_price']
                        
                        if trade.get('side') == 'BUY':
                            trade['current_pnl'] = (current_price - entry_price) * quantity
                        else:
                            trade['current_pnl'] = (entry_price - current_price) * quantity
                        
                        trade['current_price'] = current_price
                        trade['pnl_percentage'] = ((current_price - entry_price) / entry_price) * 100 if trade.get('side') == 'BUY' else ((entry_price - current_price) / entry_price) * 100
                except Exception as e:
                    print(f"Errore calcolo PnL per {trade.get('trade_id')}: {e}")
                    trade['current_pnl'] = 0
                    trade['current_price'] = trade.get('entry_price', 0)
        
        return jsonify({
            'success': True, 
            'data': trades,
            'trades': trades if not session_id else None,
            'total': len(trades)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@history_bp.route('/performance')
def get_performance_data():
    """Ottieni dati di performance per grafici"""
    try:
        trading_db = current_app.config['TRADING_DB']
        days = request.args.get('days', 30, type=int)
        
        performance = trading_db.get_performance_stats(days)
        
        return jsonify({
            'success': True,
            'data': performance,
            'performance': performance
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@history_bp.route('/daily-performance')
def get_daily_performance():
    """Ottieni performance giornaliera"""
    try:
        trading_db = current_app.config['TRADING_DB']
        days = request.args.get('days', 30, type=int)
        daily_data = trading_db.get_daily_performance(days)
        return jsonify({'success': True, 'data': daily_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@history_bp.route('/events')
def get_recent_events():
    """Ottieni eventi recenti"""
    try:
        trading_db = current_app.config['TRADING_DB']
        limit = request.args.get('limit', 50, type=int)
        events = trading_db.get_recent_events(limit)
        return jsonify({'success': True, 'data': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@history_bp.route('/analytics')
def get_trading_analytics():
    """Ottieni analytics completi del trading"""
    try:
        trading_db = current_app.config['TRADING_DB']
        days = request.args.get('days', 30, type=int)
        
        # Combina varie statistiche per analytics
        performance = trading_db.get_performance_stats(days)
        daily_perf = trading_db.get_daily_performance(days)
        recent_trades = trading_db.get_trade_history(limit=10)
        
        analytics = {
            'performance': performance,
            'daily_performance': daily_perf,
            'recent_trades': recent_trades,
            'total_sessions': len(trading_db.get_session_history(limit=1000))
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})