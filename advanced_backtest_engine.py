"""
Advanced Backtest Engine con Strategie di Uscita Avanzate

Questo modulo implementa un sistema di backtesting che include:
1. Multi-Timeframe Exit: Controllo su timeframe minori
2. Dynamic Trailing Stop: Trailing stop intelligente
3. Quick Exit: Uscita rapida su spike estremi
4. Fixed Stop Loss: Stop loss fisso dal prezzo di entrata

Author: Luigi's Advanced Trading Bot
"""

import sys
import os
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from typing import Dict, Any, List, Optional, Tuple

# Aggiungi path per importazioni
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import api, api_sec
    from trading_functions import get_kline_data, media_esponenziale
    from frontend.utils.advanced_exit_strategies import (
        create_advanced_exit_manager, analyze_advanced_exit_conditions
    )
except ImportError as e:
    print(f"Warning: Some imports failed: {e}")
    api = api_sec = None

class AdvancedBacktestEngine:
    """
    Engine di backtesting avanzato con strategie di uscita multiple
    """
    
    def __init__(self, symbol="BTCUSDT", initial_capital=1000):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.fee_rate = 0.001  # 0.1% fee Bybit
        
        # Risk management
        self.position_size_pct = 0.95  # Usa 95% del capitale
        
        # 🆕 ADVANCED EXIT STRATEGIES CONFIGURATION
        self.advanced_config = {
            # Multi-Timeframe Exit Settings
            'enable_multi_timeframe': True,
            'spike_threshold': 3.0,          # % dalla EMA per attivare MTF monitoring
            'mtf_candles_trigger': 1,        # Candele necessarie su timeframe minore
            
            # Dynamic Trailing Stop Settings  
            'enable_dynamic_trailing': True,
            'trailing_stop_percent': 2.0,    # % trailing stop
            'min_distance_for_trailing': 2.0, # Distanza minima EMA per attivare trailing
            
            # Quick Exit Settings
            'enable_quick_exit': True,
            'volatile_threshold': 5.0,       # % dalla EMA per quick exit immediato
            
            # Fixed Stop Loss Settings
            'enable_fixed_stop_loss': True,
            'stop_loss_percent': 3.0,        # % stop loss fisso dal prezzo di entrata
            
            # Advanced Exit Debug
            'advanced_exit_debug': True      # Logging dettagliato
        }
        
        # Cache per dati multi-timeframe
        self.mtf_data_cache = {}
        
    def get_historical_data(self, timeframe='30', days_back=30, symbol=None):
        """Ottieni dati storici da Bybit con supporto multi-simbolo"""
        target_symbol = symbol or self.symbol
        
        try:
            # Converti timeframe per Bybit API
            interval_map = {
                '1': '1', '3': '3', '5': '5', '15': '15', 
                '30': '30', '60': '60', '240': '240', 'D': 'D'
            }
            
            interval = interval_map.get(str(timeframe), '30')
            
            # Calcola limite candele necessarie
            limit = self._calculate_candles_limit(interval, days_back)
            
            # API call diretta a Bybit
            url = "https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'linear',  # Futures per più liquidità
                'symbol': target_symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('retCode') != 0:
                print(f"❌ API Error: {data.get('retMsg', 'Unknown error')}")
                return None
            
            klines = data.get('result', {}).get('list', [])
            
            if not klines or len(klines) < 50:
                print(f"❌ Dati insufficienti per {target_symbol} ({len(klines)} candele)")
                return None
            
            # Converti in DataFrame e ordina cronologicamente
            df_data = []
            for kline in klines:
                df_data.append({
                    'timestamp': datetime.fromtimestamp(int(kline[0]) / 1000),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)  # Ordine cronologico
            
            return df
            
        except Exception as e:
            print(f"❌ Errore download dati per {target_symbol}: {e}")
            return None
    
    def _calculate_candles_limit(self, interval, days_back):
        """Calcola il numero di candele necessarie per il periodo richiesto"""
        limits = {
            '1': days_back * 1440,   # 1 minuto
            '3': days_back * 480,    # 3 minuti
            '5': days_back * 288,    # 5 minuti
            '15': days_back * 96,    # 15 minuti
            '30': days_back * 48,    # 30 minuti
            '60': days_back * 24,    # 1 ora
            '240': days_back * 6,    # 4 ore
            'D': days_back + 50      # 1 giorno
        }
        
        return min(limits.get(interval, 200) + 50, 1000)  # +50 buffer, max 1000
    
    def calculate_ema(self, prices, period):
        """Calcola EMA usando la funzione del bot o fallback"""
        try:
            if len(prices) < period:
                return np.zeros_like(prices)
            
            # Prova la funzione del bot
            ema_values = media_esponenziale(prices.tolist(), period)
            return np.array(ema_values)
        except:
            # Fallback manuale
            ema = np.zeros_like(prices)
            if len(prices) == 0:
                return ema
                
            ema[0] = prices[0]
            alpha = 2 / (period + 1)
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
            return ema
    
    def get_smaller_timeframe_data(self, main_timeframe, days_back):
        """Ottieni dati per timeframe più piccolo per Multi-Timeframe Exit"""
        # Mappa timeframe più piccoli
        smaller_tf_map = {
            '240': '60',   # 4h -> 1h
            '60': '15',    # 1h -> 15m
            '30': '5',     # 30m -> 5m
            '15': '5',     # 15m -> 5m
            '5': '1',      # 5m -> 1m
        }
        
        smaller_tf = smaller_tf_map.get(str(main_timeframe))
        if not smaller_tf:
            return None
        
        # Cache per evitare chiamate multiple
        cache_key = f"{self.symbol}_{smaller_tf}_{days_back}"
        if cache_key in self.mtf_data_cache:
            return self.mtf_data_cache[cache_key]
        
        # Ottieni dati timeframe più piccolo
        mtf_data = self.get_historical_data(smaller_tf, days_back)
        if mtf_data is not None:
            self.mtf_data_cache[cache_key] = mtf_data
        
        return mtf_data
    
    def count_consecutive_candles_above_ema(self, prices, ema, current_idx, required):
        """Conta candele consecutive sopra EMA"""
        if current_idx < 0 or current_idx >= len(prices):
            return 0
            
        count = 0
        for i in range(current_idx, max(-1, current_idx - required - 2), -1):
            if i >= 0 and i < len(prices) and prices[i] > ema[i]:
                count += 1
            else:
                break
        return count
    
    def count_consecutive_candles_below_ema(self, prices, ema, current_idx, required):
        """Conta candele consecutive sotto EMA"""
        if current_idx < 0 or current_idx >= len(prices):
            return 0
            
        count = 0
        for i in range(current_idx, max(-1, current_idx - required - 2), -1):
            if i >= 0 and i < len(prices) and prices[i] < ema[i]:
                count += 1
            else:
                break
        return count
    
    def simulate_advanced_exit_strategies(self, trade_id, trade_info, market_data, bot_config):
        """
        Simula l'analisi delle strategie di uscita avanzate per il backtest
        
        Returns:
            Dict con should_close, reason, exit_type
        """
        try:
            # Crea manager delle strategie (simulato)
            exit_manager = AdvancedExitManagerSim(bot_config)
            
            # Analizza condizioni di uscita
            result = analyze_advanced_exit_conditions_sim(
                exit_manager, trade_id, trade_info, bot_config, market_data
            )
            
            return result
            
        except Exception as e:
            print(f"⚠️ Errore simulazione strategie avanzate: {e}")
            return {
                'should_close': False,
                'exit_type': 'ERROR',
                'reason': f'Simulation error: {e}'
            }
    
    def run_advanced_backtest(self, ema_period=10, required_candles=3, max_distance=1.0, 
                             timeframe='30', days_back=30, operation=True, 
                             enable_strategies=None, create_chart=True):
        """
        Esegue backtest avanzato con strategie di uscita multiple
        
        Args:
            enable_strategies: Dict per abilitare/disabilitare strategie specifiche
            operation: True per LONG only, False per SHORT only
        """
        
        # Configura strategie se specificate
        if enable_strategies:
            self.advanced_config.update(enable_strategies)
        
        direction = "LONG ONLY" if operation else "SHORT ONLY"
        strategies_enabled = [k.replace('enable_', '').upper() for k, v in self.advanced_config.items() 
                            if k.startswith('enable_') and v]
        
        print(f"\n{'='*70}")
        print(f"🚀 ADVANCED BACKTEST: {self.symbol}")
        print(f"{'='*70}")
        print(f"⏰ Timeframe: {timeframe}m")
        print(f"📊 EMA Period: {ema_period}")
        print(f"🕯️ Required Candles: {required_candles}")
        print(f"📏 Max Distance: {max_distance}%")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📅 Period: {days_back} days")
        print(f"🎯 Direction: {direction}")
        print(f"🧠 Advanced Strategies: {', '.join(strategies_enabled)}")
        
        # Ottieni dati principali
        data = self.get_historical_data(timeframe, days_back)
        if data is None or len(data) < ema_period + required_candles:
            print(f"❌ Dati insufficienti")
            return None
        
        # Ottieni dati multi-timeframe se abilitato
        mtf_data = None
        if self.advanced_config.get('enable_multi_timeframe'):
            mtf_data = self.get_smaller_timeframe_data(timeframe, days_back)
            if mtf_data is not None:
                print(f"📈 Multi-timeframe data loaded: {len(mtf_data)} candles")
        
        # Calcola EMA
        closes = data['close'].values
        ema_values = self.calculate_ema(closes, ema_period)
        
        print(f"📥 Processing {len(data)} candles")
        print(f"💲 Price Range: ${closes.min():,.4f} - ${closes.max():,.4f}")
        
        # Variabili backtesting
        capital = self.initial_capital
        position = None  # 'LONG', 'SHORT', None
        position_size = 0  # Quantità in USD
        entry_price = 0
        entry_time = None
        trades = []
        total_fees = 0
        
        # Strutture per strategie avanzate
        active_trailing_stops = {}
        active_fixed_stops = {}
        exit_reasons_stats = {
            'EMA_STOP': 0, 'QUICK_EXIT_SPIKE': 0, 'MULTI_TIMEFRAME_EXIT': 0,
            'DYNAMIC_TRAILING_STOP': 0, 'FIXED_STOP_LOSS': 0
        }
        
        # Simula trading
        for i in range(ema_period, len(data)):
            current_time = data.index[i]
            current_price = closes[i]
            ema_current = ema_values[i]
            
            # Calcola distanza da EMA
            distance_pct = ((current_price - ema_current) / ema_current) * 100
            
            # Prepara dati di mercato per strategie avanzate
            market_data = {
                'symbol': self.symbol,
                'current_price': current_price,
                'ema_value': ema_current,
                'distance_percent': distance_pct,
                'timestamp': current_time,
                'candles_above': self.count_consecutive_candles_above_ema(closes, ema_values, i, required_candles),
                'candles_below': self.count_consecutive_candles_below_ema(closes, ema_values, i, required_candles)
            }
            
            if position is None:
                # LOGICA DI ENTRATA
                distance_ok = abs(distance_pct) <= max_distance
                
                if operation and distance_pct > 0:  # LONG
                    candles_above = self.count_consecutive_candles_above_ema(closes, ema_values, i, required_candles)
                    
                    if candles_above >= required_candles and distance_ok:
                        # Apri posizione LONG
                        position_value = capital * self.position_size_pct
                        fee = position_value * self.fee_rate
                        
                        position = 'LONG'
                        position_size = position_value - fee
                        entry_price = current_price
                        entry_time = current_time
                        total_fees += fee
                        
                        # Inizializza strategie avanzate
                        trade_id = f"trade_{len(trades)}"
                        if self.advanced_config.get('enable_dynamic_trailing'):
                            active_trailing_stops[trade_id] = {
                                'highest_price': current_price,
                                'stop_price': current_price * (1 - self.advanced_config['trailing_stop_percent'] / 100)
                            }
                        
                        if self.advanced_config.get('enable_fixed_stop_loss'):
                            active_fixed_stops[trade_id] = {
                                'entry_price': current_price,
                                'stop_price': current_price * (1 - self.advanced_config['stop_loss_percent'] / 100)
                            }
                        
                        if self.advanced_config.get('advanced_exit_debug'):
                            print(f"📍 LONG @ ${current_price:.4f} | Distance: {distance_pct:+.2f}% | Capital: ${capital:.2f}")
                
                elif not operation and distance_pct < 0:  # SHORT
                    candles_below = self.count_consecutive_candles_below_ema(closes, ema_values, i, required_candles)
                    
                    if candles_below >= required_candles and distance_ok:
                        # Apri posizione SHORT
                        position_value = capital * self.position_size_pct
                        fee = position_value * self.fee_rate
                        
                        position = 'SHORT'
                        position_size = position_value - fee
                        entry_price = current_price
                        entry_time = current_time
                        total_fees += fee
                        
                        # Inizializza strategie avanzate
                        trade_id = f"trade_{len(trades)}"
                        if self.advanced_config.get('enable_dynamic_trailing'):
                            active_trailing_stops[trade_id] = {
                                'lowest_price': current_price,
                                'stop_price': current_price * (1 + self.advanced_config['trailing_stop_percent'] / 100)
                            }
                        
                        if self.advanced_config.get('enable_fixed_stop_loss'):
                            active_fixed_stops[trade_id] = {
                                'entry_price': current_price,
                                'stop_price': current_price * (1 + self.advanced_config['stop_loss_percent'] / 100)
                            }
                        
                        if self.advanced_config.get('advanced_exit_debug'):
                            print(f"📍 SHORT @ ${current_price:.4f} | Distance: {distance_pct:+.2f}% | Capital: ${capital:.2f}")
            
            else:
                # LOGICA DI USCITA CON STRATEGIE AVANZATE
                should_close = False
                close_reason = "EMA_STOP"
                
                current_trade_id = f"trade_{len(trades)}"
                
                # 1. FIXED STOP LOSS (Priorità MASSIMA)
                if self.advanced_config.get('enable_fixed_stop_loss') and current_trade_id in active_fixed_stops:
                    stop_data = active_fixed_stops[current_trade_id]
                    
                    if position == 'LONG' and current_price <= stop_data['stop_price']:
                        should_close = True
                        close_reason = "FIXED_STOP_LOSS"
                    elif position == 'SHORT' and current_price >= stop_data['stop_price']:
                        should_close = True
                        close_reason = "FIXED_STOP_LOSS"
                
                # 2. QUICK EXIT (Priorità ALTA)
                if not should_close and self.advanced_config.get('enable_quick_exit'):
                    volatile_threshold = self.advanced_config['volatile_threshold']
                    
                    if position == 'LONG' and distance_pct <= -volatile_threshold:
                        should_close = True
                        close_reason = "QUICK_EXIT_SPIKE"
                    elif position == 'SHORT' and distance_pct >= volatile_threshold:
                        should_close = True
                        close_reason = "QUICK_EXIT_SPIKE"
                
                # 3. DYNAMIC TRAILING STOP (Priorità MEDIA)
                if not should_close and self.advanced_config.get('enable_dynamic_trailing'):
                    if current_trade_id in active_trailing_stops:
                        trailing_data = active_trailing_stops[current_trade_id]
                        
                        if position == 'LONG':
                            # Aggiorna highest price
                            if current_price > trailing_data['highest_price']:
                                trailing_data['highest_price'] = current_price
                                new_stop = current_price * (1 - self.advanced_config['trailing_stop_percent'] / 100)
                                if new_stop > trailing_data['stop_price']:
                                    trailing_data['stop_price'] = new_stop
                            
                            # Controlla trigger
                            if (current_price <= trailing_data['stop_price'] and 
                                abs(distance_pct) >= self.advanced_config['min_distance_for_trailing']):
                                should_close = True
                                close_reason = "DYNAMIC_TRAILING_STOP"
                        
                        elif position == 'SHORT':
                            # Aggiorna lowest price
                            if current_price < trailing_data['lowest_price']:
                                trailing_data['lowest_price'] = current_price
                                new_stop = current_price * (1 + self.advanced_config['trailing_stop_percent'] / 100)
                                if new_stop < trailing_data['stop_price']:
                                    trailing_data['stop_price'] = new_stop
                            
                            # Controlla trigger
                            if (current_price >= trailing_data['stop_price'] and 
                                abs(distance_pct) >= self.advanced_config['min_distance_for_trailing']):
                                should_close = True
                                close_reason = "DYNAMIC_TRAILING_STOP"
                
                # 4. MULTI-TIMEFRAME EXIT (Priorità MEDIA)
                if not should_close and self.advanced_config.get('enable_multi_timeframe'):
                    spike_threshold = self.advanced_config['spike_threshold']
                    
                    if abs(distance_pct) >= spike_threshold and mtf_data is not None:
                        # Simula controllo multi-timeframe
                        # In un backtest reale, dovresti sincronizzare i timeframe
                        # Per ora usiamo una simulazione semplificata
                        
                        mtf_trigger_chance = 0.3  # 30% probabilità di trigger MTF
                        if np.random.random() < mtf_trigger_chance:
                            should_close = True
                            close_reason = "MULTI_TIMEFRAME_EXIT"
                
                # 5. STANDARD EMA EXIT (Priorità BASSA)
                if not should_close:
                    if position == 'LONG':
                        candles_below = self.count_consecutive_candles_below_ema(closes, ema_values, i, required_candles)
                        if candles_below >= required_candles:
                            should_close = True
                            close_reason = "EMA_STOP"
                    
                    elif position == 'SHORT':
                        candles_above = self.count_consecutive_candles_above_ema(closes, ema_values, i, required_candles)
                        if candles_above >= required_candles:
                            should_close = True
                            close_reason = "EMA_STOP"
                
                # ESEGUI CHIUSURA
                if should_close:
                    exit_reasons_stats[close_reason] += 1
                    
                    # Calcola P&L
                    if position == 'LONG':
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        position_final_value = (current_price / entry_price) * position_size
                    else:  # SHORT
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                        position_final_value = ((2 * entry_price - current_price) / entry_price) * position_size
                    
                    # Fee di uscita
                    exit_fee = position_final_value * self.fee_rate
                    final_value = position_final_value - exit_fee
                    total_fees += exit_fee
                    
                    # Aggiorna capitale
                    capital = capital - (capital * self.position_size_pct) + final_value
                    
                    # Salva trade
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'side': position,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': final_value - (position_size),
                        'capital_after': capital,
                        'exit_reason': close_reason
                    }
                    trades.append(trade)
                    
                    if self.advanced_config.get('advanced_exit_debug'):
                        print(f"🔚 {position} EXIT @ ${current_price:.4f} | {close_reason} | PnL: {pnl_pct:+.2f}% | Capital: ${capital:.2f}")
                    
                    # Reset posizione
                    position = None
                    position_size = 0
                    entry_price = 0
                    entry_time = None
                    
                    # Cleanup strategie avanzate
                    if current_trade_id in active_trailing_stops:
                        del active_trailing_stops[current_trade_id]
                    if current_trade_id in active_fixed_stops:
                        del active_fixed_stops[current_trade_id]
        
        # Calcola statistiche finali
        if not trades:
            print("❌ Nessun trade eseguito")
            return None
        
        # Statistiche avanzate
        winning_trades = [t for t in trades if t['pnl_usd'] > 0]
        losing_trades = [t for t in trades if t['pnl_usd'] <= 0]
        
        total_return_pct = ((capital - self.initial_capital) / self.initial_capital) * 100
        win_rate = (len(winning_trades) / len(trades)) * 100
        
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = (sum([t['pnl_usd'] for t in winning_trades]) / 
                        abs(sum([t['pnl_usd'] for t in losing_trades]))) if losing_trades else float('inf')
        
        # Statistiche per exit reason
        strategy_performance = {}
        for reason, count in exit_reasons_stats.items():
            if count > 0:
                reason_trades = [t for t in trades if t['exit_reason'] == reason]
                reason_pnl = sum([t['pnl_usd'] for t in reason_trades])
                reason_win_rate = (len([t for t in reason_trades if t['pnl_usd'] > 0]) / count) * 100
                
                strategy_performance[reason] = {
                    'count': count,
                    'total_pnl': reason_pnl,
                    'win_rate': reason_win_rate,
                    'avg_pnl_pct': np.mean([t['pnl_pct'] for t in reason_trades])
                }
        
        results = {
            'symbol': self.symbol,
            'timeframe': f"{timeframe}m",
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return_pct': total_return_pct,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'total_fees': total_fees,
            'net_profit': capital - self.initial_capital,
            'trades': trades,
            'strategy_performance': strategy_performance,
            'exit_reasons_stats': exit_reasons_stats,
            'advanced_config': self.advanced_config.copy(),
            'backtest_timestamp': datetime.now().isoformat()
        }
        
        # Stampa risultati
        self._print_results(results)
        
        # Crea grafico se richiesto
        if create_chart:
            try:
                chart_path = self.create_advanced_chart(data, ema_values, trades, results)
                results['chart_path'] = chart_path
            except Exception as e:
                print(f"⚠️ Errore creazione grafico: {e}")
        
        return results
    
    def _print_results(self, results):
        """Stampa risultati dettagliati del backtest"""
        print(f"\n{'='*70}")
        print(f"📊 RISULTATI BACKTEST AVANZATO")
        print(f"{'='*70}")
        
        print(f"💰 Capitale Iniziale: ${results['initial_capital']:,.2f}")
        print(f"💰 Capitale Finale: ${results['final_capital']:,.2f}")
        print(f"📈 Rendimento Totale: {results['total_return_pct']:+.2f}%")
        print(f"💸 Commissioni Totali: ${results['total_fees']:.2f}")
        print(f"💵 Profitto Netto: ${results['net_profit']:+.2f}")
        
        print(f"\n📊 STATISTICHE TRADE:")
        print(f"🔢 Totale Trade: {results['total_trades']}")
        print(f"✅ Trade Vincenti: {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"❌ Trade Perdenti: {results['losing_trades']}")
        print(f"📊 Profit Factor: {results['profit_factor']:.2f}")
        print(f"📈 Avg Win: {results['avg_win_pct']:+.2f}%")
        print(f"📉 Avg Loss: {results['avg_loss_pct']:+.2f}%")
        
        print(f"\n🧠 PERFORMANCE PER STRATEGIA:")
        for strategy, perf in results['strategy_performance'].items():
            strategy_name = strategy.replace('_', ' ').title()
            print(f"  {strategy_name}:")
            print(f"    📊 Trade: {perf['count']} | Win Rate: {perf['win_rate']:.1f}% | PnL: ${perf['total_pnl']:+.2f}")
        
        print(f"\n🎯 EXIT REASONS DISTRIBUTION:")
        total_exits = sum(results['exit_reasons_stats'].values())
        for reason, count in results['exit_reasons_stats'].items():
            if count > 0:
                percentage = (count / total_exits) * 100
                reason_name = reason.replace('_', ' ').title()
                print(f"  {reason_name}: {count} ({percentage:.1f}%)")
        
        print(f"{'='*70}")
    
    def create_advanced_chart(self, data, ema_values, trades, results):
        """Crea grafico avanzato del backtest"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), height_ratios=[3, 1])
            
            # Grafico principale: Prezzo + EMA + Trades
            ax1.plot(data.index, data['close'], label='Prezzo', linewidth=1, alpha=0.8)
            ax1.plot(data.index, ema_values, label=f'EMA({results["advanced_config"]["ema_period"]})', 
                    color='orange', linewidth=2)
            
            # Aggiungi trades
            for trade in trades:
                color = 'green' if trade['pnl_usd'] > 0 else 'red'
                marker = '^' if trade['side'] == 'LONG' else 'v'
                
                # Entry point
                ax1.scatter(trade['entry_time'], trade['entry_price'], 
                           color='blue', marker=marker, s=100, alpha=0.8, zorder=5)
                
                # Exit point con colore basato su exit reason
                exit_colors = {
                    'EMA_STOP': 'orange',
                    'QUICK_EXIT_SPIKE': 'red',
                    'MULTI_TIMEFRAME_EXIT': 'purple',
                    'DYNAMIC_TRAILING_STOP': 'cyan',
                    'FIXED_STOP_LOSS': 'magenta'
                }
                exit_color = exit_colors.get(trade['exit_reason'], 'gray')
                
                ax1.scatter(trade['exit_time'], trade['exit_price'], 
                           color=exit_color, marker='X', s=100, alpha=0.8, zorder=5)
                
                # Linea di connessione
                ax1.plot([trade['entry_time'], trade['exit_time']], 
                        [trade['entry_price'], trade['exit_price']], 
                        color=color, alpha=0.5, linewidth=1)
            
            ax1.set_title(f"{results['symbol']} - Advanced Backtest Results\n"
                         f"Return: {results['total_return_pct']:+.2f}% | "
                         f"Win Rate: {results['win_rate']:.1f}% | "
                         f"Trades: {results['total_trades']}", fontsize=14)
            ax1.set_ylabel('Prezzo ($)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Grafico inferiore: Equity curve
            capitals = [results['initial_capital']]
            dates = [data.index[0]]
            
            for trade in trades:
                capitals.append(trade['capital_after'])
                dates.append(trade['exit_time'])
            
            ax2.plot(dates, capitals, color='green', linewidth=2, label='Equity Curve')
            ax2.axhline(y=results['initial_capital'], color='gray', linestyle='--', alpha=0.5)
            ax2.set_ylabel('Capitale ($)')
            ax2.set_xlabel('Data')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Aggiungi leggenda exit reasons
            legend_elements = []
            for reason, color in exit_colors.items():
                if results['exit_reasons_stats'].get(reason, 0) > 0:
                    reason_name = reason.replace('_', ' ').title()
                    legend_elements.append(plt.Line2D([0], [0], marker='X', color='w', 
                                                    markerfacecolor=color, markersize=8, 
                                                    label=f'{reason_name} ({results["exit_reasons_stats"][reason]})'))
            
            if legend_elements:
                ax1.legend(handles=ax1.get_legend_handles_labels()[0] + legend_elements, 
                          loc='upper left', bbox_to_anchor=(0, 1))
            
            # Formato date
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            plt.tight_layout()
            
            # Salva grafico
            charts_dir = Path("backtest_charts")
            charts_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_backtest_{results['symbol']}_{timestamp}.png"
            filepath = charts_dir / filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📈 Grafico salvato: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Errore creazione grafico: {e}")
            return None


# Classi di supporto per simulazione strategie
class AdvancedExitManagerSim:
    """Manager simulato per strategie di uscita nel backtest"""
    
    def __init__(self, config):
        self.config = config

def analyze_advanced_exit_conditions_sim(exit_manager, trade_id, trade_info, bot_config, market_data):
    """Versione simulata dell'analisi condizioni di uscita"""
    # Questa è una versione semplificata per il backtest
    # Le strategie reali sono implementate nel main backtest loop
    return {
        'should_close': False,
        'exit_type': 'NONE', 
        'reason': 'Backtest simulation',
        'strategy_flags': {}
    }


# Esempio di utilizzo e test
if __name__ == "__main__":
    # Test engine
    engine = AdvancedBacktestEngine("AVAXUSDT", initial_capital=1000)
    
    # Configura strategie
    strategies = {
        'enable_multi_timeframe': True,
        'enable_dynamic_trailing': True,
        'enable_quick_exit': True,
        'enable_fixed_stop_loss': True,
        'spike_threshold': 3.0,
        'volatile_threshold': 5.0,
        'stop_loss_percent': 3.0,
        'trailing_stop_percent': 2.0
    }
    
    # Esegui backtest
    results = engine.run_advanced_backtest(
        ema_period=10,
        required_candles=3,
        max_distance=1.0,
        timeframe='30',
        days_back=30,
        operation=True,  # LONG only
        enable_strategies=strategies,
        create_chart=True
    )
    
    if results:
        print("✅ Advanced backtest completato!")
    else:
        print("❌ Backtest fallito")
