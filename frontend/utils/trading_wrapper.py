"""
Wrapper per le funzioni di trading che integra il salvataggio nel database
"""

import sys
import os
import time
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
    from trading_functions import (
        bot_open_position,
        bot_trailing_stop,
        mostra_saldo,
        vedi_prezzo_moneta
    )
    from config import api, api_sec
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
        """Imposta la sessione corrente"""
        self.current_session_id = session_id
    
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
                from trading_functions import compra_moneta_bybit_by_quantita, vendi_moneta_bybit_by_quantita
                
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
                
                # Memorizza il trade attivo
                self.active_trades[trade_id] = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': actual_quantity,  # Quantità in monete, non USD
                    'entry_price': result.get('entry_price', price),
                    'bybit_order_id': result.get('order_id'),
                    'timestamp': datetime.now().isoformat()
                }
                
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
    
    def close_position(self, trade_id, price=None, reason="MANUAL", **kwargs):
        """
        Chiude una posizione e aggiorna il database
        
        Args:
            trade_id: ID del trade da chiudere
            price: Prezzo di chiusura (None per market price)
            reason: Motivo della chiusura
            **kwargs: Altri parametri
        """
        if trade_id not in self.active_trades:
            return {
                'success': False,
                'error': f'Trade {trade_id} non trovato nei trade attivi'
            }
        
        trade_info = self.active_trades[trade_id]
        
        try:
            # Log tentativo chiusura
            trading_db.log_event(
                "POSITION_CLOSE_ATTEMPT",
                "TRADING",
                f"Tentativo chiusura posizione: {trade_id}",
                {
                    'trade_id': trade_id,
                    'reason': reason,
                    'close_price': price
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
                # Import delle funzioni originali
                from trading_functions import chiudi_operazione_long, chiudi_operazione_short
                
                symbol = trade_info['symbol']
                quantity = trade_info['quantity']
                side = trade_info['side']
                
                print(f"🔄 Chiusura reale Bybit usando funzioni originali: {side} {quantity} {symbol}")
                
                # Usa le funzioni originali per chiudere
                if side == 'Buy':
                    # LONG -> chiudi con SELL
                    print(f"🔴 Chiusura LONG usando chiudi_operazione_long")
                    chiudi_operazione_long("linear", symbol, quantity)
                elif side == 'Sell':
                    # SHORT -> chiudi con BUY  
                    print(f"🔵 Chiusura SHORT usando chiudi_operazione_short")
                    chiudi_operazione_short("linear", symbol, quantity)
                
                print(f"✅ Posizione chiusa su Bybit con funzioni originali")
                success_bybit = True
                    
            except Exception as e:
                print(f"❌ Eccezione durante chiusura Bybit: {e}")
                return {
                    'success': False,
                    'error': f'Eccezione Bybit: {str(e)}'
                }
            
            # Se la chiusura Bybit è andata bene, aggiorna il database
            if success_bybit:
                print(f"🔍 DEBUG: Aggiornamento database per trade {trade_id}")
                
                # Calcola fee approssimativa (0.1%)
                fee = (price * trade_info['quantity']) * 0.001
                
                print(f"🔍 DEBUG: Chiamo trading_db.close_trade({trade_id}, {price}, {fee})")
                
                # Aggiorna il trade nel database
                trading_db.close_trade(trade_id, price, fee)
                
                print(f"🔍 DEBUG: Rimuovo trade {trade_id} da active_trades")
                print(f"🔍 DEBUG: Active trades prima: {list(self.active_trades.keys())}")
                
                # Rimuovi dai trade attivi
                del self.active_trades[trade_id]
                
                print(f"🔍 DEBUG: Active trades dopo: {list(self.active_trades.keys())}")
                
                # Log successo
                trading_db.log_event(
                    "POSITION_CLOSED",
                    "TRADING",
                    f"Posizione chiusa con successo: {trade_id}",
                    {
                        'trade_id': trade_id,
                        'close_price': price,
                        'reason': reason,
                        'fee': fee
                    },
                    session_id=self.current_session_id
                )
                
                return {
                    'success': True,
                    'trade_id': trade_id,
                    'message': f'Posizione {trade_id} chiusa',
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
                    'trade_id': trade_id,
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
                # Carica trade aperti dalla sessione corrente
                trades = trading_db.get_trade_history(self.current_session_id, 100)
                open_trades = [t for t in trades if t['status'] == 'OPEN']
                
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
                    
                    # Crea un trade_id fittizio per la posizione Bybit
                    trade_id = f"BYBIT_{symbol}_{side}_{int(time.time())}"
                    
                    # Aggiungi al wrapper se non esiste già
                    existing = any(
                        trade['symbol'] == symbol and trade['side'] == side 
                        for trade in self.active_trades.values()
                    )
                    
                    if not existing:
                        self.active_trades[trade_id] = {
                            'symbol': symbol,
                            'side': side,
                            'quantity': size,
                            'entry_price': avg_price,
                            'timestamp': datetime.now().isoformat(),
                            'bybit_sync': True  # Flag per indicare che è sincronizzato da Bybit
                        }
                        
                        print(f"✅ Aggiunta posizione Bybit: {trade_id} - {side} {size} {symbol}")
                        
                        # Registra nel database se c'è una sessione attiva
                        if self.current_session_id:
                            db_trade_id = trading_db.add_trade(
                                session_id=self.current_session_id,
                                symbol=symbol,
                                side=side.upper(),
                                entry_price=avg_price,
                                quantity=size,
                                strategy_signal="BYBIT_SYNC"
                            )
                            
                            # Aggiorna l'ID nel wrapper
                            self.active_trades[db_trade_id] = self.active_trades.pop(trade_id)
                            print(f"📝 Posizione registrata nel database: {db_trade_id}")
                
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

# Istanza globale del wrapper
trading_wrapper = TradingWrapper()
