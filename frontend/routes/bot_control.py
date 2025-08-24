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
    state_manager = current_app.config.get('BOT_STATE_MANAGER')
    
    if bot_status['running']:
        return jsonify({'success': False, 'error': 'Il bot è già in esecuzione'})
    
    try:
        # Aggiorna i parametri del bot
        data = request.get_json()
        if data:
            # Gestione robusta per 'operation' (accetta sia string che bool)
            op = data.get('operation', 'true')
            if isinstance(op, bool):
                operation = op
            else:
                operation = str(op).lower() == 'true'
            bot_status.update({
                'symbol': data.get('symbol', 'AVAXUSDT'),
                'quantity': int(data.get('quantity', 50)),
                'operation': operation,
                'ema_period': int(data.get('ema_period', 10)),
                'interval': int(data.get('interval', 30)),
                'open_candles': int(data.get('open_candles', 3)),
                'stop_candles': int(data.get('stop_candles', 3)),
                'distance': float(data.get('distance', 1)),
                'category': 'linear'
            })
        
        bot_status['running'] = True
        bot_status['last_update'] = datetime.now().isoformat()
        stop_bot_flag = False
        
        # ⚠️ NON salvare stato all'avvio se c'è già uno stato di recovery
        # Il recovery system gestirà tutto automaticamente
        if state_manager and not state_manager.should_auto_restart():
            # Salva solo se NON è un auto-restart (nuovo avvio manuale)
            trading_wrapper = current_app.config.get('TRADING_WRAPPER')
            state_manager.save_bot_running_state(bot_status, None, trading_wrapper)
            print("💾 Configurazione bot salvata per recovery (enhanced)")
        else:
            print("🔄 Avvio con recovery esistente - stato non sovrascritto")
        
        # Avvia il bot in un thread separato
        bot_thread = threading.Thread(target=run_trading_bot, args=(bot_status, current_app.config))
        bot_thread.daemon = True
        bot_thread.start()
        
        # ✅ NOTIFICA TELEGRAM: Bot avviato
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            config_for_telegram = {
                'ema_period': bot_status['ema_period'],
                'interval': bot_status['interval'],
                'quantity': bot_status['quantity'],
                'stop_candles': bot_status['stop_candles']
            }
            operation_text = "LONG" if bot_status['operation'] else "SHORT"
            telegram_notifier.notify_bot_started(bot_status['symbol'], operation_text, config_for_telegram)
        
        return jsonify({
            'success': True, 
            'message': 'Bot avviato con successo',
            'config': {
                'symbol': bot_status['symbol'],
                'quantity': bot_status['quantity'],
                'operation': 'LONG' if bot_status['operation'] else 'SHORT',
                'ema_period': bot_status['ema_period'],
                'interval': bot_status['interval'],
                'open_candles': bot_status['open_candles'],
                'stop_candles': bot_status['stop_candles'],
                'distance': bot_status['distance']
            }
        })
    except Exception as e:
        bot_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/stop', methods=['POST'])
def stop_bot():
    """Ferma il bot di trading"""
    global stop_bot_flag
    
    bot_status = current_app.config['BOT_STATUS']
    trading_db = current_app.config['TRADING_DB']
    state_manager = current_app.config.get('BOT_STATE_MANAGER')
    
    stop_bot_flag = True
    bot_status['running'] = False
    bot_status['last_update'] = datetime.now().isoformat()
    
    # Salva stop manuale
    if state_manager:
        state_manager.save_bot_stopped_state()
        print("💾 Bot fermato manualmente - stato salvato")
    
    # 🔧 Chiudi la sessione nel trading wrapper
    trading_wrapper = current_app.config.get('TRADING_WRAPPER')
    if trading_wrapper and trading_wrapper.current_session_id:
        try:
            print(f"🔚 Chiusura sessione wrapper: {trading_wrapper.current_session_id}")
            
            # Ottieni saldo finale
            try:
                from trading_functions import mostra_saldo
                balance_response = mostra_saldo()
                final_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except Exception as e:
                print(f"Errore mostra_saldo per final_balance: {e}")
                final_balance = 0
            
            # Chiudi la sessione del wrapper
            trading_wrapper.end_current_session(final_balance)
            
        except Exception as e:
            print(f"❌ Errore chiusura sessione wrapper: {e}")
    
    # Chiudi la sessione corrente se attiva nel bot_status
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
    
    # ✅ NOTIFICA TELEGRAM: Bot fermato
    telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
    if telegram_notifier:
        telegram_notifier.notify_bot_stopped("Fermato manualmente")
    
    return jsonify({'success': True, 'message': 'Bot fermato'})

@bot_control_bp.route('/status')
def get_bot_status():
    """Ottieni lo stato del bot"""
    bot_status = current_app.config['BOT_STATUS']
    return jsonify(bot_status)

@bot_control_bp.route('/config', methods=['GET'])
def get_bot_config():
    """Ottieni configurazione corrente del bot"""
    try:
        bot_status = current_app.config['BOT_STATUS']
        state_manager = current_app.config.get('BOT_STATE_MANAGER')
        
        # Prova a ottenere config salvata per recovery
        saved_config = None
        can_auto_restart = False
        
        if state_manager:
            if state_manager.should_auto_restart():
                saved_config = state_manager.get_recovery_config()
                can_auto_restart = True
        
        current_config = {
            'symbol': bot_status['symbol'],
            'quantity': bot_status['quantity'],
            'operation': bot_status['operation'],
            'ema_period': bot_status['ema_period'],
            'interval': bot_status['interval'],
            'open_candles': bot_status['open_candles'],
            'stop_candles': bot_status['stop_candles'],
            'distance': bot_status['distance'],
            'running': bot_status['running'],
            'session_id': bot_status.get('current_session_id'),
            'total_trades': bot_status.get('total_trades', 0)
        }
        
        return jsonify({
            'success': True,
            'current_config': current_config,
            'saved_config': saved_config,
            'can_auto_restart': can_auto_restart
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bot_control_bp.route('/clear-recovery', methods=['POST'])
def clear_recovery():
    """Cancella stato di recovery salvato"""
    try:
        state_manager = current_app.config.get('BOT_STATE_MANAGER')
        if state_manager:
            state_manager.clear_state()
            print("💾 Stato di recovery cancellato")
        
        return jsonify({'success': True, 'message': 'Recovery state cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/recovery-status', methods=['GET'])
def get_recovery_status():
    """Ottieni stato del sistema di crash recovery avanzato"""
    try:
        state_manager = current_app.config.get('BOT_STATE_MANAGER')
        
        if not state_manager:
            return jsonify({
                'success': False,
                'error': 'Sistema di crash recovery non disponibile'
            })
        
        # Ottieni il summary dello stato di recovery
        recovery_summary = state_manager.get_recovery_summary()
        
        return jsonify({
            'success': True,
            'summary': recovery_summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore nel controllo recovery: {str(e)}'
        })

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

# RIMOSSE le route recovery che usavano RECOVERY_MANAGER
# Ora usiamo solo BOT_STATE_MANAGER (SimpleBotState)

@bot_control_bp.route('/simple-recovery/status')
def get_simple_recovery_status():
    """Ottieni stato del simple recovery system"""
    try:
        state_manager = current_app.config.get('BOT_STATE_MANAGER')
        
        if not state_manager:
            return jsonify({'success': False, 'error': 'Simple recovery system non disponibile'})
        
        state = state_manager.get_bot_state()
        can_restart = state_manager.should_auto_restart()
        
        return jsonify({
            'success': True,
            'has_saved_state': state is not None,
            'can_auto_restart': can_restart,
            'last_save_time': state.get('last_save_time') if state else None,
            'was_running': state.get('is_running', False) if state else False,
            'stopped_manually': state.get('stopped_manually', False) if state else False
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bot_control_bp.route('/simple-recovery/start', methods=['POST'])
def start_simple_recovery():
    """Avvia recovery usando SimpleBotState"""
    try:
        state_manager = current_app.config.get('BOT_STATE_MANAGER')
        
        if not state_manager:
            return jsonify({'success': False, 'error': 'Simple recovery system non disponibile'})
        
        if not state_manager.should_auto_restart():
            return jsonify({'success': False, 'error': 'Nessun recovery necessario o bot fermato manualmente'})
        
        recovery_config = state_manager.get_recovery_config()
        if not recovery_config:
            return jsonify({'success': False, 'error': 'Configurazione recovery non trovata'})
        
        # Prepara i dati per riavviare il bot
        start_data = {
            'symbol': recovery_config['symbol'],
            'quantity': recovery_config['quantity'],
            'operation': 'true' if recovery_config['operation'] else 'false',
            'ema_period': recovery_config['ema_period'],
            'interval': recovery_config['interval'],
            'open_candles': recovery_config['open_candles'],
            'stop_candles': recovery_config['stop_candles'],
            'distance': recovery_config['distance']
        }
        
        # Simula la chiamata a start_bot
        import json
        from flask import request as mock_request
        
        # Salva la request originale
        original_json = request.get_json
        
        # Mock della request per start_bot
        request.get_json = lambda: start_data
        
        try:
            result = start_bot()
            return result
        finally:
            # Ripristina la request originale
            request.get_json = original_json
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})