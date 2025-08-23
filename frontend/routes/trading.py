from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from pybit.unified_trading import HTTP
from trading_functions import vedi_prezzo_moneta, mostra_saldo
from config import api, api_sec

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/open-position', methods=['POST'])
def api_open_position():
    """API per aprire una posizione manualmente"""
    try:
        trading_wrapper = current_app.config['TRADING_WRAPPER']
        trading_db = current_app.config['TRADING_DB']
        bot_status = current_app.config['BOT_STATUS']
        
        data = request.get_json()
        
        symbol = data.get('symbol', 'AVAXUSDT')
        side = data.get('side', 'Buy')  # 'Buy' o 'Sell'
        quantity = data.get('quantity', 10)
        price = data.get('price')  # None per market order
        
        # Assicurati che ci sia una sessione attiva
        if not bot_status.get('current_session_id'):
            # Crea una sessione manuale
            strategy_config = {
                'symbol': symbol,
                'mode': 'MANUAL',
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                balance_response = mostra_saldo()
                initial_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except:
                initial_balance = 0
            
            session_id = trading_db.start_session(symbol, strategy_config, initial_balance)
            bot_status['current_session_id'] = session_id
            trading_wrapper.set_session(session_id)
        
        # Apri posizione usando il wrapper
        result = trading_wrapper.open_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            strategy_signal='MANUAL_API'
        )
        
        if result['success']:
            bot_status['total_trades'] += 1
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore apertura posizione: {str(e)}'
        })

@trading_bp.route('/close-position', methods=['POST'])
def api_close_position():
    """API per chiudere una posizione"""
    try:
        trading_wrapper = current_app.config['TRADING_WRAPPER']
        trading_db = current_app.config['TRADING_DB']
        
        data = request.get_json()
        
        trade_id = data.get('trade_id')
        symbol = data.get('symbol')
        side = data.get('side')
        price = data.get('price')  # None per market price
        reason = data.get('reason', 'MANUAL_CLOSE')
        
        # Se non abbiamo trade_id ma abbiamo symbol e side, prova a trovarlo
        if not trade_id and symbol and side:
            active_trades = trading_wrapper.get_active_trades()
            for tid, trade_info in active_trades.items():
                if (trade_info.get('symbol') == symbol and 
                    trade_info.get('side') == side):
                    trade_id = tid
                    break
        
        # Se ancora non abbiamo trade_id, prova a cercare nel database
        if not trade_id and symbol and side:
            try:
                if trading_wrapper.current_session_id:
                    trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
                    open_trades = [t for t in trades if t['status'] == 'OPEN' 
                                 and t['symbol'] == symbol and t['side'] == side]
                    if open_trades:
                        trade_id = open_trades[0]['trade_id']
            except Exception as e:
                print(f"Errore ricerca trade nel database: {e}")
        
        if not trade_id:
            return jsonify({
                'success': False,
                'error': f'Trade non trovato per {symbol} {side}. Verifica che ci sia una posizione aperta.'
            })
        
        result = trading_wrapper.close_position(
            trade_id=trade_id,
            price=price,
            reason=reason
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore chiusura posizione: {str(e)}'
        })

@trading_bp.route('/active-trades')
def get_active_trades():
    """Ottieni trade attualmente attivi"""
    try:
        trading_wrapper = current_app.config['TRADING_WRAPPER']
        active_trades = trading_wrapper.get_active_trades()
        return jsonify({
            'success': True,
            'data': active_trades
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@trading_bp.route('/positions')
def get_bybit_positions():
    """Ottiene le posizioni attive direttamente da Bybit con PnL"""
    try:
        session = HTTP(
            testnet=False,
            api_key=api,
            api_secret=api_sec,
        )
        
        debug_info = {
            'linear_positions': [],
            'inverse_positions': [],
            'option_positions': []
        }
        
        # Test categoria linear con varie settle coins
        settle_coins = ['USDT', 'BTC', 'ETH']
        for coin in settle_coins:
            try:
                linear_response = session.get_positions(category="linear", settleCoin=coin)
                debug_info[f'linear_{coin.lower()}_response'] = linear_response
                if linear_response['retCode'] == 0:
                    debug_info['linear_positions'].extend(linear_response['result']['list'])
            except Exception as e:
                debug_info[f'linear_{coin.lower()}_exception'] = str(e)
        
        # Test categoria inverse
        try:
            inverse_response = session.get_positions(category="inverse")
            debug_info['inverse_response'] = inverse_response
            if inverse_response['retCode'] == 0:
                debug_info['inverse_positions'] = inverse_response['result']['list']
        except Exception as e:
            debug_info['inverse_exception'] = str(e)
        
        # Test categoria option
        try:
            option_response = session.get_positions(category="option")
            debug_info['option_response'] = option_response
            if option_response['retCode'] == 0:
                debug_info['option_positions'] = option_response['result']['list']
        except Exception as e:
            debug_info['option_exception'] = str(e)
        
        # Combina tutte le posizioni attive
        active_positions = []
        all_positions = (debug_info.get('linear_positions', []) + 
                        debug_info.get('inverse_positions', []) + 
                        debug_info.get('option_positions', []))
        
        for position in all_positions:
            # Filtra solo posizioni con size > 0
            if float(position.get('size', 0)) > 0:
                try:
                    current_price = float(vedi_prezzo_moneta('linear', position['symbol']))
                    entry_price = float(position.get('avgPrice', 0)) if position.get('avgPrice') else 0
                    size = float(position['size'])
                    
                    # Calcola PnL
                    unrealized_pnl = float(position.get('unrealisedPnl', 0))
                    pnl_percentage = (unrealized_pnl / (entry_price * size)) * 100 if entry_price > 0 and size > 0 else 0
                    
                    active_positions.append({
                        'symbol': position['symbol'],
                        'side': position.get('side', 'Unknown'),
                        'size': size,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_percentage': round(pnl_percentage, 2),
                        'leverage': position.get('leverage', 'N/A'),
                        'created_time': position.get('createdTime', 'N/A'),
                        'category': position.get('category', 'linear')
                    })
                except Exception as e:
                    print(f"Errore nel processing della posizione {position.get('symbol', 'Unknown')}: {e}")
        
        return jsonify({
            'success': True,
            'positions': active_positions,
            'total_positions': len(active_positions),
            'debug_info': debug_info
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@trading_bp.route('/sync-trades', methods=['POST'])
def sync_trades():
    """Sincronizza trade con il database e Bybit"""
    try:
        trading_wrapper = current_app.config['TRADING_WRAPPER']
        trading_db = current_app.config['TRADING_DB']
        
        # Prima sincronizza con il database
        trading_wrapper.sync_with_database()
        
        # Poi sincronizza con Bybit
        bybit_result = trading_wrapper.sync_with_bybit()
        
        active_trades = trading_wrapper.get_active_trades()
        
        # Verifica trade nel database che il wrapper non conosce
        if trading_wrapper.current_session_id:
            db_trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
            open_db_trades = [t for t in db_trades if t['status'] == 'OPEN']
            
            # Aggiungi trade mancanti al wrapper
            for db_trade in open_db_trades:
                trade_id = db_trade['trade_id']
                if trade_id not in active_trades:
                    trading_wrapper.active_trades[trade_id] = {
                        'symbol': db_trade['symbol'],
                        'side': db_trade['side'],
                        'quantity': db_trade['quantity'],
                        'entry_price': db_trade['entry_price'],
                        'timestamp': db_trade['entry_time']
                    }
        
        active_trades = trading_wrapper.get_active_trades()
        
        return jsonify({
            'success': True,
            'message': f'Sincronizzazione completata: {len(active_trades)} trade attivi',
            'active_trades': len(active_trades),
            'trade_details': active_trades,
            'bybit_sync': bybit_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@trading_bp.route('/debug-trades')
def debug_trades():
    """Debug per verificare tutti i trade"""
    try:
        trading_wrapper = current_app.config['TRADING_WRAPPER']
        trading_db = current_app.config['TRADING_DB']
        
        # Trade nel wrapper
        wrapper_trades = trading_wrapper.get_active_trades()
        
        # Trade nel database
        db_trades = []
        if trading_wrapper.current_session_id:
            all_trades = trading_db.get_trade_history(trading_wrapper.current_session_id, 100)
            db_trades = [t for t in all_trades if t['status'] == 'OPEN']
        
        return jsonify({
            'success': True,
            'current_session_id': trading_wrapper.current_session_id,
            'wrapper_trades_count': len(wrapper_trades),
            'wrapper_trades': wrapper_trades,
            'db_trades_count': len(db_trades),
            'db_trades': db_trades
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })