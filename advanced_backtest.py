#!/usr/bin/env python3
"""
Advanced Backtesting Engine per Trading Bot
Sistema avanzato di backtesting con analisi approfondite, ottimizzazione parametri,
e integrazione con il sistema di trading esistente
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import traceback
from pathlib import Path

# Aggiungi il path per gli import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import *
    from trading_functions import (
        get_kline_data,
        media_esponenziale,
        vedi_prezzo_moneta,
        analizza_prezzo_sopra_media,
        controlla_candele_sopra_ema,
        controlla_candele_sotto_ema
    )
    print("✅ Import configurazioni e funzioni trading riuscito!")
except ImportError as e:
    print(f"❌ Errore nell'import: {e}")
    sys.exit(1)

class AdvancedBacktestEngine:
    """Motore di backtesting avanzato per strategie di trading"""
    
    def __init__(self, symbol: str, category: str = "linear", initial_capital: float = 1000):
        self.symbol = symbol
        self.category = category
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Trading state
        self.position_open = False
        self.position_type = None  # True = Long, False = Short
        self.entry_price = 0
        self.quantity = 0
        self.entry_timestamp = 0
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        self.drawdown_curve = []
        self.max_capital = initial_capital
        self.max_drawdown = 0
        
        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0
        self.largest_win = 0
        self.largest_loss = 0
        
        # Advanced metrics
        self.sharpe_ratio = 0
        self.sortino_ratio = 0
        self.max_consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.current_streak = 0
        self.current_streak_type = None  # 'win' or 'loss'
        
        # Risk management
        self.stop_loss_pct = None
        self.take_profit_pct = None
        self.max_risk_per_trade = 0.02  # 2% del capitale per trade
        
    def set_risk_management(self, stop_loss_pct: float = None, take_profit_pct: float = None, 
                           max_risk_per_trade: float = 0.02):
        """Configura risk management"""
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_risk_per_trade = max_risk_per_trade
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float = None) -> float:
        """Calcola la dimensione della posizione basata sul risk management"""
        if stop_loss_price and self.max_risk_per_trade:
            # Risk-based position sizing
            risk_amount = self.current_capital * self.max_risk_per_trade
            price_diff = abs(entry_price - stop_loss_price)
            if price_diff > 0:
                return risk_amount / price_diff
        
        # Default: usa tutto il capitale disponibile
        return self.current_capital / entry_price
    
    def open_position(self, position_type: bool, price: float, timestamp: int, 
                     reason: str = "", quantity_override: float = None) -> bool:
        """Apre una posizione con risk management avanzato"""
        if self.position_open:
            return False
        
        # Calcola stop loss se configurato
        stop_loss_price = None
        if self.stop_loss_pct:
            if position_type:  # Long
                stop_loss_price = price * (1 - self.stop_loss_pct / 100)
            else:  # Short
                stop_loss_price = price * (1 + self.stop_loss_pct / 100)
        
        # Calcola dimensione posizione
        if quantity_override:
            self.quantity = quantity_override
        else:
            self.quantity = self.calculate_position_size(price, stop_loss_price)
        
        # Apri posizione
        self.position_open = True
        self.position_type = position_type
        self.entry_price = price
        self.entry_timestamp = timestamp
        
        # Calcola commissioni (0.1% Bybit)
        trade_value = self.quantity * price
        fee = trade_value * 0.001  # 0.1%
        self.total_fees += fee
        
        trade_record = {
            'timestamp': timestamp,
            'action': 'OPEN',
            'type': 'LONG' if position_type else 'SHORT',
            'price': price,
            'quantity': self.quantity,
            'value': trade_value,
            'fee': fee,
            'capital_before': self.current_capital,
            'reason': reason,
            'stop_loss': stop_loss_price
        }
        self.trades.append(trade_record)
        
        print(f"   🟢 APRI {trade_record['type']}: {self.quantity:.6f} @ ${price:,.2f} "
              f"(Val: ${trade_value:.2f}, Fee: ${fee:.2f}) - {reason}")
        
        return True
    
    def close_position(self, price: float, timestamp: int, reason: str = "") -> bool:
        """Chiude una posizione con calcolo avanzato P&L"""
        if not self.position_open:
            return False
        
        # Calcola P&L
        trade_value = self.quantity * price
        initial_value = self.quantity * self.entry_price
        
        if self.position_type:  # Long
            pnl = trade_value - initial_value
        else:  # Short
            pnl = initial_value - trade_value
        
        # Calcola commissioni chiusura
        fee = trade_value * 0.001  # 0.1%
        self.total_fees += fee
        
        # P&L netto (dopo commissioni)
        net_pnl = pnl - fee
        
        # Aggiorna capitale
        if self.position_type:  # Long
            self.current_capital = trade_value - fee
        else:  # Short
            self.current_capital = self.current_capital + net_pnl
        
        # Calcoli percentuali
        pnl_pct = (net_pnl / initial_value) * 100
        capital_pct = (net_pnl / self.trades[-1]['capital_before']) * 100
        
        # Durata trade
        duration_ms = timestamp - self.entry_timestamp
        duration_hours = duration_ms / (1000 * 60 * 60)
        
        trade_record = {
            'timestamp': timestamp,
            'action': 'CLOSE',
            'type': 'LONG' if self.position_type else 'SHORT',
            'price': price,
            'quantity': self.quantity,
            'value': trade_value,
            'fee': fee,
            'pnl_gross': pnl,
            'pnl_net': net_pnl,
            'pnl_pct': pnl_pct,
            'capital_pct': capital_pct,
            'capital_after': self.current_capital,
            'duration_hours': duration_hours,
            'reason': reason
        }
        self.trades.append(trade_record)
        
        # Aggiorna statistiche
        self.total_trades += 1
        if net_pnl > 0:
            self.winning_trades += 1
            self.largest_win = max(self.largest_win, net_pnl)
            if self.current_streak_type == 'win':
                self.current_streak += 1
            else:
                self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_streak)
                self.current_streak = 1
                self.current_streak_type = 'win'
        else:
            self.losing_trades += 1
            self.largest_loss = min(self.largest_loss, net_pnl)
            if self.current_streak_type == 'loss':
                self.current_streak += 1
            else:
                self.max_consecutive_wins = max(self.max_consecutive_wins, self.current_streak)
                self.current_streak = 1
                self.current_streak_type = 'loss'
        
        # Aggiorna equity e drawdown
        self.max_capital = max(self.max_capital, self.current_capital)
        current_drawdown = (self.max_capital - self.current_capital) / self.max_capital * 100
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        print(f"   🔴 CHIUDI {trade_record['type']}: {self.quantity:.6f} @ ${price:,.2f} "
              f"P&L: ${net_pnl:.2f} ({pnl_pct:+.2f}%) Capitale: ${self.current_capital:.2f} - {reason}")
        
        # Reset posizione
        self.position_open = False
        self.position_type = None
        self.entry_price = 0
        self.quantity = 0
        self.entry_timestamp = 0
        
        return True
    
    def check_risk_management(self, current_price: float, timestamp: int) -> bool:
        """Controlla se attivare stop loss o take profit"""
        if not self.position_open:
            return False
        
        # Controlla stop loss
        if self.stop_loss_pct:
            if self.position_type:  # Long
                stop_price = self.entry_price * (1 - self.stop_loss_pct / 100)
                if current_price <= stop_price:
                    self.close_position(current_price, timestamp, 
                                      f"STOP LOSS ({self.stop_loss_pct}%)")
                    return True
            else:  # Short
                stop_price = self.entry_price * (1 + self.stop_loss_pct / 100)
                if current_price >= stop_price:
                    self.close_position(current_price, timestamp, 
                                      f"STOP LOSS ({self.stop_loss_pct}%)")
                    return True
        
        # Controlla take profit
        if self.take_profit_pct:
            if self.position_type:  # Long
                target_price = self.entry_price * (1 + self.take_profit_pct / 100)
                if current_price >= target_price:
                    self.close_position(current_price, timestamp, 
                                      f"TAKE PROFIT ({self.take_profit_pct}%)")
                    return True
            else:  # Short
                target_price = self.entry_price * (1 - self.take_profit_pct / 100)
                if current_price <= target_price:
                    self.close_position(current_price, timestamp, 
                                      f"TAKE PROFIT ({self.take_profit_pct}%)")
                    return True
        
        return False
    
    def update_equity_curve(self, timestamp: int, price: float, ema_value: float = None):
        """Aggiorna la curva di equity"""
        # Calcola valore posizione corrente
        if self.position_open:
            current_value = self.quantity * price
            if self.position_type:  # Long
                unrealized_pnl = current_value - (self.quantity * self.entry_price)
                current_equity = current_value - (self.total_fees * 2)  # Stima commissioni
            else:  # Short
                unrealized_pnl = (self.quantity * self.entry_price) - current_value
                current_equity = self.current_capital + unrealized_pnl
        else:
            unrealized_pnl = 0
            current_equity = self.current_capital
        
        equity_point = {
            'timestamp': timestamp,
            'price': price,
            'equity': current_equity,
            'unrealized_pnl': unrealized_pnl,
            'position_open': self.position_open,
            'drawdown': (self.max_capital - current_equity) / self.max_capital * 100 if self.max_capital > 0 else 0,
            'ema': ema_value
        }
        self.equity_curve.append(equity_point)
    
    def test_triple_confirmation_strategy(self, ema_period: int = 10, required_candles: int = 3,
                                       max_distance: float = 1.0, timeframe: str = "30",
                                       days_back: int = 30, use_risk_management: bool = True) -> Dict:
        """
        Testa la strategia Triple Confirmation con la stessa logica del bot reale
        """
        print(f"\n{'='*80}")
        print(f"🎯 ADVANCED BACKTEST: TRIPLE CONFIRMATION STRATEGY")
        print(f"{'='*80}")
        print(f"📊 Symbol: {self.symbol}")
        print(f"⏰ Timeframe: {timeframe} minutes")
        print(f"📈 EMA Period: {ema_period}")
        print(f"🕯️ Required Candles: {required_candles}")
        print(f"📏 Max Distance from EMA: {max_distance}%")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📅 Test Period: {days_back} days")
        print(f"🛡️ Risk Management: {'ON' if use_risk_management else 'OFF'}")
        
        if use_risk_management:
            self.set_risk_management(stop_loss_pct=2.0, take_profit_pct=4.0, max_risk_per_trade=0.05)
            print(f"   🛑 Stop Loss: {self.stop_loss_pct}%")
            print(f"   🎯 Take Profit: {self.take_profit_pct}%")
            print(f"   💰 Max Risk per Trade: {self.max_risk_per_trade*100}%")
        
        # Calcola quante candele servono
        limit = self._calculate_candles_needed(timeframe, days_back, ema_period)
        print(f"📥 Downloading {limit} candles...")
        
        # Scarica dati
        kline_data = get_kline_data(self.category, self.symbol, timeframe, limit=limit)
        
        if not kline_data or len(kline_data) < ema_period + required_candles:
            print("❌ Insufficient data for backtest")
            return {}
        
        # Prepara dati
        timestamps = [int(candle[0]) for candle in reversed(kline_data)]
        opens = [float(candle[1]) for candle in reversed(kline_data)]
        highs = [float(candle[2]) for candle in reversed(kline_data)]
        lows = [float(candle[3]) for candle in reversed(kline_data)]
        closes = [float(candle[4]) for candle in reversed(kline_data)]
        volumes = [float(candle[5]) for candle in reversed(kline_data)]
        
        # Calcola EMA
        ema_values = media_esponenziale(closes, ema_period)
        
        print(f"✅ Processing {len(closes)} candles")
        print(f"📊 Price Range: ${min(closes):,.2f} - ${max(closes):,.2f}")
        print(f"📊 EMA Range: ${min(ema_values[ema_period:]):,.2f} - ${max(ema_values[ema_period:]):,.2f}")
        
        # Contatori segnali
        long_signals = 0
        short_signals = 0
        
        # Simula trading
        for i in range(ema_period + required_candles, len(closes)):
            timestamp = timestamps[i]
            current_price = closes[i]
            current_ema = ema_values[i]
            
            # Aggiorna equity curve
            self.update_equity_curve(timestamp, current_price, current_ema)
            
            # Controlla risk management prima dei segnali
            if use_risk_management and self.check_risk_management(current_price, timestamp):
                continue
            
            if not self.position_open:
                # Logica di entrata - replica esatta del bot reale
                
                # Segnale LONG: controlla candele sopra EMA
                candles_above = self._check_candles_above_ema(closes[:i+1], ema_values[:i+1], required_candles)
                
                if candles_above >= required_candles:
                    distance = self._calculate_ema_distance(current_price, current_ema)
                    
                    if 0 <= distance <= max_distance:
                        # Volume confirmation (opzionale)
                        volume_ok = self._check_volume_confirmation(volumes, i)
                        
                        if volume_ok:
                            quantity = self.current_capital / current_price if not use_risk_management else None
                            if self.open_position(True, current_price, timestamp, 
                                                f"LONG: {candles_above} candles above EMA, dist: {distance:.2f}%",
                                                quantity):
                                long_signals += 1
                
                # Segnale SHORT: controlla candele sotto EMA
                candles_below = self._check_candles_below_ema(closes[:i+1], ema_values[:i+1], required_candles)
                
                if candles_below >= required_candles:
                    distance = self._calculate_ema_distance(current_price, current_ema)
                    
                    if -max_distance <= distance <= 0:
                        # Volume confirmation (opzionale)
                        volume_ok = self._check_volume_confirmation(volumes, i)
                        
                        if volume_ok:
                            quantity = self.current_capital / current_price if not use_risk_management else None
                            if self.open_position(False, current_price, timestamp,
                                                f"SHORT: {candles_below} candles below EMA, dist: {distance:.2f}%",
                                                quantity):
                                short_signals += 1
            
            else:
                # Logica di uscita - trailing stop con EMA
                if self.position_type:  # Long position
                    candles_below = self._check_candles_below_ema(closes[:i+1], ema_values[:i+1], required_candles)
                    
                    if candles_below >= required_candles:
                        self.close_position(current_price, timestamp,
                                          f"TRAILING STOP LONG: {candles_below} candles below EMA")
                
                else:  # Short position
                    candles_above = self._check_candles_above_ema(closes[:i+1], ema_values[:i+1], required_candles)
                    
                    if candles_above >= required_candles:
                        self.close_position(current_price, timestamp,
                                          f"TRAILING STOP SHORT: {candles_above} candles above EMA")
        
        # Chiudi posizione finale se aperta
        if self.position_open:
            self.close_position(closes[-1], timestamps[-1], "END OF BACKTEST")
        
        # Genera report
        results = self._generate_advanced_report(long_signals, short_signals, timeframe, days_back)
        
        return results
    
    def _calculate_candles_needed(self, timeframe: str, days_back: int, ema_period: int) -> int:
        """Calcola il numero di candele necessarie per il backtest"""
        if timeframe == "M":
            return max(24, ema_period + 10)
        elif timeframe == "W":
            return max(52, ema_period + 10)
        elif timeframe == "D":
            return max(days_back + ema_period + 10, 100)
        elif timeframe == "720":  # 12 ore
            return (days_back * 2) + ema_period + 10
        elif timeframe == "360":  # 6 ore
            return (days_back * 4) + ema_period + 10
        elif timeframe == "240":  # 4 ore
            return (days_back * 6) + ema_period + 10
        elif timeframe == "120":  # 2 ore
            return (days_back * 12) + ema_period + 10
        elif timeframe == "60":   # 1 ora
            return (days_back * 24) + ema_period + 10
        elif timeframe == "30":   # 30 minuti
            return (days_back * 48) + ema_period + 10
        elif timeframe == "15":   # 15 minuti
            return (days_back * 96) + ema_period + 10
        elif timeframe == "5":    # 5 minuti
            return (days_back * 288) + ema_period + 10
        elif timeframe == "3":    # 3 minuti
            return (days_back * 480) + ema_period + 10
        elif timeframe == "1":    # 1 minuto
            return (days_back * 1440) + ema_period + 10
        else:
            return min(1000, (days_back * 48) + ema_period + 10)
    
    def _check_candles_above_ema(self, prices: List[float], ema_values: List[float], 
                                required_candles: int) -> int:
        """Conta candele consecutive sopra EMA"""
        if len(prices) < required_candles or len(ema_values) < required_candles:
            return 0
        
        consecutive = 0
        for i in range(required_candles):
            idx = -(i + 1)
            if prices[idx] > ema_values[idx]:
                consecutive += 1
            else:
                break
        return consecutive
    
    def _check_candles_below_ema(self, prices: List[float], ema_values: List[float],
                                required_candles: int) -> int:
        """Conta candele consecutive sotto EMA"""
        if len(prices) < required_candles or len(ema_values) < required_candles:
            return 0
        
        consecutive = 0
        for i in range(required_candles):
            idx = -(i + 1)
            if prices[idx] < ema_values[idx]:
                consecutive += 1
            else:
                break
        return consecutive
    
    def _calculate_ema_distance(self, price: float, ema_value: float) -> float:
        """Calcola distanza percentuale dall'EMA"""
        return ((price - ema_value) / ema_value) * 100
    
    def _check_volume_confirmation(self, volumes: List[float], index: int, 
                                  lookback: int = 5) -> bool:
        """Controlla conferma volume (opzionale)"""
        if index < lookback:
            return True  # Non abbastanza dati, accetta
        
        current_volume = volumes[index]
        avg_volume = sum(volumes[index-lookback:index]) / lookback
        
        # Volume sopra media
        return current_volume > avg_volume * 1.2
    
    def _generate_advanced_report(self, long_signals: int, short_signals: int,
                                timeframe: str, days_back: int) -> Dict:
        """Genera report dettagliato del backtest"""
        
        print(f"\n{'='*80}")
        print(f"📊 ADVANCED BACKTEST RESULTS")
        print(f"{'='*80}")
        
        # Metriche base
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        print(f"💰 PERFORMANCE:")
        print(f"   Initial Capital: ${self.initial_capital:,.2f}")
        print(f"   Final Capital: ${self.current_capital:,.2f}")
        print(f"   Total Return: ${total_return:,.2f} ({total_return_pct:+.2f}%)")
        print(f"   Max Drawdown: {self.max_drawdown:.2f}%")
        
        print(f"\n📈 TRADES:")
        print(f"   Total Trades: {self.total_trades}")
        print(f"   Long Signals: {long_signals}")
        print(f"   Short Signals: {short_signals}")
        print(f"   Winning Trades: {self.winning_trades}")
        print(f"   Losing Trades: {self.losing_trades}")
        
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            print(f"   Win Rate: {win_rate:.1f}%")
        
        print(f"\n💵 P&L ANALYSIS:")
        print(f"   Largest Win: ${self.largest_win:.2f}")
        print(f"   Largest Loss: ${self.largest_loss:.2f}")
        print(f"   Total Fees: ${self.total_fees:.2f}")
        
        # Calcola metriche avanzate
        if len(self.equity_curve) > 0:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                if prev_equity > 0:
                    daily_return = (curr_equity - prev_equity) / prev_equity
                    returns.append(daily_return)
            
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                
                # Sharpe Ratio (assumendo risk-free rate = 0)
                sharpe = (avg_return / std_return) * np.sqrt(365) if std_return > 0 else 0
                
                # Sortino Ratio
                negative_returns = [r for r in returns if r < 0]
                downside_std = np.std(negative_returns) if negative_returns else 0
                sortino = (avg_return / downside_std) * np.sqrt(365) if downside_std > 0 else 0
                
                print(f"\n📊 ADVANCED METRICS:")
                print(f"   Sharpe Ratio: {sharpe:.2f}")
                print(f"   Sortino Ratio: {sortino:.2f}")
                print(f"   Volatility: {std_return * np.sqrt(365) * 100:.2f}%")
        
        print(f"\n🎯 STREAK ANALYSIS:")
        print(f"   Max Consecutive Wins: {self.max_consecutive_wins}")
        print(f"   Max Consecutive Losses: {self.max_consecutive_losses}")
        
        # Salva risultati
        results = {
            'symbol': self.symbol,
            'timeframe': timeframe,
            'days_back': days_back,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'max_drawdown': self.max_drawdown,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'total_fees': self.total_fees,
            'sharpe_ratio': sharpe if 'sharpe' in locals() else 0,
            'sortino_ratio': sortino if 'sortino' in locals() else 0,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        # Salva in file
        self._save_results_to_file(results)
        
        return results
    
    def _save_results_to_file(self, results: Dict):
        """Salva i risultati in un file JSON"""
        try:
            # Crea directory se non esiste
            results_dir = Path("backtest_results")
            results_dir.mkdir(exist_ok=True)
            
            # Nome file con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{self.symbol}_{results['timeframe']}_{timestamp}.json"
            filepath = results_dir / filename
            
            # Serializza i risultati (converte numpy types)
            serializable_results = self._make_serializable(results)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {filepath}")
            
        except Exception as e:
            print(f"⚠️ Error saving results: {e}")
    
    def _make_serializable(self, obj):
        """Converte oggetti numpy in tipi serializzabili"""
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

def run_quick_backtest():
    """Esegue un backtest rapido con parametri predefiniti"""
    print("🚀 QUICK BACKTEST - Triple Confirmation Strategy")
    
    symbol = input("📝 Symbol (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    
    engine = AdvancedBacktestEngine(symbol, initial_capital=1000)
    
    results = engine.test_triple_confirmation_strategy(
        ema_period=10,
        required_candles=3,
        max_distance=1.0,
        timeframe="30",
        days_back=30,
        use_risk_management=True
    )
    
    return results

def run_parameter_optimization():
    """Ottimizzazione parametri con grid search"""
    print("🧪 PARAMETER OPTIMIZATION")
    
    symbol = input("📝 Symbol (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    
    # Parametri da testare
    ema_periods = [5, 10, 15, 20]
    candle_counts = [2, 3, 4, 5]
    distances = [0.5, 1.0, 1.5, 2.0]
    
    best_result = {'total_return_pct': -999999}
    all_results = []
    
    total_tests = len(ema_periods) * len(candle_counts) * len(distances)
    current_test = 0
    
    print(f"⏳ Running {total_tests} optimization tests...")
    
    for ema in ema_periods:
        for candles in candle_counts:
            for distance in distances:
                current_test += 1
                print(f"\n🔄 Test {current_test}/{total_tests}: EMA={ema}, Candles={candles}, Distance={distance}%")
                
                try:
                    engine = AdvancedBacktestEngine(symbol, initial_capital=1000)
                    results = engine.test_triple_confirmation_strategy(
                        ema_period=ema,
                        required_candles=candles,
                        max_distance=distance,
                        timeframe="30",
                        days_back=30,
                        use_risk_management=True
                    )
                    
                    # Aggiungi parametri ai risultati
                    results['ema_period'] = ema
                    results['required_candles'] = candles
                    results['max_distance'] = distance
                    
                    all_results.append(results)
                    
                    if results['total_return_pct'] > best_result['total_return_pct']:
                        best_result = results
                    
                    print(f"   Return: {results['total_return_pct']:.2f}%, Trades: {results['total_trades']}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
    
    # Mostra risultati ottimizzazione
    print(f"\n{'='*80}")
    print(f"🏆 OPTIMIZATION RESULTS")
    print(f"{'='*80}")
    
    print(f"🥇 BEST PARAMETERS:")
    print(f"   EMA Period: {best_result.get('ema_period')}")
    print(f"   Required Candles: {best_result.get('required_candles')}")
    print(f"   Max Distance: {best_result.get('max_distance')}%")
    print(f"   Return: {best_result.get('total_return_pct', 0):.2f}%")
    print(f"   Total Trades: {best_result.get('total_trades', 0)}")
    print(f"   Win Rate: {best_result.get('win_rate', 0):.1f}%")
    
    # Top 5 combinazioni
    sorted_results = sorted(all_results, key=lambda x: x['total_return_pct'], reverse=True)
    print(f"\n🏅 TOP 5 COMBINATIONS:")
    for i, result in enumerate(sorted_results[:5]):
        print(f"   {i+1}. EMA={result.get('ema_period')}, "
              f"Candles={result.get('required_candles')}, "
              f"Dist={result.get('max_distance')}% → "
              f"{result.get('total_return_pct', 0):.2f}%")
    
    # Salva risultati ottimizzazione
    try:
        opt_results = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'best_parameters': best_result,
            'all_results': sorted_results
        }
        
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_{symbol}_{timestamp}.json"
        filepath = results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(opt_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Optimization results saved to: {filepath}")
        
    except Exception as e:
        print(f"⚠️ Error saving optimization results: {e}")
    
    return best_result

def compare_timeframes():
    """Confronta performance su timeframe diversi"""
    print("📊 TIMEFRAME COMPARISON")
    
    symbol = input("📝 Symbol (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    
    timeframes = [
        ("5", "5 minutes"),
        ("15", "15 minutes"),
        ("30", "30 minutes"),
        ("60", "1 hour"),
        ("240", "4 hours"),
        ("D", "1 day")
    ]
    
    results = []
    
    for tf_code, tf_name in timeframes:
        print(f"\n⏰ Testing {tf_name}...")
        
        try:
            # Calcola giorni appropriati per il timeframe
            if tf_code in ["5", "15", "30"]:
                days = 14
            elif tf_code in ["60", "240"]:
                days = 60
            else:
                days = 180
            
            engine = AdvancedBacktestEngine(symbol, initial_capital=1000)
            result = engine.test_triple_confirmation_strategy(
                ema_period=10,
                required_candles=3,
                max_distance=1.0,
                timeframe=tf_code,
                days_back=days,
                use_risk_management=True
            )
            
            result['timeframe_name'] = tf_name
            result['timeframe_code'] = tf_code
            results.append(result)
            
        except Exception as e:
            print(f"   ❌ Error on {tf_name}: {e}")
    
    # Ordina per performance
    results.sort(key=lambda x: x['total_return_pct'], reverse=True)
    
    print(f"\n{'='*80}")
    print(f"🏆 TIMEFRAME COMPARISON RESULTS")
    print(f"{'='*80}")
    
    for i, result in enumerate(results):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📊"
        print(f"{emoji} {result['timeframe_name']}: "
              f"{result['total_return_pct']:.2f}% "
              f"({result['total_trades']} trades, "
              f"{result['win_rate']:.1f}% win rate)")
    
    return results

def main():
    """Menu principale backtest avanzato"""
    print(f"\n{'='*80}")
    print(f"🚀 ADVANCED BACKTESTING ENGINE v2.0")
    print(f"{'='*80}")
    
    while True:
        print(f"\n📊 ADVANCED BACKTEST MENU:")
        print("1. 🎯 Quick Backtest (Recommended)")
        print("2. 🧪 Parameter Optimization")
        print("3. 📊 Timeframe Comparison")
        print("4. 📈 Custom Backtest")
        print("5. 📁 View Previous Results")
        print("0. ❌ Exit")
        
        choice = input("\n👉 Choose option: ").strip()
        
        if choice == "1":
            run_quick_backtest()
        elif choice == "2":
            run_parameter_optimization()
        elif choice == "3":
            compare_timeframes()
        elif choice == "4":
            # TODO: Implementare custom backtest
            print("🚧 Custom backtest coming soon...")
        elif choice == "5":
            # TODO: Implementare visualizzazione risultati precedenti
            print("🚧 Results viewer coming soon...")
        elif choice == "0":
            print("👋 Exiting advanced backtest...")
            break
        else:
            print("❌ Invalid option!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Backtest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print(f"📝 Traceback:\n{traceback.format_exc()}")
