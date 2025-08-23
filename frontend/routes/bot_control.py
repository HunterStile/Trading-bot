from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import threading
import time
from utils.bot_functions import run_trading_bot

bot_control_bp = Blueprint('bot_control', __name__)

# Variabili globali per il bot
bot_thread = None
stop_bot_flag = False

@bot_control_bp.route('/start', methods=['POST'])
def start_bot():
    """Avvia il bot di trading"""
    global bot_thread, stop_bot_flag
    
    bot_status = current_app.config['BOT_STATUS']
    trading_db = current_app.config['TRADING_DB']
    state_manager = current_app.config['STATE_MANAGER']
    
    if bot_status['running']:
        return jsonify({'success': False, 'error': 'Il bot è già in esecuzione'})
    
    try:
        # Aggiorna i parametri del bot
        data = request.get_json()
        if data:
            bot_status.update(data)
        
        # Salva configurazione bot per recovery
        if state_manager:
            bot_config = {
                'symbol': data.get('symbol'),
                'quantity': data.get('quantity'),
                'operation': data.get('operation'),
                'ema_period': data.get('ema_period'),
                'interval': data.get('interval'),
                'open_candles': data.get('open_candles'),
                'stop_candles': data.get('stop_candles'),
                'distance': data.get('distance'),
                'timestamp': datetime.now().isoformat(),
                'auto_restart': True,
                'was_running': True
            }
            state_manager.save_bot_state('bot_config', bot_config)
            print("💾 Configurazione bot salvata per recovery")
        
        bot_status['running'] = True
        bot_status['last_update'] = datetime.now().isoformat()
        stop_bot_flag = False
        
        # Avvia il bot in un thread separato
        bot_thread = threading.Thread(target=run_trading_bot, args=(bot_status, current_app.config))
        bot_thread.daemon = True
        bot_thread.start()
        
        return jsonify({'success': True, 'message': 'Bot avviato con successo'})
    except Exception as e:
        bot_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/stop', methods=['POST'])
def stop_bot():
    """Ferma il bot di trading"""
    global stop_bot_flag
    
    bot_status = current_app.config['BOT_STATUS']
    trading_db = current_app.config['TRADING_DB']
    state_manager = current_app.config['STATE_MANAGER']
    
    stop_bot_flag = True
    bot_status['running'] = False
    bot_status['last_update'] = datetime.now().isoformat()
    
    # Aggiorna stato nel recovery (bot fermato manualmente)
    if state_manager:
        bot_config = state_manager.get_bot_state('bot_config')
        if bot_config:
            bot_config['was_running'] = False
            bot_config['stopped_manually'] = True
            bot_config['stop_timestamp'] = datetime.now().isoformat()
            state_manager.save_bot_state('bot_config', bot_config)
    
    # Chiudi la sessione corrente se attiva
    if bot_status.get('current_session_id'):
        try:
            from trading_functions import mostra_saldo
            
            # Ottieni saldo finale
            try:
                balance_response = mostra_saldo()
                final_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except Exception as e:
                print(f"Errore mostra_saldo per final_balance: {e}")
                final_balance = 0
                
            trading_db.end_session(bot_status['current_session_id'], final_balance)
            trading_db.log_event(
                "BOT_STOP", 
                "SYSTEM", 
                f"Bot fermato. Sessione {bot_status['current_session_id']} terminata",
                {
                    'total_trades': bot_status['total_trades'],
                    'session_pnl': bot_status['session_pnl'],
                    'final_balance': final_balance
                },
                session_id=bot_status['current_session_id']
            )
            
            # Reset session data
            bot_status['current_session_id'] = None
            bot_status['session_start_time'] = None
            bot_status['total_trades'] = 0
            bot_status['session_pnl'] = 0
            
        except Exception as e:
            print(f"Errore nella chiusura della sessione: {e}")
    
    return jsonify({'success': True, 'message': 'Bot fermato'})

@bot_control_bp.route('/status')
def get_bot_status():
    """Ottieni lo stato del bot"""
    bot_status = current_app.config['BOT_STATUS']
    return jsonify(bot_status)

@bot_control_bp.route('/settings', methods=['POST'])
def update_bot_settings():
    """Aggiorna le impostazioni del bot"""
    bot_status = current_app.config['BOT_STATUS']
    
    try:
        data = request.get_json()
        bot_status.update(data)
        bot_status['last_update'] = datetime.now().isoformat()
        
        return jsonify({'success': True, 'message': 'Impostazioni aggiornate'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/recovery/status')
def get_recovery_status():
    """Ottieni stato del recovery system"""
    try:
        recovery_manager = current_app.config['RECOVERY_MANAGER']
        state_manager = current_app.config['STATE_MANAGER']
        
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        summary = state_manager.get_recovery_summary()
        
        return jsonify({
            'success': True,
            'recovery_summary': summary,
            'recovery_active': recovery_manager.recovery_active
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/recovery/start', methods=['POST'])
def start_recovery():
    """Avvia recovery del bot"""
    try:
        recovery_manager = current_app.config['RECOVERY_MANAGER']
        
        if not recovery_manager:
            return jsonify({'success': False, 'error': 'Recovery system non disponibile'})
        
        result = recovery_manager.perform_initial_recovery()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})