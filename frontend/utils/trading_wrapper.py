"""
Wrapper per le funzioni di trading che integra il salvataggio nel database
"""

import sys
import os
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Aggiungi il percorso del bot principale
bot_path = Path(__file__).parent.parent.parent  # Vai alla root del progetto
sys.path.append(str(bot_path))
print(f"[TRADING_WRAPPER] Aggiunto path: {bot_path}")

# Import database
from utils.database import trading_db

# Import funzioni originali del bot
try:
    from core.trading_functions import (
        bot_open_position,
        bot_trailing_stop,
        mostra_saldo,
        vedi_prezzo_moneta
    )
    from core.config import api, api_sec
    print("[TRADING_WRAPPER] ✅ Funzioni di trading importate con successo")
    TRADING_FUNCTIONS_AVAILABLE = True
except ImportError as e:
    print(f"[TRADING_WRAPPER] ❌ Errore nell'importazione delle funzioni del trading bot: {e}")
    bot_open_position = None
    bot_trailing_stop = None
    mostra_saldo = None
    vedi_prezzo_moneta = None
    TRADING_FUNCTIONS_AVAILABLE = False

class TradingWrapper:
    """Wrapper per le funzioni di trading con integrazione database"""
    
    def __init__(self):
        self.current_session_id = None
        self.active_trades = {}  # trade_id -> trade_info
        
    def set_session(self, session_id):
        """Imposta la sessione corrente e gestisce posizioni orfane da recovery"""
        self.current_session_id = session_id
        
        # 🆕 Gestisci posizioni orfane da recovery
        orphan_trades = {trade_id: trade for trade_id, trade in self.active_trades.items() 
                        if trade.get('recovery_orphan') and trade.get('needs_session')}
        
        if orphan_trades:
            print(f"🔄 Gestione {len(orphan_trades)} posizioni orfane da recovery...")
            
            for temp_trade_id, trade_info in orphan_trades.items():
                try:
                    # Registra nel database con la nuova sessione
                    db_trade_id = trading_db.add_trade(
                        session_id=session_id,
                        symbol=trade_info['symbol'],
                        side=trade_info['side'].upper(),
                        entry_price=trade_info['entry_price'],
                        quantity=trade_info['quantity'],
                        strategy_signal="RECOVERY_ORPHAN"
                    )
                    
                    # Crea mappatura
                    external_id = trade_info.get('external_trade_id', f"BYBIT_{trade_info['symbol']}_{trade_info['side']}_{int(time.time())}")
                    trading_db.add_trade_id_mapping(db_trade_id, external_id, 
                                                   symbol=trade_info['symbol'], 
                                                   side=trade_info['side'])
                    
                    # Aggiorna il trade nel wrapper con l'ID corretto
                    self.active_trades[db_trade_id] = {
                        'symbol': trade_info['symbol'],
                        'side': trade_info['side'],
                        'quantity': trade_info['quantity'],
                        'entry_price': trade_info['entry_price'],
                        'timestamp': trade_info['timestamp'],
                        'bybit_sync': True,
                        'external_trade_id': external_id,
                        'recovered': True
                    }
                    
                    # Rimuovi il trade temporaneo
                    del self.active_trades[temp_trade_id]
                    
                    print(f"✅ Posizione orfana registrata: {temp_trade_id} -> {db_trade_id}")
                    
                except Exception as e:
                    print(f"❌ Errore registrazione posizione orfana {temp_trade_id}: {e}")
            
            print(f"✅ Gestione posizioni orfane completata")
        
        print(f"📋 Sessione impostata: {session_id}, Posizioni attive: {len(self.active_trades)}")
    
    def open_position(self, symbol, side, quantity, price=None, **kwargs):
        """
        Apre una posizione e la registra nel database
        
        Args:
            symbol: Simbolo da tradare (es. 'AVAXUSDT')
            side: 'Buy' o 'Sell'
            quantity: Quantità da tradare
            price: Prezzo (None per market order)
            **kwargs: Altri parametri per la funzione originale
        """
        if not TRADING_FUNCTIONS_AVAILABLE or not bot_open_position:
            raise Exception("Funzione di apertura posizione non disponibile")
        
        try:
            # Log tentativo di apertura
            trading_db.log_event(
                "POSITION_OPEN_ATTEMPT",
                "TRADING",
                f"Tentativo apertura posizione: {side} {quantity} {symbol}",
                {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price
                },
                session_id=self.current_session_id
            )
            
            # Chiama la funzione originale con i parametri corretti
            # bot_open_position(categoria, simbolo, periodo_ema, intervallo, quantita, candele, lunghezza, operazione)
            # La funzione originale non restituisce un valore, fa tutto il processo direttamente
            categoria = kwargs.get('categoria', 'linear')
            periodo_ema = kwargs.get('periodo_ema', 10)
            intervallo = kwargs.get('intervallo', 30)
            candele = kwargs.get('candele', 3)
            lunghezza = kwargs.get('lunghezza', 3)
            operazione = True if side.lower() == 'buy' else False
            
            try:
                # Per catturare il numero di monete, dobbiamo usare direttamente le funzioni bybit
                from core.trading_functions import compra_moneta_bybit_by_quantita, vendi_moneta_bybit_by_quantita
                
                if side.lower() == 'buy':
                    # LONG: compra monete
                    tokens_bought = compra_moneta_bybit_by_quantita(categoria, symbol, quantity)
                    actual_quantity = tokens_bought
                else:
                    # SHORT: vendi monete  
                    tokens_sold = vendi_moneta_bybit_by_quantita(categoria, symbol, quantity)
                    actual_quantity = tokens_sold
                
                print(f"✅ Operazione completata: {actual_quantity} {symbol} per ${quantity} USD")
                
                # Se arriviamo qui senza eccezioni, assumiamo il successo
                # Recupera il prezzo di mercato corrente come entry_price se non fornito
                if price:
                    entry_price = price
                else:
                    try:
                        entry_price = vedi_prezzo_moneta('linear', symbol)
                    except Exception:
                        entry_price = 0
                result = {
                    'success': True,
                    'entry_price': entry_price,
                    'order_id': f"BOT_{symbol}_{int(time.time())}",
                    'actual_quantity': actual_quantity  # Quantità reale in monete
                }
            except Exception as e:
                result = {
                    'success': False,
                    'error': str(e)
                }
            
            if result and result.get('success'):
                # Usa la quantità reale in monete invece che in USD
                actual_quantity = result.get('actual_quantity', quantity)
                
                # Salva trade nel database
                trade_id = trading_db.add_trade(
                    session_id=self.current_session_id,
                    symbol=symbol,
                    side=side.upper(),
                    entry_price=result.get('entry_price', price),
                    quantity=actual_quantity,  # Quantità in monete, non USD
                    strategy_signal=kwargs.get('strategy_signal', 'MANUAL')
                )
                
                # Crea ID esterno per mappatura con Bybit
                external_id = f"BYBIT_{symbol}_{side}_{int(time.time())}"
                
                # Salva mappatura ID
                trading_db.add_trade_id_mapping(
                    internal_trade_id=trade_id,
                    external_trade_id=external_id,
                    bybit_order_id=result.get('order_id'),
                    symbol=symbol,
                    side=side
                )
                
                # Memorizza il trade attivo con entrambi gli ID
                self.active_trades[trade_id] = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': actual_quantity,  # Quantità in monete, non USD
                    'entry_price': result.get('entry_price', price),
                    'bybit_order_id': result.get('order_id'),
                    'external_trade_id': external_id,  # ID per recovery
                    'timestamp': datetime.now().isoformat()
                }
                
                # 🆕 IMPORTANTE: Sincronizza immediatamente con Bybit per ottenere l'ID reale della posizione
                try:
                    print(f"🔄 Sincronizzazione immediata con Bybit per posizione {trade_id}...")
                    
                    # Importa credenziali API
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from core.config import api, api_sec
                    
                    # Ottieni le posizioni aggiornate da Bybit
                    from pybit.unified_trading import HTTP
                    session = HTTP(
                        testnet=False,
                        api_key=api,
                        api_secret=api_sec,
                    )
                    
                    response = session.get_positions(category="linear", settleCoin="USDT")
                    if response['retCode'] == 0:
                        bybit_positions = response['result']['list']
                        
                        # Trova la posizione che corrisponde al nostro trade
                        for pos in bybit_positions:
                            if (pos['symbol'] == symbol and 
                                pos['side'] == side and 
                                float(pos.get('size', 0)) > 0):
                                
                                # Aggiorna la mappatura con l'ID reale della posizione
                                real_external_id = f"BYBIT_{symbol}_{side}_{pos.get('positionIdx', int(time.time()))}"
                                
                                # Aggiorna la mappatura nel database
                                trading_db.add_trade_id_mapping(
                                    internal_trade_id=trade_id,
                                    external_trade_id=real_external_id,
                                    bybit_order_id=result.get('order_id'),
                                    symbol=symbol,
                                    side=side
                                )
                                
                                # Aggiorna l'active_trades con l'ID reale
                                self.active_trades[trade_id]['real_external_id'] = real_external_id
                                
                                print(f"✅ ID reale Bybit associato: {trade_id} -> {real_external_id}")
                                break
                        
                except Exception as e:
                    print(f"⚠️ Errore sincronizzazione immediata con Bybit: {e}")
                    # Non è un errore critico, continuiamo
                
                # Log successo
                trading_db.log_event(
                    "POSITION_OPENED",
                    "TRADING",
                    f"Posizione aperta con successo: {trade_id}",
                    {
                        'trade_id': trade_id,
                        'symbol': symbol,
                        'side': side,
                        'quantity_usd': quantity,  # Quantità originale in USD
                        'quantity_tokens': actual_quantity,  # Quantità reale in monete
                        'entry_price': result.get('entry_price'),
                        'bybit_order_id': result.get('order_id')
                    },
                    session_id=self.current_session_id
                )
                
                return {
                    'success': True,
                    'trade_id': trade_id,
                    'message': f'Posizione {side} aperta per {symbol}',
                    'data': result
                }
            else:
                # Log fallimento
                trading_db.log_event(
                    "POSITION_OPEN_FAILED",
                    "ERROR",
                    f"Fallimento apertura posizione: {result.get('error', 'Errore sconosciuto')}",
                    {
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'error': result.get('error') if result else 'Nessuna risposta'
                    },
                    severity="ERROR",
                    session_id=self.current_session_id
                )
                
                return {
                    'success': False,
                    'error': result.get('error', 'Errore nell\'apertura della posizione') if result else 'Nessuna risposta dal broker'
                }
                
        except Exception as e:
            # Log eccezione
            trading_db.log_event(
                "POSITION_OPEN_EXCEPTION",
                "ERROR", 
                f"Eccezione durante apertura posizione: {str(e)}",
                {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
            
            return {
                'success': False,
                'error': f'Eccezione durante apertura posizione: {str(e)}'
            }
    
    def close_position(self, trade_id=None, symbol=None, side=None, price=None, reason="MANUAL", **kwargs):
        """
        Chiude una posizione e aggiorna il database
        
        Args:
            trade_id: ID del trade da chiudere (opzionale se forniti symbol+side)
            symbol: Simbolo da chiudere (opzionale se fornito trade_id)
            side: Lato della posizione (opzionale se fornito trade_id)
            price: Prezzo di chiusura (None per market price)
            reason: Motivo della chiusura
            **kwargs: Altri parametri
        """
        
        # Trova il trade da chiudere
        trade_info = None
        final_trade_id = trade_id
        
        # Caso 1: trade_id fornito direttamente - controlla negli active_trades
        if trade_id and trade_id in self.active_trades:
            trade_info = self.active_trades[trade_id]
            print(f"🎯 Trade trovato negli active_trades: {trade_id}")
        
        # Caso 2: Cerca per symbol+side negli active_trades
        elif symbol and side:
            for tid, tinfo in self.active_trades.items():
                if tinfo.get('symbol') == symbol and tinfo.get('side') == side:
                    trade_info = tinfo
                    final_trade_id = tid
                    print(f"🎯 Trade trovato negli active_trades per symbol+side: {tid}")
                    break
        
        # Caso 3: Se non trovato negli active_trades, cerca nel database
        if not trade_info:
            print(f"🔍 Trade non trovato negli active_trades, cercando nel database...")
            
            try:
                # Prima prova a cercare per external_trade_id se sembra essere un ID Bybit
                if trade_id and trade_id.startswith('BYBIT_'):
                    internal_id = trading_db.get_internal_trade_id(trade_id)
                    if internal_id:
                        final_trade_id = internal_id
                        print(f"🔄 Conversione ID: {trade_id} -> {internal_id}")
                
                # Se ancora non trovato, cerca per symbol+side nel database
                if not trade_info:
                    if symbol and side:
                        search_session = self.current_session_id if self.current_session_id else None
                        final_trade_id = trading_db.find_trade_by_symbol_side(symbol, side, search_session)
                        print(f"🔍 Ricerca database per {symbol} {side} in sessione {search_session}: {final_trade_id}")
                    
                    if final_trade_id:
                        # Ottieni dati del trade dal database
                        try:
                            trades = trading_db.get_trade_history(self.current_session_id, 200) if self.current_session_id else []
                            # Se non trovato nella sessione corrente, cerca in tutte le sessioni
                            if not trades:
                                # Cerca in tutte le sessioni per recovery
                                all_sessions = trading_db.get_all_sessions()
                                for session in all_sessions:
                                    trades = trading_db.get_trade_history(session['session_id'], 200)
                                    matching_trades = [t for t in trades if t['trade_id'] == final_trade_id and t['status'] == 'OPEN']
                                    if matching_trades:
                                        break
                            else:
                                matching_trades = [t for t in trades if t['trade_id'] == final_trade_id and t['status'] == 'OPEN']
                            
                            if matching_trades:
                                db_trade = matching_trades[0]
                                trade_info = {
                                    'symbol': db_trade['symbol'],
                                    'side': db_trade['side'],
                                    'quantity': db_trade['quantity'],
                                    'entry_price': db_trade['entry_price'],
                                    'timestamp': db_trade['entry_time']
                                }
                                
                                # Aggiungi agli active_trades per tracking futuro
                                self.active_trades[final_trade_id] = trade_info
                                print(f"📋 Trade recuperato dal database: {final_trade_id}")
                            else:
                                print(f"❌ Trade {final_trade_id} non trovato o già chiuso nel database")
                                
                        except Exception as e:
                            print(f"❌ Errore lettura database: {e}")
                    
            except Exception as e:
                print(f"❌ Errore ricerca trade nel database: {e}")
        
        if not trade_info:
            return {
                'success': False,
                'error': f'Trade non trovato: trade_id={trade_id}, symbol={symbol}, side={side}'
            }
        
        try:
            # Log tentativo chiusura
            trading_db.log_event(
                "POSITION_CLOSE_ATTEMPT",
                "TRADING",
                f"Tentativo chiusura posizione: {final_trade_id}",
                {
                    'trade_id': final_trade_id,
                    'reason': reason,
                    'close_price': price,
                    'found_in': 'active_trades' if trade_id in self.active_trades else 'database'
                },
                session_id=self.current_session_id
            )
            
            # Se price non specificato, ottieni prezzo corrente
            if price is None:
                current_price = self.get_current_price(trade_info['symbol'])
                if current_price:
                    price = current_price
                else:
                    return {
                        'success': False,
                        'error': 'Impossibile ottenere prezzo corrente'
                    }
            
            # CHIUSURA REALE SU BYBIT usando le funzioni originali
            success_bybit = False
            try:
                from core.trading_functions import chiudi_operazione_long, chiudi_operazione_short
                
                symbol = trade_info['symbol']
                quantity = trade_info['quantity']
                side = trade_info['side']
                
                print(f"🔄 Chiusura reale Bybit: {side} {quantity} {symbol}")
                
                # ✅ CORREZIONE: Normalizza il side a maiuscolo per il confronto
                side_normalized = side.upper()
                
                # ✅ CORREZIONE: Cattura il risultato e verifica il successo
                if side_normalized == 'BUY':
                    # Per chiudere BUY, dobbiamo fare SELL
                    result = chiudi_operazione_long("linear", symbol, quantity)
                elif side_normalized == 'SELL':
                    # Per chiudere SELL, dobbiamo fare BUY  
                    result = chiudi_operazione_short("linear", symbol, quantity)
                else:
                    raise ValueError(f"Side non riconosciuto: {side} (normalizzato: {side_normalized})")
                
                # Verifica se l'ordine è andato a buon fine
                if result and result.get('retCode') == 0:
                    print(f"✅ Posizione chiusa su Bybit: {result.get('result', {}).get('orderId')}")
                    success_bybit = True
                else:
                    error_msg = result.get('retMsg', 'Errore sconosciuto') if result else 'Nessuna risposta da Bybit'
                    print(f"❌ Errore chiusura Bybit: {error_msg}")
                    return {
                        'success': False,
                        'error': f'Errore Bybit: {error_msg}'
                    }
                    
            except Exception as e:
                print(f"❌ Eccezione durante chiusura Bybit: {e}")
                return {
                    'success': False,
                    'error': f'Eccezione Bybit: {str(e)}'
                }
            
            # Se la chiusura Bybit è andata bene, aggiorna il database
            if success_bybit:
                # Calcola fee approssimativa (0.1%)
                fee = (price * trade_info['quantity']) * 0.001
                
                # Aggiorna il trade nel database
                trading_db.close_trade(final_trade_id, price, fee)
                
                # Rimuovi dai trade attivi
                if final_trade_id in self.active_trades:
                    del self.active_trades[final_trade_id]
                
                # Log successo
                trading_db.log_event(
                    "POSITION_CLOSED",
                    "TRADING",
                    f"Posizione chiusa con successo: {final_trade_id}",
                    {
                        'trade_id': final_trade_id,
                        'close_price': price,
                        'reason': reason,
                        'fee': fee
                    },
                    session_id=self.current_session_id
                )
                
                return {
                    'success': True,
                    'trade_id': final_trade_id,
                    'message': f'Posizione {final_trade_id} chiusa',
                    'close_price': price,
                    'fee': fee
                }
            else:
                return {
                    'success': False,
                    'error': 'Chiusura Bybit fallita'
                }
                
        except Exception as e:
            # Log eccezione
            trading_db.log_event(
                "POSITION_CLOSE_EXCEPTION",
                "ERROR",
                f"Eccezione durante chiusura posizione: {str(e)}",
                {
                    'trade_id': final_trade_id,
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
            
            return {
                'success': False,
                'error': f'Eccezione durante chiusura posizione: {str(e)}'
            }
    
    def trailing_stop(self, symbol, **kwargs):
        """
        Gestisce il trailing stop e registra le azioni
        """
        if not TRADING_FUNCTIONS_AVAILABLE or not bot_trailing_stop:
            return {
                'success': False,
                'error': 'Funzione trailing stop non disponibile'
            }
        
        try:
            # Log esecuzione trailing stop
            trading_db.log_event(
                "TRAILING_STOP_CHECK",
                "TRADING",
                f"Controllo trailing stop per {symbol}",
                {
                    'symbol': symbol,
                    'parameters': kwargs
                },
                session_id=self.current_session_id
            )
            
            # Chiama funzione originale
            result = bot_trailing_stop(symbol, **kwargs)
            
            if result:
                trading_db.log_event(
                    "TRAILING_STOP_ACTION",
                    "TRADING",
                    f"Azione trailing stop: {result.get('action', 'unknown')}",
                    {
                        'symbol': symbol,
                        'result': result
                    },
                    session_id=self.current_session_id
                )
            
            return result
            
        except Exception as e:
            trading_db.log_event(
                "TRAILING_STOP_EXCEPTION",
                "ERROR",
                f"Eccezione durante trailing stop: {str(e)}",
                {
                    'symbol': symbol,
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
            
            return {
                'success': False,
                'error': f'Errore trailing stop: {str(e)}'
            }
    
    def get_balance(self):
        """Ottiene il saldo e registra la query"""
        if not TRADING_FUNCTIONS_AVAILABLE or not mostra_saldo:
            return {
                'success': False,
                'error': 'Funzione saldo non disponibile'
            }
        
        try:
            result = mostra_saldo()
            
            if result:
                trading_db.log_event(
                    "BALANCE_CHECK",
                    "SYSTEM",
                    f"Saldo controllato: ${result.get('total_equity', 0):.2f}",
                    {
                        'balance_data': result
                    },
                    session_id=self.current_session_id
                )
            
            return result
            
        except Exception as e:
            trading_db.log_event(
                "BALANCE_CHECK_EXCEPTION",
                "ERROR",
                f"Errore controllo saldo: {str(e)}",
                {
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
            
            return {
                'success': False,
                'error': f'Errore controllo saldo: {str(e)}'
            }
    
    def get_current_price(self, symbol):
        """Ottiene il prezzo corrente"""
        if not TRADING_FUNCTIONS_AVAILABLE or not vedi_prezzo_moneta:
            return None
        
        try:
            price = vedi_prezzo_moneta('linear', symbol)
            return price
        except Exception as e:
            trading_db.log_event(
                "PRICE_CHECK_EXCEPTION",
                "ERROR",
                f"Errore controllo prezzo {symbol}: {str(e)}",
                {
                    'symbol': symbol,
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
            return None
    
    def get_active_trades(self):
        """Restituisce i trade attualmente attivi"""
        return self.active_trades.copy()
    
    def sync_with_database(self):
        """Sincronizza i trade attivi con il database"""
        try:
            if self.current_session_id:
                # Caso normale: carica trade aperti dalla sessione corrente
                trades = trading_db.get_trade_history(self.current_session_id, 100)
                open_trades = [t for t in trades if t['status'] == 'OPEN']
                
                print(f"📋 Sync database: sessione {self.current_session_id}, {len(open_trades)} trade aperti")
                
                # Aggiorna active_trades
                self.active_trades = {}
                for trade in open_trades:
                    self.active_trades[trade['trade_id']] = {
                        'symbol': trade['symbol'],
                        'side': trade['side'],
                        'quantity': trade['quantity'],
                        'entry_price': trade['entry_price'],
                        'timestamp': trade['entry_time']
                    }
                
                trading_db.log_event(
                    "TRADES_SYNCED",
                    "SYSTEM",
                    f"Sincronizzati {len(self.active_trades)} trade attivi",
                    {
                        'active_trades': len(self.active_trades),
                        'session_id': self.current_session_id
                    },
                    session_id=self.current_session_id
                )
                
            else:
                # Recovery mode: cerca trade aperti in TUTTE le sessioni attive
                print(f"📋 Sync database: modalità recovery - cerca in tutte le sessioni")
                
                # Ottieni tutte le sessioni attive (non terminate)
                with sqlite3.connect(trading_db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT DISTINCT session_id FROM trades 
                        WHERE status = 'OPEN'
                        ORDER BY entry_time DESC
                    ''')
                    active_sessions = [row[0] for row in cursor.fetchall()]
                
                print(f"📋 Trovate {len(active_sessions)} sessioni con trade aperti")
                
                # Carica tutti i trade aperti
                all_open_trades = []
                for session_id in active_sessions:
                    trades = trading_db.get_trade_history(session_id, 100)
                    session_open_trades = [t for t in trades if t['status'] == 'OPEN']
                    all_open_trades.extend(session_open_trades)
                    print(f"   - {session_id}: {len(session_open_trades)} trade aperti")
                
                # Aggiorna active_trades
                self.active_trades = {}
                for trade in all_open_trades:
                    self.active_trades[trade['trade_id']] = {
                        'symbol': trade['symbol'],
                        'side': trade['side'],
                        'quantity': trade['quantity'],
                        'entry_price': trade['entry_price'],
                        'timestamp': trade['entry_time'],
                        'session_id': trade['session_id'],  # Mantieni riferimento sessione
                        'recovered_from_db': True  # Flag per indicare recovery da DB
                    }
                
                print(f"📋 Recovery sync: caricati {len(self.active_trades)} trade totali")
                
        except Exception as e:
            trading_db.log_event(
                "SYNC_EXCEPTION",
                "ERROR",
                f"Errore sincronizzazione: {str(e)}",
                {
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )

    def sync_with_bybit(self):
        """Sincronizza con le posizioni reali su Bybit"""
        try:
            from pybit.unified_trading import HTTP
            
            session = HTTP(
                testnet=False,
                api_key=api,
                api_secret=api_sec,
            )
            
            # Ottieni posizioni attive da Bybit
            response = session.get_positions(category="linear", settleCoin="USDT")
            
            if response['retCode'] == 0:
                bybit_positions = response['result']['list']
                
                # Filtra solo posizioni con size > 0
                active_positions = [pos for pos in bybit_positions if float(pos.get('size', 0)) > 0]
                
                print(f"🔄 Trovate {len(active_positions)} posizioni attive su Bybit")
                
                for pos in active_positions:
                    symbol = pos['symbol']
                    side = 'Buy' if pos['side'] == 'Buy' else 'Sell'  # Normalizza
                    size = float(pos['size'])
                    avg_price = float(pos['avgPrice']) if pos['avgPrice'] else 0
                    
                    # Prima controlla se esiste già nel database per questa sessione
                    existing_trade_id = None
                    
                    # Durante recovery, cerca in TUTTE le sessioni aperte se non c'è sessione corrente
                    if self.current_session_id:
                        existing_trade_id = trading_db.find_trade_by_symbol_side(symbol, side, self.current_session_id)
                    else:
                        # Recovery: cerca trade aperti in qualsiasi sessione
                        existing_trade_id = trading_db.find_trade_by_symbol_side(symbol, side, None)
                        print(f"🔄 Recovery mode: cerca trade {symbol} {side} in tutte le sessioni")
                    
                    if existing_trade_id:
                        # Trade esiste già nel database, usalo
                        self.active_trades[existing_trade_id] = {
                            'symbol': symbol,
                            'side': side,
                            'quantity': size,
                            'entry_price': avg_price,
                            'timestamp': datetime.now().isoformat(),
                            'bybit_sync': True,
                            'recovered': True  # Flag per indicare che è stato recuperato
                        }
                        
                        print(f"♻️ Posizione esistente recuperata: {existing_trade_id} - {side} {size} {symbol}")
                        
                        # Crea mappatura se non esiste
                        external_id = f"BYBIT_{symbol}_{side}_{int(time.time())}"
                        trading_db.add_trade_id_mapping(existing_trade_id, external_id, symbol=symbol, side=side)
                        
                    else:
                        # 🆕 Durante recovery, se non trovato nel database ma esiste su Bybit,
                        # potrebbe essere una posizione "orfana" - gestiamola comunque
                        print(f"⚠️ Posizione Bybit non trovata nel database: {symbol} {side} {size}")
                        
                        # 🔧 CONTROLLO DUPLICATI RIGOROSO: Verifica sia in active_trades che nel database
                        existing = None
                        
                        # 1. Controlla active_trades
                        for trade_id, trade_info in self.active_trades.items():
                            if (trade_info.get('symbol') == symbol and 
                                trade_info.get('side') == side and 
                                abs(float(trade_info.get('quantity', 0)) - size) < 10):  # Tolleranza di 10 token
                                existing = trade_id
                                print(f"⚠️ Posizione simile già in active_trades: {trade_id}")
                                break
                        
                        # 2. Se non trovato in active_trades, controlla nel database
                        if not existing and self.current_session_id:
                            try:
                                trades = trading_db.get_trade_history(self.current_session_id, 50)
                                for trade in trades:
                                    if (trade['symbol'] == symbol and 
                                        trade['side'].upper() == side.upper() and
                                        trade['status'] == 'OPEN' and
                                        abs(float(trade['quantity']) - size) < 10):
                                        existing = trade['trade_id']
                                        print(f"⚠️ Posizione simile già nel database: {existing}")
                                        break
                            except Exception as e:
                                print(f"❌ Errore controllo database duplicati: {e}")
                        
                        if not existing:
                            # Crea un ID temporaneo per tracking
                            temp_trade_id = f"RECOVERY_{symbol}_{side}_{int(time.time())}"
                            external_id = f"BYBIT_{symbol}_{side}_{int(time.time())}"
                            
                            # 🔧 IMPORTANTE: Registra immediatamente nel database se abbiamo una sessione
                            if self.current_session_id:
                                try:
                                    # Registra come trade orphan nel database
                                    db_trade_id = trading_db.add_trade(
                                        session_id=self.current_session_id,
                                        symbol=symbol,
                                        side=side.upper(),
                                        entry_price=avg_price,
                                        quantity=size,
                                        strategy_signal="RECOVERY_ORPHAN"
                                    )
                                    
                                    # Crea la mappatura ID
                                    trading_db.add_trade_id_mapping(db_trade_id, external_id, symbol=symbol, side=side)
                                    
                                    # Usa l'ID del database invece del temporaneo
                                    temp_trade_id = db_trade_id
                                    
                                    print(f"✅ Posizione orfana registrata nel database: {db_trade_id}")
                                    
                                except Exception as e:
                                    print(f"❌ Errore registrazione posizione orfana: {e}")
                                    # Se fallisce la registrazione, usa l'ID temporaneo ma marca per registrazione successiva
                                    temp_trade_id = f"RECOVERY_{symbol}_{side}_{int(time.time())}"
                            
                            # Aggiungi al wrapper per tracking immediato
                            self.active_trades[temp_trade_id] = {
                                'symbol': symbol,
                                'side': side,
                                'quantity': size,
                                'entry_price': avg_price,
                                'timestamp': datetime.now().isoformat(),
                                'bybit_sync': True,
                                'external_trade_id': external_id,
                                'recovery_orphan': True,  # Flag speciale per posizioni orfane
                                'db_registered': bool(self.current_session_id),  # Se registrato nel DB
                                'needs_session': not bool(self.current_session_id)  # Se serve registrazione
                            }
                            
                            print(f"🆘 Posizione orfana aggiunta per recovery: {temp_trade_id} - {side} {size} {symbol}")
                        else:
                            print(f"✅ Duplicato evitato completamente per {symbol} {side} - esistente: {existing}")
                added_count = len([t for t in self.active_trades.values() if t.get('bybit_sync')])
                print(f"📊 Riepilogo sync: {len(active_positions)} posizioni Bybit, {added_count} aggiunte al wrapper")
                
                return {
                    'success': True,
                    'positions_found': len(active_positions),
                    'positions_added': len([t for t in self.active_trades.values() if t.get('bybit_sync')])
                }
            else:
                return {
                    'success': False,
                    'error': f"Errore Bybit: {response.get('retMsg', 'Unknown')}"
                }
                
        except Exception as e:
            print(f"❌ Errore sincronizzazione Bybit: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        
        # Aggiungi questi metodi nel TradingWrapper

    def auto_close_empty_sessions(self):
        """Chiude automaticamente le sessioni senza trade attivi"""
        try:
            if not self.current_session_id:
                return
            
            # Controlla se ci sono trade aperti nella sessione corrente
            trades = trading_db.get_trade_history(self.current_session_id, 1000)
            open_trades = [t for t in trades if t['status'] == 'OPEN']
            
            # Se non ci sono trade aperti e non ci sono posizioni attive
            if not open_trades and not self.active_trades:
                print(f"🔚 Auto-chiusura sessione vuota: {self.current_session_id}")
                self.end_current_session()
                
        except Exception as e:
            print(f"❌ Errore auto-chiusura sessioni: {e}")

    def end_current_session(self, final_balance=None):
        """Termina la sessione corrente"""
        if self.current_session_id:
            try:
                # 🔧 Controlla se ci sono trade aperti prima di chiudere
                open_trades_count = len([t for t in self.active_trades.values() if not t.get('closed', False)])
                
                if open_trades_count > 0:
                    print(f"⚠️ Attenzione: chiusura sessione con {open_trades_count} trade ancora aperti")
                    
                    # Opzionalmente, chiudi automaticamente i trade aperti
                    for trade_id, trade_info in list(self.active_trades.items()):
                        if not trade_info.get('closed', False):
                            try:
                                print(f"🔄 Auto-chiusura trade aperto: {trade_id}")
                                # Nota: qui potresti voler chiamare close_position, ma per sicurezza loggiamo solo
                                trading_db.log_event(
                                    "TRADE_LEFT_OPEN",
                                    "WARNING",
                                    f"Trade {trade_id} rimasto aperto alla chiusura sessione",
                                    {
                                        'trade_id': trade_id,
                                        'symbol': trade_info.get('symbol'),
                                        'side': trade_info.get('side'),
                                        'quantity': trade_info.get('quantity')
                                    },
                                    session_id=self.current_session_id,
                                    severity="WARNING"
                                )
                            except Exception as e:
                                print(f"❌ Errore logging trade aperto: {e}")
                
                # Ottieni saldo finale se non fornito
                if final_balance is None:
                    balance_info = self.get_balance()
                    if balance_info and balance_info.get('success'):
                        final_balance = balance_info.get('total_equity', 0)
                
                # Chiudi la sessione nel database
                trading_db.end_session(self.current_session_id, final_balance)
                
                print(f"🏁 Sessione terminata: {self.current_session_id}")
                
                # Reset session e clear active trades
                old_session = self.current_session_id
                self.current_session_id = None
                self.active_trades.clear()  # Pulisci i trade attivi
                
                return {
                    'success': True,
                    'message': f'Sessione {old_session} terminata',
                    'final_balance': final_balance
                }
                
            except Exception as e:
                print(f"❌ Errore terminazione sessione: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }

    def sync_with_exchange_positions(self):
        """Sincronizza il wrapper con le posizioni reali dell'exchange per crash recovery"""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Sincronizzazione posizioni exchange per recovery...")
            
            # Prima sincronizza con il database
            self.sync_with_database()
            
            # Poi sincronizza con Bybit
            result = self.sync_with_bybit()
            
            if result['success']:
                positions_count = len(self.active_trades)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Sincronizzazione completata: {positions_count} posizioni attive")
                
                # Se non ci sono posizioni attive, considera di chiudere sessioni vuote
                if positions_count == 0:
                    self.auto_close_empty_sessions()
                
                # Log evento
                trading_db.log_event(
                    "EXCHANGE_SYNC_RECOVERY",
                    "RECOVERY",
                    f"Sincronizzazione exchange per recovery: {positions_count} posizioni",
                    {
                        'positions_count': positions_count,
                        'active_trades': list(self.active_trades.keys())
                    },
                    session_id=self.current_session_id
                )
                
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore sincronizzazione: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Eccezione durante sincronizzazione: {e}")
        
    def cleanup_closed_positions(self):
        """Pulisce le posizioni chiuse dal tracking"""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧹 Pulizia posizioni chiuse...")
            
            # Sincronizza con Bybit per vedere le posizioni realmente attive
            sync_result = self.sync_with_bybit()
            
            if not sync_result['success']:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Impossibile verificare posizioni su Bybit")
                return
            
            # Se non ci sono posizioni attive, pulisci tutto
            active_positions_count = len([t for t in self.active_trades.values() if t.get('bybit_sync')])
            
            if active_positions_count == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧹 Nessuna posizione attiva - Pulizia completa")
                self.active_trades.clear()
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 {active_positions_count} posizioni ancora attive")
            
            # Log evento
            trading_db.log_event(
                "POSITIONS_CLEANUP",
                "SYSTEM",
                f"Pulizia posizioni completata: {len(self.active_trades)} rimaste attive",
                {
                    'remaining_positions': len(self.active_trades),
                    'active_trades': list(self.active_trades.keys())
                },
                session_id=self.current_session_id
            )
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Errore pulizia posizioni: {e}")
            
            # Log eccezione
            trading_db.log_event(
                "POSITIONS_CLEANUP_ERROR",
                "ERROR",
                f"Errore pulizia posizioni: {str(e)}",
                {
                    'exception': str(e)
                },
                severity="ERROR",
                session_id=self.current_session_id
            )
    
    def get_positions_summary(self):
        """Ottieni riassunto delle posizioni per debugging"""
        summary = {
            'total_positions': len(self.active_trades),
            'positions_by_symbol': {},
            'positions_by_side': {'Buy': 0, 'Sell': 0},
            'positions_detail': []
        }
        
        for trade_id, trade_info in self.active_trades.items():
            symbol = trade_info['symbol']
            side = trade_info['side']
            
            # Conta per simbolo
            if symbol not in summary['positions_by_symbol']:
                summary['positions_by_symbol'][symbol] = 0
            summary['positions_by_symbol'][symbol] += 1
            
            # Conta per lato
            summary['positions_by_side'][side] += 1
            
            # Dettaglio posizione
            summary['positions_detail'].append({
                'trade_id': trade_id,
                'symbol': symbol,
                'side': side,
                'quantity': trade_info['quantity'],
                'entry_price': trade_info['entry_price'],
                'timestamp': trade_info['timestamp'],
                'is_bybit_sync': trade_info.get('bybit_sync', False)
            })
        
        return summary

# Istanza globale del wrapper
trading_wrapper = TradingWrapper()
