from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from pybit.unified_trading import HTTP
from core.trading_functions import mostra_saldo, vedi_prezzo_moneta, get_kline_data, analizza_prezzo_sopra_media
from core.config import api, api_sec

api_bp = Blueprint('api', __name__)

@api_bp.route('/balance')
def get_balance():
    """Ottieni il saldo del wallet"""
    try:
        session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
        response = session.get_wallet_balance(accountType="UNIFIED")
        
        if response and 'result' in response:
            balance_data = response['result']['list'][0]
            return jsonify({
                'success': True,
                'data': {
                    'total_equity': float(balance_data.get('totalEquity', 0)),
                    'total_wallet_balance': float(balance_data.get('totalWalletBalance', 0)),
                    'total_margin_balance': float(balance_data.get('totalMarginBalance', 0)),
                    'total_available_balance': float(balance_data.get('totalAvailableBalance', 0))
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/price/<symbol>')
def get_price(symbol):
    """Ottieni il prezzo di un simbolo"""
    try:
        price = vedi_prezzo_moneta('linear', symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'price': price,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/market-data/<symbol>')
def get_market_data(symbol):
    """Ottieni dati di mercato per un simbolo"""
    try:
        # Ottieni dati delle candele
        kline_data = get_kline_data('linear', symbol, '30', 50)
        
        if kline_data:
            # Prepara i dati per il grafico
            chart_data = []
            for candle in reversed(kline_data):
                chart_data.append({
                    'timestamp': int(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            # Analisi EMA
            analysis = analizza_prezzo_sopra_media('linear', symbol, '30', 10)
            
            return jsonify({
                'success': True,
                'symbol': symbol,
                'chart_data': chart_data[-20:],  # Ultimi 20 punti
                'analysis': {
                    'above_ema': analysis[0],
                    'percentage_diff': analysis[1],
                    'current_price': analysis[2]
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/test-connection')
def test_connection():
    """Testa la connessione alle API"""
    try:
        session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
        
        # Test con una richiesta semplice
        response = session.get_server_time()
        
        if response:
            return jsonify({
                'success': True,
                'message': 'Connessione API Bybit riuscita',
                'server_time': response.get('time', 0)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/config/save', methods=['POST'])
def save_bot_config():
    """Salva configurazione bot"""
    try:
        trading_db = current_app.config['TRADING_DB']
        data = request.get_json()
        config_name = data.get('name', f"Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        config_data = data.get('config', {})
        set_active = data.get('set_active', False)
        
        trading_db.save_bot_config(config_name, config_data, set_active)
        return jsonify({'success': True, 'message': 'Configurazione salvata'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/config/list')
def get_bot_configs():
    """Ottieni configurazioni salvate"""
    try:
        trading_db = current_app.config['TRADING_DB']
        configs = trading_db.get_bot_configs()
        return jsonify({'success': True, 'data': configs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/export/data')
def export_trading_data():
    """Esporta dati di trading"""
    try:
        trading_db = current_app.config['TRADING_DB']
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        export_filename = f"trading_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = os.path.join(os.path.dirname(__file__), '..', 'exports', export_filename)
        
        # Crea cartella exports se non esiste
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        
        trading_db.export_data(export_path, start_date, end_date)
        
        return jsonify({
            'success': True, 
            'message': 'Dati esportati con successo',
            'filename': export_filename,
            'path': export_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})