import time
from datetime import datetime
from trading_functions import (
    vedi_prezzo_moneta, get_kline_data, analizza_prezzo_sopra_media, 
    controlla_candele_sopra_ema, controlla_candele_sotto_ema, 
    media_esponenziale, mostra_saldo
)

def run_trading_bot(bot_status, app_config):
    """Esegue il bot di trading"""
    trading_wrapper = app_config['TRADING_WRAPPER']
    trading_db = app_config['TRADING_DB']
    socketio = app_config['SOCKETIO']
    
    try:
        # Configura sempre il wrapper prima di iniziare
        if bot_status['current_session_id']:
            # Usa sessione esistente
            trading_wrapper.set_session(bot_status['current_session_id'])
            trading_wrapper.sync_with_database()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Continuando sessione esistente: {bot_status['current_session_id']}")
        else:
            # Crea nuova sessione
            strategy_config = {
                'symbol': bot_status['symbol'],
                'ema_period': bot_status['ema_period'],
                'interval': bot_status['interval'],
                'open_candles': bot_status['open_candles'],
                'stop_candles': bot_status['stop_candles'],
                'distance': bot_status['distance'],
                'quantity': bot_status['quantity'],
                'operation': bot_status['operation']
            }
            
            # Ottieni saldo iniziale
            try:
                balance_response = mostra_saldo()
                initial_balance = balance_response.get('total_equity', 0) if balance_response else 0
            except Exception as e:
                print(f"[DEBUG] Errore mostra_saldo per initial_balance: {e}")
                initial_balance = 0
                
            bot_status['current_session_id'] = trading_db.start_session(
                bot_status['symbol'], 
                strategy_config, 
                initial_balance
            )
            bot_status['session_start_time'] = datetime.now().isoformat()
            bot_status['total_trades'] = 0
            bot_status['session_pnl'] = 0
            
            # Configura il wrapper di trading per la sessione
            trading_wrapper.set_session(bot_status['current_session_id'])
            trading_wrapper.sync_with_database()
            
            trading_db.log_event(
                "BOT_START", 
                "SYSTEM", 
                f"Bot avviato per {bot_status['symbol']}", 
                strategy_config,
                session_id=bot_status['current_session_id']
            )
        
        # Loop principale del bot
        while bot_status['running']:
            try:
                symbol = bot_status['symbol']
                current_price = vedi_prezzo_moneta('linear', symbol)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Analizzando {symbol} - Prezzo: ${current_price:.4f}")
                
                # Invia log al frontend
                socketio.emit('analysis_log', {
                    'message': f"🔍 Analizzando {symbol} - Prezzo: ${current_price:.4f}",
                    'type': 'info'
                })
                
                # Ottieni dati EMA se disponibili
                interval = bot_status['interval']
                klines = get_kline_data('linear', symbol, interval, 200)
                
                if klines:
                    # Analizza mercato e esegui strategia
                    analyze_and_execute_strategy(
                        bot_status, klines, current_price, symbol,
                        trading_wrapper, trading_db, socketio
                    )
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Nessun dato kline disponibile per {symbol}")
                
                # Emetti aggiornamenti via WebSocket
                socketio.emit('bot_update', {
                    'status': 'running',
                    'timestamp': datetime.now().isoformat(),
                    'message': f"Analisi completata per {symbol}",
                    'price': current_price,
                    'session_id': bot_status['current_session_id'],
                    'total_trades': bot_status['total_trades'],
                    'session_pnl': bot_status['session_pnl'],
                    'active_trades': len(trading_wrapper.get_active_trades()) if trading_wrapper else 0
                })
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ Attendo prossimo ciclo (10 secondi)...")
                
            except Exception as loop_error:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore nel ciclo: {str(loop_error)}")
                trading_db.log_event(
                    "LOOP_ERROR", 
                    "ERROR", 
                    f"Errore nel ciclo: {str(loop_error)}",
                    {'error': str(loop_error)},
                    severity="ERROR",
                    session_id=bot_status['current_session_id']
                )
            
            time.sleep(10)
            
    except Exception as e:
        bot_status['running'] = False
        if bot_status.get('current_session_id'):
            trading_db.log_event(
                "BOT_ERROR", 
                "ERROR", 
                f"Errore del bot: {str(e)}",
                {'error': str(e)},
                severity="ERROR",
                session_id=bot_status['current_session_id']
            )
        
        socketio.emit('bot_error', {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

def analyze_and_execute_strategy(bot_status, klines, current_price, symbol, 
                                trading_wrapper, trading_db, socketio):
    """Analizza il mercato ed esegue la strategia di trading"""
    try:
        # Analisi EMA
        ema_analysis = analizza_prezzo_sopra_media('linear', symbol, bot_status['interval'], bot_status['ema_period'])
        
        if ema_analysis and len(ema_analysis) >= 3:
            distance_percent = ema_analysis[2]
            is_above_ema = distance_percent > 0
        else:
            distance_percent = 0
            is_above_ema = False
        
        # Calcola EMA attuale
        reversed_klines = reversed(klines)
        close_prices = [float(candle[4]) for candle in reversed_klines]
        ema_values = media_esponenziale(close_prices, bot_status['ema_period'])
        ema_value = ema_values[-1] if ema_values else current_price
        
        if ema_value > 0:
            distance_percent = ((current_price - ema_value) / ema_value) * 100
            is_above_ema = distance_percent > 0
        
        # Controlla candele consecutive
        candles_above_result = controlla_candele_sopra_ema('linear', symbol, bot_status['interval'], bot_status['ema_period'])
        candles_below_result = controlla_candele_sotto_ema('linear', symbol, bot_status['interval'], bot_status['ema_period'])
        
        candles_above = candles_above_result[0] if candles_above_result and len(candles_above_result) > 0 else 0
        candles_below = candles_below_result[0] if candles_below_result and len(candles_below_result) > 0 else 0
        
        # Log analisi
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 EMA({bot_status['ema_period']}): ${ema_value:.4f}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Prezzo {'SOPRA' if is_above_ema else 'SOTTO'} EMA ({distance_percent:+.2f}%)")
        
        # Verifica posizioni attive
        active_trades = trading_wrapper.get_active_trades()
        
        if not active_trades:
            # Analisi apertura posizioni
            analyze_entry_signals(bot_status, is_above_ema, candles_above, candles_below, 
                                distance_percent, current_price, symbol, 
                                trading_wrapper, socketio)
        else:
            # Analisi chiusura posizioni
            analyze_exit_signals(bot_status, active_trades, candles_above, candles_below,
                                current_price, trading_wrapper, socketio)
        
        # Salva analisi di mercato
        ema_data = {
            'candles_above_ema': candles_above,
            'price': current_price,
            'distance_percent': distance_percent,
            'ema_value': ema_value,
            'is_above_ema': is_above_ema
        }
        trading_db.add_market_analysis(symbol, current_price, ema_data)
        
        # Log dell'analisi per database
        analysis_msg = f"Prezzo: {current_price}, EMA: {ema_value:.4f}, Distanza: {distance_percent:.2f}%"
        trading_db.log_event(
            "MARKET_ANALYSIS", 
            "TRADING", 
            analysis_msg,
            {
                'price': current_price,
                'ema_data': ema_data,
                'candles_above': candles_above,
                'candles_below': candles_below,
                'distance_percent': distance_percent
            },
            session_id=bot_status['current_session_id']
        )
        
    except Exception as analysis_error:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore nell'analisi: {str(analysis_error)}")
        trading_db.log_event(
            "ANALYSIS_ERROR", 
            "ERROR", 
            f"Errore nell'analisi: {str(analysis_error)}",
            {'error': str(analysis_error)},
            severity="ERROR",
            session_id=bot_status['current_session_id']
        )

def analyze_entry_signals(bot_status, is_above_ema, candles_above, candles_below, 
                         distance_percent, current_price, symbol, trading_wrapper, socketio):
    """Analizza i segnali di entrata per nuove posizioni"""
    distance_ok = abs(distance_percent) <= bot_status['distance']
    
    socketio.emit('analysis_log', {
        'message': f"🔍 Nessuna posizione attiva - Analisi condizioni apertura...",
        'type': 'info'
    })
    
    # Condizioni per LONG
    if bot_status['operation']:  # True = Long
        long_conditions = {
            'above_ema': is_above_ema,
            'enough_candles': candles_above >= bot_status['open_candles'],
            'distance_ok': distance_ok
        }
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 LONG - Condizioni apertura:")
        print(f"  ✅ Sopra EMA: {'✅' if long_conditions['above_ema'] else '❌'}")
        print(f"  ✅ Candele richieste: {'✅' if long_conditions['enough_candles'] else '❌'} ({candles_above}/{bot_status['open_candles']})")
        print(f"  ✅ Distanza OK: {'✅' if long_conditions['distance_ok'] else '❌'} ({distance_percent:.2f}% <= {bot_status['distance']}%)")
        
        if all(long_conditions.values()):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE LONG! Apertura posizione...")
            
            result = trading_wrapper.open_position(
                symbol=symbol,
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
                bot_status['total_trades'] += 1
                socketio.emit('trade_notification', {
                    'type': 'POSITION_OPENED',
                    'side': 'LONG',
                    'symbol': symbol,
                    'price': current_price,
                    'quantity': bot_status['quantity'],
                    'timestamp': datetime.now().isoformat()
                })
    
    # Condizioni per SHORT
    else:  # False = Short
        short_conditions = {
            'below_ema': not is_above_ema,
            'enough_candles': candles_below >= bot_status['open_candles'],
            'distance_ok': distance_ok
        }
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 SHORT - Condizioni apertura:")
        print(f"  ✅ Sotto EMA: {'✅' if short_conditions['below_ema'] else '❌'}")
        print(f"  ✅ Candele richieste: {'✅' if short_conditions['enough_candles'] else '❌'} ({candles_below}/{bot_status['open_candles']})")
        print(f"  ✅ Distanza OK: {'✅' if short_conditions['distance_ok'] else '❌'} ({abs(distance_percent):.2f}% <= {bot_status['distance']}%)")
        
        if all(short_conditions.values()):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SEGNALE SHORT! Apertura posizione...")
            
            result = trading_wrapper.open_position(
                symbol=symbol,
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
                bot_status['total_trades'] += 1
                socketio.emit('trade_notification', {
                    'type': 'POSITION_OPENED',
                    'side': 'SHORT',
                    'symbol': symbol,
                    'price': current_price,
                    'quantity': bot_status['quantity'],
                    'timestamp': datetime.now().isoformat()
                })

def analyze_exit_signals(bot_status, active_trades, candles_above, candles_below, 
                        current_price, trading_wrapper, socketio):
    """Analizza i segnali di uscita per posizioni attive"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Posizioni attive trovate ({len(active_trades)}) - Analisi condizioni chiusura...")
    
    for trade_id, trade_info in active_trades.items():
        trade_side = trade_info['side']
        trade_symbol = trade_info.get('symbol', bot_status['symbol'])
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Analizzando posizione {trade_side} {trade_symbol}")
        
        # Condizioni di chiusura per LONG
        if trade_side == 'Buy':
            close_long = candles_below >= bot_status['stop_candles']
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 LONG {trade_symbol} - Candele sotto EMA: {candles_below}/{bot_status['stop_candles']}")
            
            if close_long:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔻 SEGNALE CHIUSURA LONG! Eseguendo chiusura...")
                
                result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                if result['success']:
                    socketio.emit('trade_notification', {
                        'type': 'POSITION_CLOSED',
                        'side': 'LONG',
                        'symbol': trade_symbol,
                        'price': current_price,
                        'reason': 'EMA_STOP',
                        'timestamp': datetime.now().isoformat()
                    })
        
        # Condizioni di chiusura per SHORT  
        elif trade_side == 'Sell':
            close_short = candles_above >= bot_status['stop_candles']
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 SHORT {trade_symbol} - Candele sopra EMA: {candles_above}/{bot_status['stop_candles']}")
            
            if close_short:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔺 SEGNALE CHIUSURA SHORT! Eseguendo chiusura...")
                
                result = trading_wrapper.close_position(trade_id, current_price, "EMA_STOP")
                if result['success']:
                    socketio.emit('trade_notification', {
                        'type': 'POSITION_CLOSED',
                        'side': 'SHORT',
                        'symbol': trade_symbol,
                        'price': current_price,
                        'reason': 'EMA_STOP',
                        'timestamp': datetime.now().isoformat()
                    })