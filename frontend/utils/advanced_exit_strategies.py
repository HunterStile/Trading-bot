"""
Sistema Avanzato di Exit Strategies per Crypto Trading Bot

Questo modulo implementa strategie di uscita avanzate per gestire meglio
i pump&dump tipici delle criptovalute:

1. Multi-Timeframe Exit: Monitoraggio timeframe più piccoli quando prezzo si allontana
2. Trailing Stop Dinamico: Stop più aggressivi quando c'è volatilità alta
3. Quick Exit su spike: Uscite rapide in caso di movimenti anomali
4. Fixed Stop Loss: Stop loss fisso basato sul prezzo di entrata della posizione

Author: Luigi's Trading Bot
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from core.trading_functions import (
    get_kline_data, media_esponenziale, vedi_prezzo_moneta,
    controlla_candele_sopra_ema, controlla_candele_sotto_ema,
    analizza_prezzo_sopra_media
)

class AdvancedExitManager:
    """Gestore delle strategie di uscita avanzate"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_trailing_stops = {}  # {trade_id: trailing_data}
        self.mtf_monitors = {}           # {trade_id: multi_timeframe_data}
        self.fixed_stop_losses = {}      # {trade_id: fixed_stop_data}
        
    def should_use_advanced_exit(self, current_price: float, ema_value: float, 
                               distance_percent: float) -> Dict[str, bool]:
        """
        Determina se usare strategie di uscita avanzate basate sulla distanza dalla EMA
        
        Returns:
            Dict con flags per attivare diverse strategie
        """
        # Soglie per attivare strategie avanzate
        spike_threshold = self.config.get('spike_threshold', 3.0)  # 3% default
        volatile_threshold = self.config.get('volatile_threshold', 5.0)  # 5% default
        
        abs_distance = abs(distance_percent)
        
        return {
            'use_multi_timeframe': abs_distance >= spike_threshold,
            'use_dynamic_trailing': abs_distance >= spike_threshold,
            'use_quick_exit': abs_distance >= volatile_threshold,
            'use_fixed_stop_loss': True  # Fixed stop loss è sempre attivo se abilitato
        }
    
    def analyze_multi_timeframe_exit(self, trade_id: str, trade_info: Dict, 
                                   bot_status: Dict, market_data: Dict) -> Dict[str, Any]:
        """
        Implementa Multi-Timeframe Exit Strategy
        
        Quando il prezzo si allontana dalla EMA oltre soglia, monitora timeframe minore.
        Se anche una candela va contro trend sul timeframe minore, chiudi.
        """
        try:
            symbol = trade_info.get('symbol', bot_status['symbol'])
            current_interval = bot_status['interval']
            
            # Configura timeframe più piccolo
            smaller_intervals = self._get_smaller_interval(current_interval)
            if not smaller_intervals:
                return {'should_close': False, 'reason': 'No smaller timeframe available'}
            
            smaller_interval = smaller_intervals[0]  # Prendi il più piccolo disponibile
            
            print(f"[MTF] Attivo Multi-Timeframe Exit per {symbol}")
            print(f"[MTF] Timeframe principale: {current_interval}m, Timeframe controllo: {smaller_interval}m")
            
            # Analizza timeframe più piccolo
            mtf_analysis = self._analyze_smaller_timeframe(
                symbol, smaller_interval, bot_status, trade_info['side']
            )
            
            if not mtf_analysis['valid']:
                return {'should_close': False, 'reason': 'MTF analysis failed'}
            
            # Logica decisionale
            trade_side = trade_info['side'].upper()
            
            if trade_side == 'BUY':  # Long position
                # Per long: chiudi se anche una candela chiude sotto EMA sul timeframe minore
                candles_below = mtf_analysis['candles_below']
                should_close = candles_below >= 1
                
                return {
                    'should_close': should_close,
                    'reason': f'MTF: {candles_below} candela(e) sotto EMA su {smaller_interval}m',
                    'mtf_data': mtf_analysis
                }
                
            elif trade_side == 'SELL':  # Short position  
                # Per short: chiudi se anche una candela chiude sopra EMA sul timeframe minore
                candles_above = mtf_analysis['candles_above']
                should_close = candles_above >= 1
                
                return {
                    'should_close': should_close,
                    'reason': f'MTF: {candles_above} candela(e) sopra EMA su {smaller_interval}m',
                    'mtf_data': mtf_analysis
                }
            
        except Exception as e:
            print(f"[MTF] Errore Multi-Timeframe Exit: {e}")
            return {'should_close': False, 'reason': f'MTF Error: {e}'}
    
    def analyze_dynamic_trailing_stop(self, trade_id: str, trade_info: Dict, 
                                     current_price: float, distance_percent: float) -> Dict[str, Any]:
        """
        Implementa Dynamic Trailing Stop
        
        Quando prezzo si allontana molto dalla media, attiva trailing stop più stretto
        che segue il prezzo e si attiva su retrace.
        """
        try:
            # Inizializza trailing stop se non esiste
            if trade_id not in self.active_trailing_stops:
                self._initialize_trailing_stop(trade_id, trade_info, current_price)
            
            trailing_data = self.active_trailing_stops[trade_id]
            trade_side = trade_info['side'].upper()
            
            # Aggiorna trailing stop
            self._update_trailing_stop(trailing_data, current_price, trade_side)
            
            # Controlla se deve chiudere
            should_close, reason = self._check_trailing_stop_trigger(
                trailing_data, current_price, trade_side, distance_percent
            )
            
            return {
                'should_close': should_close,
                'reason': reason,
                'trailing_data': trailing_data.copy()
            }
            
        except Exception as e:
            print(f"[DTS] Errore Dynamic Trailing Stop: {e}")
            return {'should_close': False, 'reason': f'DTS Error: {e}'}
    
    def analyze_quick_exit_on_spike(self, trade_info: Dict, market_data: Dict, 
                                   bot_status: Dict) -> Dict[str, Any]:
        """
        Implementa Quick Exit su spike anomali
        
        Per movimenti molto violenti (>5% dalla EMA), esci immediatamente
        senza aspettare le candele standard.
        """
        try:
            abs_distance = abs(market_data['distance_percent'])
            spike_threshold = self.config.get('volatile_threshold', 5.0)
            
            if abs_distance < spike_threshold:
                return {'should_close': False, 'reason': 'Spike threshold not reached'}
            
            trade_side = trade_info['side'].upper()
            
            # Per LONG: esci se prezzo crolla sotto EMA di più del 5%
            if trade_side == 'BUY' and market_data['distance_percent'] <= -spike_threshold:
                return {
                    'should_close': True,
                    'reason': f'SPIKE EXIT: Prezzo crollato {market_data["distance_percent"]:.2f}% sotto EMA'
                }
            
            # Per SHORT: esci se prezzo esplode sopra EMA di più del 5%  
            elif trade_side == 'SELL' and market_data['distance_percent'] >= spike_threshold:
                return {
                    'should_close': True,
                    'reason': f'SPIKE EXIT: Prezzo esploso {market_data["distance_percent"]:.2f}% sopra EMA'
                }
            
            return {'should_close': False, 'reason': 'Spike in favorable direction'}
            
        except Exception as e:
            print(f"[SPIKE] Errore Quick Exit: {e}")
            return {'should_close': False, 'reason': f'Spike Error: {e}'}
    
    def analyze_fixed_stop_loss(self, trade_id: str, trade_info: Dict, 
                               current_price: float) -> Dict[str, Any]:
        """
        Implementa Fixed Stop Loss Strategy
        
        Stop loss fisso basato sul prezzo di entrata della posizione.
        Viene calcolato una sola volta all'apertura del trade e rimane fisso.
        """
        try:
            # Inizializza fixed stop loss se non esiste
            if trade_id not in self.fixed_stop_losses:
                self._initialize_fixed_stop_loss(trade_id, trade_info)
            
            fixed_stop_data = self.fixed_stop_losses[trade_id]
            trade_side = trade_info['side'].upper()
            stop_price = fixed_stop_data['stop_price']
            entry_price = fixed_stop_data['entry_price']
            stop_loss_percent = fixed_stop_data['stop_loss_percent']
            
            # Controlla se il prezzo corrente ha attivato lo stop loss
            should_close = False
            reason = ""
            
            if trade_side == 'BUY':  # Long position
                # Per long: chiudi se prezzo scende sotto lo stop loss
                if current_price <= stop_price:
                    should_close = True
                    loss_percent = ((current_price - entry_price) / entry_price) * 100
                    reason = f"FIXED STOP LOSS LONG: ${current_price:.4f} <= ${stop_price:.4f} (Perdita: {loss_percent:.2f}%)"
                else:
                    reason = f"Stop Loss LONG non attivato: ${current_price:.4f} > ${stop_price:.4f}"
            
            elif trade_side == 'SELL':  # Short position
                # Per short: chiudi se prezzo sale sopra lo stop loss
                if current_price >= stop_price:
                    should_close = True
                    loss_percent = ((entry_price - current_price) / entry_price) * 100
                    reason = f"FIXED STOP LOSS SHORT: ${current_price:.4f} >= ${stop_price:.4f} (Perdita: {loss_percent:.2f}%)"
                else:
                    reason = f"Stop Loss SHORT non attivato: ${current_price:.4f} < ${stop_price:.4f}"
            
            return {
                'should_close': should_close,
                'reason': reason,
                'fixed_stop_data': {
                    'entry_price': entry_price,
                    'stop_price': stop_price,
                    'stop_loss_percent': stop_loss_percent,
                    'current_distance': abs((current_price - stop_price) / stop_price * 100)
                }
            }
            
        except Exception as e:
            print(f"[FSL] Errore Fixed Stop Loss: {e}")
            return {'should_close': False, 'reason': f'FSL Error: {e}'}
    
    def _get_smaller_interval(self, current_interval: int) -> List[int]:
        """Restituisce timeframe più piccoli disponibili"""
        # Mappa timeframe disponibili (in minuti)
        available_intervals = [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440]
        
        # Filtra solo quelli più piccoli di quello corrente
        smaller = [i for i in available_intervals if i < current_interval]
        
        # Ordina dal più piccolo al più grande
        return sorted(smaller)
    
    def _analyze_smaller_timeframe(self, symbol: str, interval: int, 
                                  bot_status: Dict, trade_side: str) -> Dict[str, Any]:
        """Analizza un timeframe più piccolo per Multi-Timeframe Exit"""
        try:
            # Usa le funzioni esistenti del bot per analisi
            candles_above_result = controlla_candele_sopra_ema(
                'linear', symbol, interval, bot_status['ema_period']
            )
            candles_below_result = controlla_candele_sotto_ema(
                'linear', symbol, interval, bot_status['ema_period'] 
            )
            
            if not candles_above_result or not candles_below_result:
                return {'valid': False}
            
            return {
                'valid': True,
                'interval': interval,
                'candles_above': candles_above_result[0],
                'candles_below': candles_below_result[0],
                'current_price': candles_above_result[1],  # Same price from both functions
                'distance_percent': candles_above_result[2],
                'timestamp': candles_above_result[3]
            }
            
        except Exception as e:
            print(f"[MTF] Errore analisi timeframe {interval}m: {e}")
            return {'valid': False}
    
    def _initialize_trailing_stop(self, trade_id: str, trade_info: Dict, current_price: float):
        """Inizializza trailing stop per una posizione"""
        trade_side = trade_info['side'].upper()
        
        # Percentuale di trailing stop basata sulla configurazione
        trailing_percent = self.config.get('trailing_stop_percent', 2.0)  # 2% default
        
        if trade_side == 'BUY':  # Long
            # Per long, trailing stop sotto il prezzo
            stop_price = current_price * (1 - trailing_percent / 100)
            highest_price = current_price
        else:  # Short
            # Per short, trailing stop sopra il prezzo
            stop_price = current_price * (1 + trailing_percent / 100)
            lowest_price = current_price
        
        self.active_trailing_stops[trade_id] = {
            'trade_side': trade_side,
            'initial_price': current_price,
            'stop_price': stop_price,
            'trailing_percent': trailing_percent,
            'highest_price': current_price if trade_side == 'BUY' else None,
            'lowest_price': current_price if trade_side == 'SELL' else None,
            'last_update': datetime.now()
        }
        
        print(f"[DTS] Trailing stop inizializzato per {trade_id} ({trade_side})")
        print(f"[DTS] Prezzo: ${current_price:.4f}, Stop: ${stop_price:.4f}")
    
    def _update_trailing_stop(self, trailing_data: Dict, current_price: float, trade_side: str):
        """Aggiorna trailing stop seguendo il prezzo"""
        trailing_percent = trailing_data['trailing_percent']
        
        if trade_side == 'BUY':  # Long position
            # Aggiorna highest price se necessario
            if current_price > trailing_data['highest_price']:
                trailing_data['highest_price'] = current_price
                # Aggiorna stop price (sale sempre)
                new_stop = current_price * (1 - trailing_percent / 100)
                if new_stop > trailing_data['stop_price']:
                    trailing_data['stop_price'] = new_stop
                    print(f"[DTS] Trailing stop aggiornato: ${new_stop:.4f}")
        
        else:  # Short position
            # Aggiorna lowest price se necessario  
            if current_price < trailing_data['lowest_price']:
                trailing_data['lowest_price'] = current_price
                # Aggiorna stop price (scende sempre)
                new_stop = current_price * (1 + trailing_percent / 100)
                if new_stop < trailing_data['stop_price']:
                    trailing_data['stop_price'] = new_stop
                    print(f"[DTS] Trailing stop aggiornato: ${new_stop:.4f}")
        
        trailing_data['last_update'] = datetime.now()
    
    def _check_trailing_stop_trigger(self, trailing_data: Dict, current_price: float, 
                                   trade_side: str, distance_percent: float) -> Tuple[bool, str]:
        """Controlla se il trailing stop deve essere attivato"""
        stop_price = trailing_data['stop_price']
        
        # Attiva trailing stop solo se distanza dalla EMA è significativa
        min_distance_for_trailing = self.config.get('min_distance_for_trailing', 2.0)
        
        if abs(distance_percent) < min_distance_for_trailing:
            return False, "Distanza insufficiente per trailing stop"
        
        if trade_side == 'BUY':  # Long
            # Chiudi se prezzo scende sotto stop
            if current_price <= stop_price:
                return True, f"Trailing Stop LONG: ${current_price:.4f} <= ${stop_price:.4f}"
        
        else:  # Short
            # Chiudi se prezzo sale sopra stop
            if current_price >= stop_price:
                return True, f"Trailing Stop SHORT: ${current_price:.4f} >= ${stop_price:.4f}"
        
        return False, f"Trailing stop non attivato (${current_price:.4f} vs ${stop_price:.4f})"
    
    def _initialize_fixed_stop_loss(self, trade_id: str, trade_info: Dict):
        """Inizializza fixed stop loss per una posizione"""
        trade_side = trade_info['side'].upper()
        entry_price = float(trade_info.get('entry_price', 0))
        
        # Percentuale di stop loss basata sulla configurazione
        stop_loss_percent = self.config.get('stop_loss_percent', 3.0)  # 3% default
        
        if entry_price <= 0:
            print(f"[FSL] Errore: prezzo di entrata non valido per {trade_id}: {entry_price}")
            return
        
        if trade_side == 'BUY':  # Long position
            # Per long: stop loss sotto il prezzo di entrata
            stop_price = entry_price * (1 - stop_loss_percent / 100)
        else:  # Short position
            # Per short: stop loss sopra il prezzo di entrata
            stop_price = entry_price * (1 + stop_loss_percent / 100)
        
        self.fixed_stop_losses[trade_id] = {
            'trade_side': trade_side,
            'entry_price': entry_price,
            'stop_price': stop_price,
            'stop_loss_percent': stop_loss_percent,
            'created_at': datetime.now()
        }
        
        print(f"[FSL] Fixed Stop Loss inizializzato per {trade_id} ({trade_side})")
        print(f"[FSL] Entry: ${entry_price:.4f}, Stop Loss: ${stop_price:.4f} ({stop_loss_percent}%)")
    
    def cleanup_trade_data(self, trade_id: str):
        """Pulisce dati di trailing stop e fixed stop loss per trade chiuso"""
        if trade_id in self.active_trailing_stops:
            del self.active_trailing_stops[trade_id]
        if trade_id in self.mtf_monitors:
            del self.mtf_monitors[trade_id]
        if trade_id in self.fixed_stop_losses:
            del self.fixed_stop_losses[trade_id]
        
        print(f"[EXIT] Cleanup completato per trade {trade_id}")


def create_advanced_exit_manager(bot_config: Dict[str, Any]) -> AdvancedExitManager:
    """Factory per creare il manager delle strategie di uscita"""
    
    # Configurazione default per strategie avanzate
    exit_config = {
        # Multi-Timeframe Exit
        'spike_threshold': bot_config.get('spike_threshold', 3.0),  # % dalla EMA per attivare MTF
        'mtf_candles_trigger': bot_config.get('mtf_candles_trigger', 1),  # candele needed su timeframe minore
        
        # Dynamic Trailing Stop
        'trailing_stop_percent': bot_config.get('trailing_stop_percent', 2.0),  # % trailing
        'min_distance_for_trailing': bot_config.get('min_distance_for_trailing', 2.0),  # min distance per attivare
        
        # Quick Exit su spike estremi
        'volatile_threshold': bot_config.get('volatile_threshold', 5.0),  # % per quick exit
        
        # Fixed Stop Loss
        'stop_loss_percent': bot_config.get('stop_loss_percent', 3.0),  # % stop loss fisso
        
        # Configurazioni generali
        'enable_multi_timeframe': bot_config.get('enable_multi_timeframe', True),
        'enable_dynamic_trailing': bot_config.get('enable_dynamic_trailing', True), 
        'enable_quick_exit': bot_config.get('enable_quick_exit', True),
        'enable_fixed_stop_loss': bot_config.get('enable_fixed_stop_loss', True)
    }
    
    return AdvancedExitManager(exit_config)


def analyze_advanced_exit_conditions(exit_manager: AdvancedExitManager, trade_id: str, 
                                    trade_info: Dict, bot_status: Dict, 
                                    market_data: Dict) -> Dict[str, Any]:
    """
    Analizza tutte le condizioni di uscita avanzate per una posizione
    
    Args:
        exit_manager: Gestore strategie uscita
        trade_id: ID del trade
        trade_info: Informazioni del trade
        bot_status: Configurazione bot
        market_data: Dati mercato correnti
    
    Returns:
        Dict con risultato analisi e motivo eventuale chiusura
    """
    try:
        current_price = market_data['current_price']
        ema_value = market_data['ema_value'] 
        distance_percent = market_data['distance_percent']
        
        print(f"[EXIT] Analisi avanzata per {trade_id} - Prezzo: ${current_price:.4f}")
        print(f"[EXIT] Distanza da EMA: {distance_percent:+.2f}%")
        
        # Determina quali strategie usare
        strategy_flags = exit_manager.should_use_advanced_exit(
            current_price, ema_value, distance_percent
        )
        
        print(f"[EXIT] Strategie attive: {[k for k, v in strategy_flags.items() if v]}")
        
        # 1. Quick Exit su spike estremi (priorità massima)
        if (strategy_flags['use_quick_exit'] and 
            exit_manager.config.get('enable_quick_exit', True)):
            
            spike_result = exit_manager.analyze_quick_exit_on_spike(
                trade_info, market_data, bot_status
            )
            
            if spike_result['should_close']:
                return {
                    'should_close': True,
                    'exit_type': 'QUICK_EXIT_SPIKE',
                    'reason': spike_result['reason'],
                    'priority': 'HIGH'
                }
        
        # 2. Multi-Timeframe Exit (priorità alta)
        if (strategy_flags['use_multi_timeframe'] and 
            exit_manager.config.get('enable_multi_timeframe', True)):
            
            mtf_result = exit_manager.analyze_multi_timeframe_exit(
                trade_id, trade_info, bot_status, market_data
            )
            
            if mtf_result['should_close']:
                return {
                    'should_close': True,
                    'exit_type': 'MULTI_TIMEFRAME_EXIT',
                    'reason': mtf_result['reason'],
                    'priority': 'HIGH',
                    'mtf_data': mtf_result.get('mtf_data')
                }
        
        # 3. Fixed Stop Loss (priorità alta - sempre controllato se abilitato)
        if exit_manager.config.get('enable_fixed_stop_loss', True):
            
            fixed_sl_result = exit_manager.analyze_fixed_stop_loss(
                trade_id, trade_info, current_price
            )
            
            if fixed_sl_result['should_close']:
                return {
                    'should_close': True,
                    'exit_type': 'FIXED_STOP_LOSS',
                    'reason': fixed_sl_result['reason'],
                    'priority': 'HIGH',
                    'fixed_stop_data': fixed_sl_result.get('fixed_stop_data')
                }
        
        # 4. Dynamic Trailing Stop (priorità media)
        if (strategy_flags['use_dynamic_trailing'] and 
            exit_manager.config.get('enable_dynamic_trailing', True)):
            
            trailing_result = exit_manager.analyze_dynamic_trailing_stop(
                trade_id, trade_info, current_price, distance_percent
            )
            
            if trailing_result['should_close']:
                return {
                    'should_close': True,
                    'exit_type': 'DYNAMIC_TRAILING_STOP', 
                    'reason': trailing_result['reason'],
                    'priority': 'MEDIUM',
                    'trailing_data': trailing_result.get('trailing_data')
                }
        
        # Nessuna condizione di uscita avanzata attivata
        return {
            'should_close': False,
            'exit_type': 'NONE',
            'reason': 'Nessuna condizione avanzata attivata',
            'strategy_flags': strategy_flags
        }
        
    except Exception as e:
        print(f"[EXIT] Errore analisi condizioni avanzate: {e}")
        return {
            'should_close': False,
            'exit_type': 'ERROR',
            'reason': f'Errore analisi: {e}'
        }


# Funzioni helper per intervalli timeframe
def get_interval_in_minutes(interval) -> int:
    """Converte intervallo in minuti"""
    if isinstance(interval, str):
        if interval == 'D':
            return 1440
        elif interval == 'W': 
            return 10080
        elif interval == 'M':
            return 43200
        else:
            return int(interval)
    return int(interval)


def get_bybit_interval_format(minutes: int) -> str:
    """Converte minuti nel formato intervallo Bybit"""
    interval_mapping = {
        1: '1',
        3: '3', 
        5: '5',
        15: '15',
        30: '30',
        60: '60',
        120: '120',
        240: '240',
        360: '360',
        720: '720',
        1440: 'D'
    }
    
    return interval_mapping.get(minutes, str(minutes))


# Esempi di configurazione per il bot
EXAMPLE_ADVANCED_EXIT_CONFIG = {
    # Multi-Timeframe Exit Settings
    'enable_multi_timeframe': True,
    'spike_threshold': 3.0,           # % dalla EMA per attivare MTF monitoring
    'mtf_candles_trigger': 1,         # Candele necessarie su timeframe minore
    
    # Dynamic Trailing Stop Settings  
    'enable_dynamic_trailing': True,
    'trailing_stop_percent': 2.0,     # % trailing stop
    'min_distance_for_trailing': 2.0, # Distanza minima EMA per attivare trailing
    
    # Quick Exit Settings
    'enable_quick_exit': True,
    'volatile_threshold': 5.0,        # % per quick exit immediato
    
    # Fixed Stop Loss Settings
    'enable_fixed_stop_loss': True,
    'stop_loss_percent': 3.0,         # % stop loss fisso dal prezzo di entrata
    
    # Configurazioni generali
    'debug_mode': True               # Logging dettagliato
}
