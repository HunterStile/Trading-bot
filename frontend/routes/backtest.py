"""
Route per il backtesting tramite interfaccia web
"""

from flask import Blueprint, request, jsonify, render_template, current_app
import sys
import os
from datetime import datetime
import traceback
import json
from pathlib import Path

# Aggiungi path per import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from simple_backtest import SimpleBacktestEngine
    from advanced_backtest_engine import AdvancedBacktestEngine
except ImportError as e:
    print(f"Import warning: {e}")
    SimpleBacktestEngine = None
    AdvancedBacktestEngine = None

backtest_bp = Blueprint('backtest', __name__)

@backtest_bp.route('/')
def backtest_dashboard():
    """Dashboard principale per il backtesting"""
    return render_template('backtest.html')

@backtest_bp.route('/run', methods=['POST'])
def run_backtest():
    """Esegue un backtest con i parametri forniti"""
    try:
        if not SimpleBacktestEngine:
            return jsonify({
                'success': False,
                'error': 'Simple backtest engine not available'
            }), 500
        
        data = request.get_json()
        
        # Parametri default
        symbol = data.get('symbol', 'BTCUSDT').upper()
        initial_capital = float(data.get('initial_capital', 1000))
        ema_period = int(data.get('ema_period', 10))
        required_candles = int(data.get('required_candles', 3))
        max_distance = float(data.get('max_distance', 1.0))
        timeframe = data.get('timeframe', '30')
        days_back = int(data.get('days_back', 30))
        use_risk_management = data.get('use_risk_management', True)
        operation = data.get('operation', True)  # True = LONG, False = SHORT
        create_chart = data.get('create_chart', True)  # True per creare grafico
        
        # Crea engine
        engine = SimpleBacktestEngine(symbol, initial_capital=initial_capital)
        
        if use_risk_management:
            stop_loss_pct = float(data.get('stop_loss_pct', 2.0))
            take_profit_pct = float(data.get('take_profit_pct', 4.0))
            engine.stop_loss_pct = stop_loss_pct
            engine.take_profit_pct = take_profit_pct
        
        # Esegui backtest
        results = engine.run_backtest(
            ema_period=ema_period,
            required_candles=required_candles,
            max_distance=max_distance,
            timeframe=timeframe,
            days_back=days_back,
            use_risk_management=use_risk_management,
            operation=operation,
            create_chart=create_chart
        )
        
        if results:
            # Salva risultati
            engine.save_results(results)
            
            # Mappa i risultati per compatibilità con il frontend
            results['final_value'] = results.get('final_capital', results.get('initial_capital', 1000))
            results['sharpe_ratio'] = results.get('profit_factor', 0)  # Usa profit factor come proxy
            results['max_drawdown'] = 0  # Il simple engine non calcola drawdown
            
            return jsonify({
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Backtest failed - no data or insufficient data'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@backtest_bp.route('/advanced', methods=['POST'])
def run_advanced_backtest():
    """Esegue un backtest avanzato con le 4 strategie di uscita"""
    try:
        if not AdvancedBacktestEngine:
            return jsonify({
                'success': False,
                'error': 'Advanced backtest engine not available'
            }), 500
        
        data = request.get_json()
        
        # Parametri base
        symbol = data.get('symbol', 'BTCUSDT').upper()
        initial_capital = float(data.get('initial_capital', 1000))
        ema_period = int(data.get('ema_period', 10))
        required_candles = int(data.get('required_candles', 3))
        max_distance = float(data.get('max_distance', 1.0))
        timeframe = data.get('timeframe', '30')
        days_back = int(data.get('days_back', 30))
        operation = data.get('operation', True)  # True = LONG, False = SHORT
        create_chart = data.get('create_chart', True)
        
        # 🆕 Parametri strategie avanzate
        enable_strategies = {
            'enable_multi_timeframe': data.get('enable_multi_timeframe', True),
            'enable_dynamic_trailing': data.get('enable_dynamic_trailing', True),
            'enable_quick_exit': data.get('enable_quick_exit', True),
            'enable_fixed_stop_loss': data.get('enable_fixed_stop_loss', True),
            
            'spike_threshold': float(data.get('spike_threshold', 3.0)),
            'volatile_threshold': float(data.get('volatile_threshold', 5.0)),
            'stop_loss_percent': float(data.get('stop_loss_percent', 3.0)),
            'trailing_stop_percent': float(data.get('trailing_stop_percent', 2.0)),
            'min_distance_for_trailing': float(data.get('min_distance_for_trailing', 2.0)),
            
            'advanced_exit_debug': data.get('advanced_exit_debug', False)
        }
        
        # Crea engine avanzato
        engine = AdvancedBacktestEngine(symbol, initial_capital=initial_capital)
        
        # Esegui backtest avanzato
        results = engine.run_advanced_backtest(
            ema_period=ema_period,
            required_candles=required_candles,
            max_distance=max_distance,
            timeframe=timeframe,
            days_back=days_back,
            operation=operation,
            enable_strategies=enable_strategies,
            create_chart=create_chart
        )
        
        if results:
            # Compatibilità con frontend esistente
            results['final_value'] = results.get('final_capital', results.get('initial_capital', 1000))
            results['sharpe_ratio'] = results.get('profit_factor', 0)
            results['max_drawdown'] = 0  # Da implementare in futuro
            
            return jsonify({
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat(),
                'backtest_type': 'advanced'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Advanced backtest failed - insufficient data or configuration error'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@backtest_bp.route('/optimize', methods=['POST'])
def optimize_parameters():
    """Ottimizza i parametri della strategia"""
    try:
        if not SimpleBacktestEngine:
            return jsonify({
                'success': False,
                'error': 'Simple backtest engine not available'
            }), 500
        
        data = request.get_json()
        
        symbol = data.get('symbol', 'BTCUSDT').upper()
        initial_capital = float(data.get('initial_capital', 1000))
        timeframe = data.get('timeframe', '30')
        days_back = int(data.get('days_back', 30))
        operation = data.get('operation', True)  # True = LONG, False = SHORT
        
        # Parametri da ottimizzare
        ema_periods = data.get('ema_periods', [5, 10, 15, 20])
        candle_counts = data.get('candle_counts', [2, 3, 4, 5])
        distances = data.get('distances', [0.5, 1.0, 1.5, 2.0])
        
        best_result = {'total_return_pct': -999999}
        all_results = []
        
        total_tests = len(ema_periods) * len(candle_counts) * len(distances)
        current_test = 0
        
        for ema in ema_periods:
            for candles in candle_counts:
                for distance in distances:
                    current_test += 1
                    
                    try:
                        engine = SimpleBacktestEngine(symbol, initial_capital=initial_capital)
                        engine.stop_loss_pct = 2.0
                        engine.take_profit_pct = 4.0
                        
                        results = engine.run_backtest(
                            ema_period=ema,
                            required_candles=candles,
                            max_distance=distance,
                            timeframe=timeframe,
                            days_back=days_back,
                            use_risk_management=True,
                            operation=operation
                        )
                        
                        if results:
                            # Aggiungi parametri
                            results['ema_period'] = ema
                            results['required_candles'] = candles
                            results['max_distance'] = distance
                            results['progress'] = current_test / total_tests * 100
                            
                            # Mappa i risultati per compatibilità con il frontend
                            results['final_value'] = results.get('final_capital', results.get('initial_capital', 1000))
                            results['sharpe_ratio'] = results.get('profit_factor', 0)
                            results['max_drawdown'] = 0
                            
                            all_results.append(results)
                            
                            if results['total_return_pct'] > best_result['total_return_pct']:
                                best_result = results
                        
                    except Exception as e:
                        print(f"Error in optimization test: {e}")
        
        # Ordina risultati
        all_results.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        return jsonify({
            'success': True,
            'best_result': best_result,
            'all_results': all_results[:20],  # Top 20 risultati
            'total_tests': total_tests,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@backtest_bp.route('/compare-timeframes', methods=['POST'])
def compare_timeframes():
    """Confronta performance su timeframe diversi"""
    try:
        if not SimpleBacktestEngine:
            return jsonify({
                'success': False,
                'error': 'Simple backtest engine not available'
            }), 500
        
        data = request.get_json()
        
        symbol = data.get('symbol', 'BTCUSDT').upper()
        initial_capital = float(data.get('initial_capital', 1000))
        operation = data.get('operation', True)  # True = LONG, False = SHORT
        timeframes = data.get('timeframes', [
            {'code': '5', 'name': '5 minutes', 'days': 7},
            {'code': '15', 'name': '15 minutes', 'days': 14},
            {'code': '30', 'name': '30 minutes', 'days': 30},
            {'code': '60', 'name': '1 hour', 'days': 60},
            {'code': '240', 'name': '4 hours', 'days': 90},
            {'code': 'D', 'name': '1 day', 'days': 180}
        ])
        
        results = []
        
        for tf in timeframes:
            try:
                engine = SimpleBacktestEngine(symbol, initial_capital=initial_capital)
                engine.stop_loss_pct = 2.0
                engine.take_profit_pct = 4.0
                
                result = engine.run_backtest(
                    ema_period=10,
                    required_candles=3,
                    max_distance=1.0,
                    timeframe=tf['code'],
                    days_back=tf['days'],
                    use_risk_management=True,
                    operation=operation
                )
                
                if result:
                    result['timeframe_name'] = tf['name']
                    result['timeframe_code'] = tf['code']
                    result['days_tested'] = tf['days']
                    
                    # Mappa i risultati per compatibilità con il frontend
                    result['final_value'] = result.get('final_capital', result.get('initial_capital', 1000))
                    result['sharpe_ratio'] = result.get('profit_factor', 0)
                    result['max_drawdown'] = 0
                    
                    results.append(result)
                
            except Exception as e:
                print(f"Error testing timeframe {tf['name']}: {e}")
        
        # Ordina per performance
        results.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@backtest_bp.route('/results')
def get_results():
    """Ottieni lista dei risultati salvati"""
    try:
        results_dir = Path("backtest_results")
        
        if not results_dir.exists():
            return jsonify({
                'success': True,
                'results': []
            })
        
        results = []
        for file_path in results_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Estrai metadati
                file_info = {
                    'filename': file_path.name,
                    'timestamp': data.get('timestamp', ''),
                    'symbol': data.get('symbol', ''),
                    'timeframe': data.get('timeframe', ''),
                    'total_return_pct': data.get('total_return_pct', 0),
                    'total_trades': data.get('total_trades', 0),
                    'win_rate': data.get('win_rate', 0),
                    'profit_factor': data.get('profit_factor', 0),
                    'file_size': file_path.stat().st_size,
                    'created': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                }
                results.append(file_info)
                
            except Exception as e:
                print(f"Error reading backtest result file {file_path}: {e}")
        
        # Ordina per data creazione (più recenti prima)
        results.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@backtest_bp.route('/results/<filename>')
def get_result_detail(filename):
    """Ottieni dettagli di un risultato specifico"""
    try:
        results_dir = Path("backtest_results")
        file_path = results_dir / filename
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'Result file not found'
            }), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@backtest_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_result(filename):
    """Elimina un risultato salvato"""
    try:
        results_dir = Path("backtest_results")
        file_path = results_dir / filename
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'Result file not found'
            }), 404
        
        file_path.unlink()
        
        return jsonify({
            'success': True,
            'message': f'Result {filename} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
