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
bot_path = Path(__file__).parent.parent
sys.path.append(str(bot_path))

# Import database
from utils.database import trading_db

# Import funzioni originali del bot
try:
    from trading_functions import (
        bot_open_position as _original_open_position,
        bot_trailing_stop as _original_trailing_stop,
        mostra_saldo as _original_show_balance,
        vedi_prezzo_moneta as _original_get_price
    )
    from config import api, api_sec
except ImportError as e:
    print(f"Errore nell'importazione delle funzioni del trading bot: {e}")
    _original_open_position = None
    _original_trailing_stop = None
    _original_show_balance = None
    _original_get_price = None

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
        if not _original_open_position:
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
                # La funzione originale probabilmente non restituisce nulla, ma fa il processo completo
                _original_open_position(
                    categoria,
                    symbol,
                    periodo_ema,
                    intervallo,
                    quantity,
                    candele,
                    lunghezza,
                    operazione
                )
                
                # Se arriviamo qui senza eccezioni, assumiamo il successo
                result = {
                    'success': True,
                    'entry_price': price if price else 0,
                    'order_id': f"BOT_{symbol}_{int(time.time())}"
                }
            except Exception as e:
                result = {
                    'success': False,
                    'error': str(e)
                }
            
            if result and result.get('success'):
                # Salva trade nel database
                trade_id = trading_db.add_trade(
                    session_id=self.current_session_id,
                    symbol=symbol,
                    side=side.upper(),
                    entry_price=result.get('entry_price', price),
                    quantity=quantity,
                    strategy_signal=kwargs.get('strategy_signal', 'MANUAL')
                )
                
                # Memorizza il trade attivo
                self.active_trades[trade_id] = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
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
                        'quantity': quantity,
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
            
            # CHIUSURA REALE SU BYBIT
            success_bybit = False
            try:
                # Import delle API Bybit
                from pybit.unified_trading import HTTP
                
                session = HTTP(
                    testnet=False,
                    api_key=api,
                    api_secret=api_sec,
                )
                
                symbol = trade_info['symbol']
                quantity = trade_info['quantity']
                side = trade_info['side']
                
                # Per chiudere una posizione, devi fare l'ordine opposto
                close_side = 'Sell' if side == 'Buy' else 'Buy'
                
                print(f"🔄 Chiusura reale Bybit: {close_side} {quantity} {symbol} @ market price")
                
                # Chiudi con ordine market opposto
                response = session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=close_side,
                    orderType="Market",
                    qty=str(quantity),
                    reduceOnly=True  # Importante: solo per chiudere posizioni esistenti
                )
                
                if response['retCode'] == 0:
                    print(f"✅ Posizione chiusa su Bybit: {response}")
                    success_bybit = True
                    order_id = response['result']['orderId']
                else:
                    print(f"❌ Errore chiusura Bybit: {response}")
                    return {
                        'success': False,
                        'error': f'Errore Bybit: {response.get("retMsg", "Unknown")}'
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
                trading_db.close_trade(trade_id, price, fee)
                
                # Rimuovi dai trade attivi
                del self.active_trades[trade_id]
                
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
        if not _original_trailing_stop:
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
            result = _original_trailing_stop(symbol, **kwargs)
            
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
        if not _original_show_balance:
            return {
                'success': False,
                'error': 'Funzione saldo non disponibile'
            }
        
        try:
            result = _original_show_balance()
            
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
        if not _original_get_price:
            return None
        
        try:
            price = _original_get_price('linear', symbol)
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
