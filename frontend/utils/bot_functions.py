import time
from datetime import datetime
from core.trading_functions import (
    vedi_prezzo_moneta, get_kline_data, analizza_prezzo_sopra_media, 
    controlla_candele_sopra_ema, controlla_candele_sotto_ema, 
    media_esponenziale, mostra_saldo
)
from .crash_recovery import create_crash_recovery_system
from .advanced_exit_strategies import (
    create_advanced_exit_manager, analyze_advanced_exit_conditions
)

def run_trading_bot(bot_status, app_config):
    """Esegue il bot di trading con crash recovery e state management avanzato"""
    trading_wrapper = app_config['TRADING_WRAPPER']
    trading_db = app_config['TRADING_DB']
    socketio = app_config['SOCKETIO']
    state_manager = app_config.get('BOT_STATE_MANAGER')
    
    # Contatore per salvataggio periodico dello stato
    state_save_counter = 0
    
    # Variabili per gestione fasi operative
    operational_phase = 'SEEKING_ENTRY'  # Default: cerca entry
    
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Avvio bot di trading...")
        
        # 🆕 CRASH RECOVERY: Controlla se è necessario recovery
        if state_manager:
            operational_phase = perform_crash_recovery(bot_status, app_config, state_manager)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Fase operativa: {operational_phase}")
        
        # ✅ CORREZIONE: Aggiorna bot_status con la fase operativa corretta dal recovery
        bot_status['operational_phase'] = operational_phase
        
        # Salva stato iniziale aggiornato SOLO se non abbiamo fatto recovery
        # Il recovery ha già salvato lo stato corretto, non sovrascrivere
        if state_manager and operational_phase != 'MANAGING_POSITIONS':
            active_trades = trading_wrapper.get_active_trades() if trading_wrapper else {}
            state_manager.save_bot_running_state(bot_status, active_trades, trading_wrapper)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Stato iniziale salvato")
        elif operational_phase == 'MANAGING_POSITIONS':
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Recovery attivo - mantenendo stato di recovery")
        
        # Gestione sessione di trading  
        # 🆕 Se abbiamo appena fatto recovery e abbiamo posizioni attive,
        # NON creare una nuova sessione che sovrascrive lo stato di recovery
        if operational_phase not in ['MANAGING_POSITIONS', 'IN_POSITION_LONG', 'IN_POSITION_SHORT']:
            setup_trading_session(bot_status, trading_wrapper, trading_db, state_manager)
        else:
            # Recovery completato con posizioni attive - continua sessione esistente
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Recovery con posizioni attive - continuando sessione esistente")
            
            # 🔍 DEBUG CRITICO: Verifica session_id nel bot_status
            current_session = bot_status.get('current_session_id')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: session_id nel bot_status: '{current_session}'")
            
            if current_session:
                trading_wrapper.set_session(current_session)
                trading_wrapper.sync_with_database()
                
                # 🆕 IMPORTANTE: Sincronizza anche con Bybit per recuperare posizioni
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Sincronizzazione posizioni per recovery...")
                sync_result = trading_wrapper.sync_with_bybit()
                if sync_result['success']:
                    active_count = len(trading_wrapper.get_active_trades())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Sincronizzazione completata: {active_count} posizioni attive")
                    
                    # ✅ IMPORTANTE: Aggiorna bot_status con il numero reale di posizioni  
                    if active_count > 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Posizioni trovate durante recovery - continuo monitoraggio")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Recovery senza posizioni - possibile desync")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore sincronizzazione Bybit: {sync_result.get('error')}")
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Continuando sessione di recovery: {current_session}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Recovery senza session_id - creando sessione temporanea")
                # Fallback: crea sessione temporanea per recovery 
                setup_trading_session(bot_status, trading_wrapper, trading_db, state_manager)        # Loop principale del bot
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Avvio ciclo di trading...")
        
        while bot_status['running']:
            try:
                # Analisi di mercato
                market_data = perform_market_analysis(bot_status)
                
                if market_data:
                    # Esegui strategia di trading
                    execute_trading_strategy(
                        bot_status, market_data, 
                        trading_wrapper, trading_db, socketio, state_manager
                    )
                    
                    # Emetti aggiornamenti WebSocket
                    emit_bot_updates(bot_status, market_data, trading_wrapper, socketio)
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Dati di mercato non disponibili")
                
                # Salvataggio periodico stato (ogni 6 cicli = 1 minuto)
                state_save_counter += 1
                if state_manager and state_save_counter >= 6:
                    # ✅ CORREZIONE: Passa anche trading_wrapper per ottenere posizioni attive
                    active_trades = trading_wrapper.get_active_trades() if trading_wrapper else {}
                    state_manager.save_bot_running_state(bot_status, active_trades, trading_wrapper)
                    state_save_counter = 0
                
                time.sleep(10)
                
            except Exception as loop_error:
                handle_loop_error(loop_error, bot_status, trading_db, socketio)
                time.sleep(5)  # Pausa più breve in caso di errore
    
    except Exception as critical_error:
        handle_critical_error(critical_error, bot_status, trading_db, socketio, state_manager)
    
    finally:
        cleanup_bot_session(bot_status, state_manager)

def setup_trading_session(bot_status, trading_wrapper, trading_db, state_manager):
    """Configura la sessione di trading"""
    if bot_status['current_session_id']:
        # Continua sessione esistente
        trading_wrapper.set_session(bot_status['current_session_id'])
        trading_wrapper.sync_with_database()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Sessione esistente: {bot_status['current_session_id']}")
    else:
        # Crea nuova sessione
        strategy_config = extract_strategy_config(bot_status)
        
        # Ottieni saldo iniziale
        initial_balance = get_initial_balance()
        
        # Avvia nuova sessione
        bot_status['current_session_id'] = trading_db.start_session(
            bot_status['symbol'], 
            strategy_config, 
            initial_balance
        )
        
        bot_status['session_start_time'] = datetime.now().isoformat()
        bot_status['total_trades'] = 0
        bot_status['session_pnl'] = 0
        
        # Configura wrapper
        trading_wrapper.set_session(bot_status['current_session_id'])
        trading_wrapper.sync_with_database()
        
        # Log evento di avvio
        trading_db.log_event(
            "BOT_START", 
            "SYSTEM", 
            f"Bot avviato per {bot_status['symbol']}", 
            strategy_config,
            session_id=bot_status['current_session_id']
        )
        
        # Aggiorna stato con session_id
        if state_manager:
            state_manager.save_bot_running_state(bot_status)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Nuova sessione creata: {bot_status['current_session_id']}")

def extract_strategy_config(bot_status):
    """Estrae configurazione strategia da bot_status"""
    return {
        'symbol': bot_status['symbol'],
        'ema_period': bot_status['ema_period'],
        'interval': bot_status['interval'],
        'open_candles': bot_status['open_candles'],
        'stop_candles': bot_status['stop_candles'],
        'distance': bot_status['distance'],
        'quantity': bot_status['quantity'],
        'operation': bot_status['operation']
    }

def get_initial_balance():
    """Ottieni saldo iniziale sicuro"""
    try:
        balance_response = mostra_saldo()
        return balance_response.get('total_equity', 0) if balance_response else 0
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore saldo iniziale: {e}")
        return 0

def perform_market_analysis(bot_status):
    """Analisi mercato con correzioni ordine candele"""
    try:
        symbol = bot_status['symbol']
        
        # Ottieni prezzo corrente
        current_price = vedi_prezzo_moneta('linear', symbol)
        if not current_price:
            return None
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Analizzando {symbol} - Prezzo: ${current_price:.6f}")
        
        # Ottieni dati candele
        interval = bot_status['interval']
        klines = get_kline_data('linear', symbol, interval, 200)
        if not klines:
            return None
        
        # Calcola EMA con correzione ordine
        ema_data = calculate_ema_analysis(klines, bot_status, current_price)
        
        # Conta candele consecutive con correzione ordine
        candles_data = count_consecutive_candles(symbol, bot_status)
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'klines': klines,
            'ema_value': ema_data['ema_value'],
            'distance_percent': ema_data['distance_percent'],
            'is_above_ema': ema_data['is_above_ema'],
            'candles_above': candles_data['candles_above'],
            'candles_below': candles_data['candles_below']
        }
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore analisi mercato: {e}")
        return None

def calculate_ema_analysis(klines, bot_status, current_price):
    """Calcola analisi EMA con ordine candele corretto"""
    try:
        symbol = bot_status['symbol']
        ema_period = bot_status['ema_period']
        
        print(f"[DEBUG] Calcolo EMA per {symbol} (Periodo: {ema_period})")
        
        # CORREZIONE: Verifica e corregge l'ordine delle candele
        # Se la prima candela è più recente dell'ultima, inverti l'array
        first_timestamp = int(klines[0][0])
        last_timestamp = int(klines[-1][0])
        
        if first_timestamp > last_timestamp:
            print(f"[DEBUG] ⚠️ Candele in ordine inverso - Correzione in corso...")
            klines = list(reversed(klines))
            print(f"[DEBUG] ✅ Candele corrette - Prima: {datetime.fromtimestamp(int(klines[0][0])/1000).strftime('%H:%M:%S')}, Ultima: {datetime.fromtimestamp(int(klines[-1][0])/1000).strftime('%H:%M:%S')}")
        
        # Estrai prezzi di chiusura (ora in ordine cronologico corretto)
        close_prices = [float(candle[4]) for candle in klines]
        
        # Debug: mostra gli ultimi prezzi
        print(f"[DEBUG] Ultimi 5 prezzi di chiusura: {close_prices[-5:]}")
        print(f"[DEBUG] Prezzo corrente: {current_price}")
        
        # Calcola EMA usando la funzione builtin (più affidabile)
        ema_values = media_esponenziale(close_prices, ema_period)
        
        if not ema_values:
            print(f"[WARNING] Impossibile calcolare EMA - Usando prezzo corrente")
            return {
                'ema_value': current_price,
                'distance_percent': 0,
                'is_above_ema': False
            }
        
        ema_value = ema_values[-1]
        
        # Calcola distanza percentuale
        if ema_value > 0:
            distance_percent = ((current_price - ema_value) / ema_value) * 100
            is_above_ema = distance_percent > 0
        else:
            print(f"[WARNING] EMA non valida: {ema_value}")
            distance_percent = 0
            is_above_ema = False
        
        print(f"[DEBUG] EMA calcolata: {ema_value:.6f}")
        print(f"[DEBUG] Distanza: {distance_percent:+.4f}%")
        print(f"[DEBUG] Sopra EMA: {is_above_ema}")
        
        # Verifica di sanità
        if abs(distance_percent) > 20:
            print(f"[WARNING] ⚠️ Distanza elevata ({distance_percent:.2f}%) - Possibile errore")
        
        return {
            'ema_value': ema_value,
            'distance_percent': distance_percent,
            'is_above_ema': is_above_ema
        }
        
    except Exception as e:
        print(f"[ERROR] Errore calcolo EMA: {e}")
        return {
            'ema_value': current_price,
            'distance_percent': 0,
            'is_above_ema': False
        }

def calculate_ema_manual(prices, period):
    """Calcola EMA manualmente per debug"""
    if len(prices) < period:
        return []
    
    # Calcola la SMA iniziale per i primi 'period' valori
    sma = sum(prices[:period]) / period
    ema_values = [sma]
    
    # Fattore di smoothing
    multiplier = 2 / (period + 1)
    
    # Calcola EMA per i valori rimanenti
    for price in prices[period:]:
        ema = (price * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)
    
    return ema_values

# Funzione aggiuntiva per verificare l'ordine delle candele
def verify_klines_order(klines):
    """Verifica l'ordine cronologico delle candele"""
    print(f"[DEBUG] Verifica ordine candele:")
    print(f"  Prima candela: {datetime.fromtimestamp(int(klines[0][0])/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Ultima candela: {datetime.fromtimestamp(int(klines[-1][0])/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verifica che siano in ordine cronologico crescente
    is_ordered = True
    for i in range(1, len(klines)):
        if int(klines[i][0]) < int(klines[i-1][0]):
            is_ordered = False
            break
    
    print(f"  Ordine cronologico corretto: {'✅' if is_ordered else '❌'}")
    return is_ordered

def count_consecutive_candles(symbol, bot_status):
    """Conta candele consecutive sopra/sotto EMA"""
    try:
        candles_above_result = controlla_candele_sopra_ema('linear', symbol, bot_status['interval'], bot_status['ema_period'])
        candles_below_result = controlla_candele_sotto_ema('linear', symbol, bot_status['interval'], bot_status['ema_period'])
        
        candles_above = candles_above_result[0] if candles_above_result and len(candles_above_result) > 0 else 0
        candles_below = candles_below_result[0] if candles_below_result and len(candles_below_result) > 0 else 0
        
        return {
            'candles_above': candles_above,
            'candles_below': candles_below
        }
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore conteggio candele: {e}")
        return {
            'candles_above': 0,
            'candles_below': 0
        }

def execute_trading_strategy(bot_status, market_data, trading_wrapper, trading_db, socketio, state_manager=None):
    """Esegue la strategia di trading basata sui dati di mercato"""
    try:
        # Log dell'analisi
        log_market_analysis(bot_status, market_data)
        
        # Verifica posizioni attive
        active_trades = trading_wrapper.get_active_trades()
        
        if not active_trades:
            # Nessuna posizione attiva - analizza segnali di entrata
            trade_opened = analyze_entry_signals(bot_status, market_data, trading_wrapper, socketio, state_manager)
            
            # Aggiorna contatore trades se apertura riuscita
            if trade_opened:
                bot_status['total_trades'] = bot_status.get('total_trades', 0) + 1
        else:
            # Posizioni attive - analizza segnali di uscita
            analyze_exit_signals(bot_status, market_data, active_trades, trading_wrapper, socketio, state_manager)
        
        # Salva analisi nel database
        save_market_analysis_to_db(bot_status, market_data, trading_db)
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore esecuzione strategia: {e}")

def log_market_analysis(bot_status, market_data):
    """Log dell'analisi di mercato"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 EMA({bot_status['ema_period']}): ${market_data['ema_value']:.4f}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Prezzo {'SOPRA' if market_data['is_above_ema'] else 'SOTTO'} EMA ({market_data['distance_percent']:+.2f}%)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🕯️ Candele: {market_data['candles_above']} sopra, {market_data['candles_below']} sotto")

def analyze_entry_signals(bot_status, market_data, trading_wrapper, socketio, state_manager=None):
    """Analizza segnali di entrata"""
    distance_ok = abs(market_data['distance_percent']) <= bot_status['distance']
    
    socketio.emit('analysis_log', {
        'message': f"🔍 Nessuna posizione attiva - Analisi condizioni apertura...",
        'type': 'info'
    })
    
    if bot_status['operation']:  # Long
        return check_long_entry_conditions(bot_status, market_data, distance_ok, trading_wrapper, socketio, state_manager)
    else:  # Short
        return check_short_entry_conditions(bot_status, market_data, distance_ok, trading_wrapper, socketio, state_manager)

def check_long_entry_conditions(bot_status, market_data, distance_ok, trading_wrapper, socketio, state_manager=None):
    """Controlla condizioni per apertura LONG"""
    conditions = {
        'above_ema': market_data['is_above_ema'],
        'enough_candles': market_data['candles_above'] >= bot_status['open_candles'],
        'distance_ok': distance_ok
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 LONG - Condizioni apertura:")
    print(f"  Sopra EMA: {'✅' if conditions['above_ema'] else '❌'}")
    print(f"  Candele: {'✅' if conditions['enough_candles'] else '❌'} ({market_data['candles_above']}/{bot_status['open_candles']})")
    print(f"  Distanza: {'✅' if conditions['distance_ok'] else '❌'} ({market_data['distance_percent']:.2f}% <= {bot_status['distance']}%)")
    
    if all(conditions.values()):
        return execute_long_entry(bot_status, market_data, trading_wrapper, socketio, state_manager)
    
    return False

def check_short_entry_conditions(bot_status, market_data, distance_ok, trading_wrapper, socketio, state_manager=None):
    """Controlla condizioni per apertura SHORT"""
    conditions = {
        'below_ema': not market_data['is_above_ema'],
        'enough_candles': market_data['candles_below'] >= bot_status['open_candles'],
        'distance_ok': distance_ok
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 SHORT - Condizioni apertura:")
    print(f"  Sotto EMA: {'✅' if conditions['below_ema'] else '❌'}")
    print(f"  Candele: {'✅' if conditions['enough_candles'] else '❌'} ({market_data['candles_below']}/{bot_status['open_candles']})")
    print(f"  Distanza: {'✅' if conditions['distance_ok'] else '❌'} ({abs(market_data['distance_percent']):.2f}% <= {bot_status['distance']}%)")
    
    if all(conditions.values()):
        return execute_short_entry(bot_status, market_data, trading_wrapper, socketio, state_manager)
    
    return False

def execute_long_entry(bot_status, market_data, trading_wrapper, socketio, state_manager=None):
    """Esegue apertura posizione LONG"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE LONG! Apertura posizione...")
    
    result = trading_wrapper.open_position(
        symbol=market_data['symbol'],
        side='Buy',
        quantity=bot_status['quantity'],
        strategy_signal=f"EMA_LONG_{bot_status['ema_period']}",
        categoria=bot_status['category'],
        periodo_ema=bot_status['ema_period'],
        intervallo=bot_status['interval'],
        candele=bot_status['open_candles'],
        lunghezza=bot_status['distance']
    )
    
    if result['success']:
        # 🆕 Aggiorna e salva lo stato con posizione aperta
        try:
            if state_manager:
                # Aggiorna fase operativa e salva stato
                state_manager.save_state_with_position(bot_status, 'IN_POSITION_LONG', trading_wrapper)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Stato salvato con posizione LONG aperta")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ state_manager non disponibile per salvataggio stato")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore aggiornamento stato: {e}")
        
        socketio.emit('trade_notification', {
            'type': 'POSITION_OPENED',
            'side': 'LONG',
            'symbol': market_data['symbol'],
            'price': market_data['current_price'],
            'quantity': bot_status['quantity'],
            'timestamp': datetime.now().isoformat()
        })
        
        # ✅ NOTIFICA TELEGRAM: Posizione aperta
        try:
            from utils.telegram_notifier import get_telegram_notifier
            telegram_notifier = get_telegram_notifier()
            if telegram_notifier:
                trade_info = {
                    'symbol': market_data['symbol'],
                    'side': 'BUY',
                    'quantity': bot_status['quantity'],
                    'price': market_data['current_price'],
                    'value': bot_status['quantity'] * market_data['current_price'],
                    'trade_id': result.get('trade_id', 'N/A')
                }
                telegram_notifier.notify_position_opened(trade_info)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore notifica Telegram: {e}")
        
        return True
    
    return False

def execute_short_entry(bot_status, market_data, trading_wrapper, socketio, state_manager=None):
    """Esegue apertura posizione SHORT"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE SHORT! Apertura posizione...")
    
    result = trading_wrapper.open_position(
        symbol=market_data['symbol'],
        side='Sell',
        quantity=bot_status['quantity'],
        strategy_signal=f"EMA_SHORT_{bot_status['ema_period']}",
        categoria=bot_status['category'],
        periodo_ema=bot_status['ema_period'],
        intervallo=bot_status['interval'],
        candele=bot_status['open_candles'],
        lunghezza=bot_status['distance']
    )
    
    if result['success']:
        # 🆕 Aggiorna e salva lo stato con posizione aperta
        try:
            if state_manager:
                # Aggiorna fase operativa e salva stato
                state_manager.save_state_with_position(bot_status, 'IN_POSITION_SHORT', trading_wrapper)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Stato salvato con posizione SHORT aperta")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ state_manager non disponibile per salvataggio stato")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore aggiornamento stato: {e}")
        
        socketio.emit('trade_notification', {
            'type': 'POSITION_OPENED',
            'side': 'SHORT',
            'symbol': market_data['symbol'],
            'price': market_data['current_price'],
            'quantity': bot_status['quantity'],
            'timestamp': datetime.now().isoformat()
        })
        
        # ✅ NOTIFICA TELEGRAM: Posizione aperta
        try:
            from utils.telegram_notifier import get_telegram_notifier
            telegram_notifier = get_telegram_notifier()
            if telegram_notifier:
                trade_info = {
                    'symbol': market_data['symbol'],
                    'side': 'SELL',
                    'quantity': bot_status['quantity'],
                    'price': market_data['current_price'],
                    'value': bot_status['quantity'] * market_data['current_price'],
                    'trade_id': result.get('trade_id', 'N/A')
                }
                telegram_notifier.notify_position_opened(trade_info)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore notifica Telegram: {e}")
        
        return True
    
    return False

def analyze_exit_signals(bot_status, market_data, active_trades, trading_wrapper, socketio, state_manager=None):
    """Analizza segnali di uscita per posizioni attive"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Posizioni attive: {len(active_trades)} - Analisi chiusura...")
    
    for trade_id, trade_info in active_trades.items():
        trade_side = trade_info['side']
        trade_symbol = trade_info.get('symbol', bot_status['symbol'])
        
        # ✅ DEBUG: Mostra il side per capire il formato
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DEBUG: Trade {trade_id} - Side: '{trade_side}' - Symbol: {trade_symbol}")
        
        # ✅ CORREZIONE: Normalizza il side per gestire case sensitivity 
        trade_side_normalized = trade_side.upper()
        
        if trade_side_normalized == 'BUY':
            check_long_exit_conditions(bot_status, market_data, trade_id, trade_symbol, trading_wrapper, socketio, state_manager)
        elif trade_side_normalized == 'SELL':
            check_short_exit_conditions(bot_status, market_data, trade_id, trade_symbol, trading_wrapper, socketio, state_manager)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Side non riconosciuto: '{trade_side}' (normalizzato: '{trade_side_normalized}')")

def check_long_exit_conditions(bot_status, market_data, trade_id, trade_symbol, trading_wrapper, socketio, state_manager=None):
    """Controlla condizioni chiusura LONG con strategie avanzate"""
    # Standard exit condition
    standard_exit = market_data['candles_below'] >= bot_status['stop_candles']
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 LONG {trade_symbol} - Candele sotto EMA: {market_data['candles_below']}/{bot_status['stop_candles']}")
    
    # 🆕 ADVANCED EXIT ANALYSIS
    should_close = standard_exit
    close_reason = "EMA_STOP"
    
    # Controlla se le strategie avanzate sono attivate
    advanced_exits_enabled = any([
        bot_status.get('enable_multi_timeframe', False),
        bot_status.get('enable_dynamic_trailing', False),
        bot_status.get('enable_quick_exit', False),
        bot_status.get('enable_fixed_stop_loss', False)
    ])
    
    if advanced_exits_enabled:
        try:
            # Crea manager delle strategie avanzate
            advanced_exit_manager = create_advanced_exit_manager(bot_status)
            
            # Informazioni trade necessarie per analisi avanzata
            # Ottieni entry_price dal trading_wrapper per Fixed Stop Loss
            active_trades = trading_wrapper.get_active_trades()
            trade_data = active_trades.get(trade_id, {})
            entry_price = trade_data.get('entry_price', 0)
            
            trade_info = {
                'side': 'BUY',  # LONG position
                'symbol': trade_symbol,
                'entry_price': entry_price
            }
            
            # Analizza condizioni di uscita avanzate
            advanced_result = analyze_advanced_exit_conditions(
                advanced_exit_manager, trade_id, trade_info, bot_status, market_data
            )
            
            if advanced_result['should_close']:
                should_close = True
                close_reason = f"ADVANCED_EXIT_{advanced_result['exit_type']}"
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 ADVANCED EXIT TRIGGERED!")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Tipo: {advanced_result['exit_type']}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Motivo: {advanced_result['reason']}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Priorità: {advanced_result.get('priority', 'UNKNOWN')}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Strategie avanzate: Nessuna uscita")
                if bot_status.get('advanced_exit_debug', False):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🐛 Advanced Debug: {advanced_result['reason']}")
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore strategie avanzate LONG: {e}")
            # Fallback a logica standard
    
    if should_close:
        execute_position_close(trade_id, 'LONG', trade_symbol, market_data['current_price'], 
                              trading_wrapper, socketio, state_manager, bot_status, close_reason)

def check_short_exit_conditions(bot_status, market_data, trade_id, trade_symbol, trading_wrapper, socketio, state_manager=None):
    """Controlla condizioni chiusura SHORT con strategie avanzate"""
    # Standard exit condition
    standard_exit = market_data['candles_above'] >= bot_status['stop_candles']
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 SHORT {trade_symbol} - Candele sopra EMA: {market_data['candles_above']}/{bot_status['stop_candles']}")
    
    # 🆕 ADVANCED EXIT ANALYSIS
    should_close = standard_exit
    close_reason = "EMA_STOP"
    
    # Controlla se le strategie avanzate sono attivate
    advanced_exits_enabled = any([
        bot_status.get('enable_multi_timeframe', False),
        bot_status.get('enable_dynamic_trailing', False),
        bot_status.get('enable_quick_exit', False),
        bot_status.get('enable_fixed_stop_loss', False)
    ])
    
    if advanced_exits_enabled:
        try:
            # Crea manager delle strategie avanzate
            advanced_exit_manager = create_advanced_exit_manager(bot_status)
            
            # Informazioni trade necessarie per analisi avanzata
            # Ottieni entry_price dal trading_wrapper per Fixed Stop Loss
            active_trades = trading_wrapper.get_active_trades()
            trade_data = active_trades.get(trade_id, {})
            entry_price = trade_data.get('entry_price', 0)
            
            trade_info = {
                'side': 'SELL',  # SHORT position
                'symbol': trade_symbol,
                'entry_price': entry_price
            }
            
            # Analizza condizioni di uscita avanzate
            advanced_result = analyze_advanced_exit_conditions(
                advanced_exit_manager, trade_id, trade_info, bot_status, market_data
            )
            
            if advanced_result['should_close']:
                should_close = True
                close_reason = f"ADVANCED_EXIT_{advanced_result['exit_type']}"
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 ADVANCED EXIT TRIGGERED!")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Tipo: {advanced_result['exit_type']}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Motivo: {advanced_result['reason']}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Priorità: {advanced_result.get('priority', 'UNKNOWN')}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Strategie avanzate: Nessuna uscita")
                if bot_status.get('advanced_exit_debug', False):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🐛 Advanced Debug: {advanced_result['reason']}")
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore strategie avanzate SHORT: {e}")
            # Fallback a logica standard
    
    if should_close:
        execute_position_close(trade_id, 'SHORT', trade_symbol, market_data['current_price'], 
                              trading_wrapper, socketio, state_manager, bot_status, close_reason)

def execute_position_close(trade_id, side, symbol, current_price, trading_wrapper, socketio, state_manager=None, bot_status=None, close_reason="EMA_STOP"):
    """Esegue chiusura posizione"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {'🔻' if side == 'LONG' else '🔺'} SEGNALE CHIUSURA {side}!")
    
    if close_reason != "EMA_STOP":
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Motivo chiusura: {close_reason}")
    
    result = trading_wrapper.close_position(trade_id, current_price, close_reason)
    
    if result['success']:
        # 📱 Invia notifica Telegram per chiusura posizione
        try:
            from .telegram_notifier import get_telegram_notifier
            notifier = get_telegram_notifier()
            if notifier:
                # Ottieni informazioni del trade dal risultato
                profit_loss = result.get('profit_loss', 0)
                profit_pct = result.get('profit_percentage', 0)
                
                notifier.notify_position_closed({
                    'symbol': symbol,
                    'side': side,
                    'close_price': current_price,
                    'timestamp': datetime.now().isoformat()
                }, pnl=profit_loss, reason="EMA_STOP")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore invio notifica Telegram chiusura: {e}")
        
        # 🆕 Aggiorna lo stato dopo chiusura posizione
        try:
            if state_manager and bot_status:
                # Controlla se ci sono ancora posizioni attive
                active_trades = trading_wrapper.get_active_trades()
                if len(active_trades) == 0:
                    # Nessuna posizione attiva - torna a SEEKING_ENTRY
                    state_manager.save_state_with_position(bot_status, 'SEEKING_ENTRY', trading_wrapper)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Stato aggiornato: ritorno a SEEKING_ENTRY")
                else:
                    # Ci sono ancora posizioni - continua MANAGING_POSITIONS
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 {len(active_trades)} posizioni ancora attive")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ state_manager o bot_status non disponibili per aggiornamento stato")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore aggiornamento stato dopo chiusura: {e}")
        
        socketio.emit('trade_notification', {
            'type': 'POSITION_CLOSED',
            'side': side,
            'symbol': symbol,
            'price': current_price,
            'reason': 'EMA_STOP',
            'timestamp': datetime.now().isoformat()
        })

def save_market_analysis_to_db(bot_status, market_data, trading_db):
    """Salva analisi di mercato nel database"""
    try:
        ema_data = {
            'candles_above_ema': market_data['candles_above'],
            'price': market_data['current_price'],
            'distance_percent': market_data['distance_percent'],
            'ema_value': market_data['ema_value'],
            'is_above_ema': market_data['is_above_ema']
        }
        
        trading_db.add_market_analysis(market_data['symbol'], market_data['current_price'], ema_data)
        
        # Log per database
        analysis_msg = f"Prezzo: {market_data['current_price']}, EMA: {market_data['ema_value']:.4f}, Distanza: {market_data['distance_percent']:.2f}%"
        trading_db.log_event(
            "MARKET_ANALYSIS", 
            "TRADING", 
            analysis_msg,
            {
                'price': market_data['current_price'],
                'ema_data': ema_data,
                'candles_above': market_data['candles_above'],
                'candles_below': market_data['candles_below'],
                'distance_percent': market_data['distance_percent']
            },
            session_id=bot_status['current_session_id']
        )
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore salvataggio analisi: {e}")

def emit_bot_updates(bot_status, market_data, trading_wrapper, socketio):
    """Emette aggiornamenti WebSocket"""
    try:
        socketio.emit('bot_update', {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'message': f"Analisi completata per {market_data['symbol']}",
            'price': market_data['current_price'],
            'session_id': bot_status['current_session_id'],
            'total_trades': bot_status['total_trades'],
            'session_pnl': bot_status['session_pnl'],
            'active_trades': len(trading_wrapper.get_active_trades()) if trading_wrapper else 0,
            'ema_value': market_data['ema_value'],
            'distance_percent': market_data['distance_percent'],
            'is_above_ema': market_data['is_above_ema']
        })
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore emissione WebSocket: {e}")

def handle_loop_error(error, bot_status, trading_db, socketio):
    """Gestisce errori nel loop principale"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore nel ciclo: {str(error)}")
    
    if bot_status.get('current_session_id'):
        trading_db.log_event(
            "LOOP_ERROR", 
            "ERROR", 
            f"Errore nel ciclo: {str(error)}",
            {'error': str(error)},
            severity="ERROR",
            session_id=bot_status['current_session_id']
        )
    
    socketio.emit('bot_error', {
        'type': 'loop_error',
        'error': str(error),
        'timestamp': datetime.now().isoformat()
    })

def handle_critical_error(error, bot_status, trading_db, socketio, state_manager):
    """Gestisce errori critici del bot"""
    bot_status['running'] = False
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore critico: {str(error)}")
    
    # NON salviamo come "stopped_manually" perché è un crash
    # Lo stato rimane con "is_running: False" ma senza flag manual
    if state_manager:
        # Aggiorna solo il flag running, mantenendo la config per recovery
        current_state = bot_status.copy()
        current_state['running'] = False
        # Non impostiamo stopped_manually = True perché è un crash
        state_manager.save_bot_running_state(current_state)
    
    if bot_status.get('current_session_id'):
        trading_db.log_event(
            "BOT_CRITICAL_ERROR", 
            "ERROR", 
            f"Errore critico del bot: {str(error)}",
            {'error': str(error)},
            severity="CRITICAL",
            session_id=bot_status['current_session_id']
        )
    
    socketio.emit('bot_error', {
        'type': 'critical_error',
        'error': str(error),
        'timestamp': datetime.now().isoformat()
    })

def perform_crash_recovery(bot_status, app_config, state_manager):
    """
    Esegue crash recovery avanzato con gestione delle fasi operative
    Returns: operational_phase corretta da usare
    """
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Verifica necessità crash recovery...")
        
        # Crea sistema di crash recovery
        recovery_system = create_crash_recovery_system(
            state_manager=state_manager,
            trading_wrapper=app_config.get('TRADING_WRAPPER')
        )
        
        # Controlla se serve recovery
        needs_recovery, recovery_info = recovery_system.check_crash_recovery_needed()
        
        if not needs_recovery:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Nessun recovery necessario - Avvio normale")
            return 'SEEKING_ENTRY'
        
        # Recovery necessario
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 CRASH RECOVERY RILEVATO!")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Azione: {recovery_info.get('recovery_action', 'UNKNOWN')}")
        
        # Mostra info recovery
        saved_phase = recovery_info.get('saved_state_summary', {}).get('operational_phase', 'UNKNOWN')
        correct_phase = recovery_info.get('analysis', {}).get('correct_operational_phase', 'SEEKING_ENTRY')
        real_positions = recovery_info.get('real_positions_summary', {}).get('real_positions_count', 0)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Stato salvato: {saved_phase}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Fase corretta: {correct_phase}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Posizioni reali: {real_positions}")
        
        # Esegui recovery
        success, operational_phase, updated_bot_status = recovery_system.execute_recovery(
            recovery_info, bot_status
        )
        
        if success:
            # Aggiorna bot_status con dati recuperati
            bot_status.update(updated_bot_status)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ CRASH RECOVERY COMPLETATO")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Fase operativa: {operational_phase}")
            
            if operational_phase == 'MANAGING_POSITIONS':
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Il bot riprenderà il monitoraggio delle posizioni esistenti")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Il bot riprenderà la ricerca di nuovi segnali di entrata")
            
            return operational_phase
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Recovery fallito - Modalità conservativa")
            return 'SEEKING_ENTRY'
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore durante crash recovery: {e}")
        import traceback
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Dettagli: {traceback.format_exc()}")
        return 'SEEKING_ENTRY'

def cleanup_bot_session(bot_status, state_manager):
    """Pulizia finale della sessione bot"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Terminazione bot loop")
    
    # Qui NON facciamo nulla di speciale per lo state_manager
    # Il salvataggio del "manual stop" deve essere fatto dalla route di stop
    # Se arriviamo qui per crash, lo stato è già stato salvato nell'handle_critical_error
