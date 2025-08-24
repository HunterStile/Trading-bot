"""
Sistema di Backtesting Semplificato per Trading Bot
Versione corretta con calcoli realistici
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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import api, api_sec
    from trading_functions import get_kline_data, media_esponenziale
except ImportError as e:
    print(f"Errore importazione config: {e}")
    api = api_sec = None

class SimpleBacktestEngine:
    """
    Engine di backtesting semplificato con calcoli corretti
    """
    
    def __init__(self, symbol="BTCUSDT", initial_capital=1000):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.fee_rate = 0.001  # 0.1% fee
        
        # Risk management
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 4.0
        self.position_size_pct = 0.95  # Usa 95% del capitale
        
    def get_historical_data(self, timeframe='30', days_back=30):
        """Ottieni dati storici da Bybit"""
        try:
            if not api:
                print("❌ API non configurata")
                return None
            
            # Converti timeframe per Bybit API
            interval_map = {
                '5': '5',
                '15': '15', 
                '30': '30',
                '60': '60',
                '240': '240',
                'D': 'D'
            }
            
            interval = interval_map.get(timeframe, '30')
            
            # Calcola quante candele servono
            if interval == 'D':
                limit = min(days_back + 50, 1000)
            elif interval == '240':
                limit = min((days_back * 6) + 50, 1000)
            elif interval == '60':
                limit = min((days_back * 24) + 50, 1000)
            elif interval == '30':
                limit = min((days_back * 48) + 50, 1000)
            elif interval == '15':
                limit = min((days_back * 96) + 50, 1000)
            elif interval == '5':
                limit = min((days_back * 288) + 50, 1000)
            else:
                limit = 200
            
            # API call diretta
            url = "https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': self.symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get('retCode') != 0:
                print(f"❌ API Error: {data.get('retMsg', 'Unknown error')}")
                return None
            
            klines = data.get('result', {}).get('list', [])
            
            if not klines or len(klines) < 50:
                print(f"❌ Dati insufficienti per {self.symbol}")
                return None
            
            # Converti in DataFrame
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
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            print(f"❌ Errore download dati: {e}")
            return None
    
    def calculate_ema(self, prices, period):
        """Calcola EMA"""
        try:
            ema_values = media_esponenziale(prices, period)
            return np.array(ema_values)
        except:
            # Fallback manuale
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            alpha = 2 / (period + 1)
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
            return ema
    
    def count_consecutive_candles_above_ema(self, prices, ema, current_idx, required):
        """Conta candele consecutive sopra EMA"""
        count = 0
        for i in range(current_idx, max(-1, current_idx - required - 1), -1):
            if i >= 0 and prices[i] > ema[i]:
                count += 1
            else:
                break
        return count
    
    def count_consecutive_candles_below_ema(self, prices, ema, current_idx, required):
        """Conta candele consecutive sotto EMA"""
        count = 0
        for i in range(current_idx, max(-1, current_idx - required - 1), -1):
            if i >= 0 and prices[i] < ema[i]:
                count += 1
            else:
                break
        return count
    
    def run_backtest(self, ema_period=10, required_candles=3, max_distance=1.0, 
                    timeframe='30', days_back=30, use_risk_management=True, operation=True, create_chart=True):
        """
        Esegue backtest semplificato
        
        Args:
            operation (bool): True per LONG only, False per SHORT only
            create_chart (bool): True per creare grafico del backtest
        """
        direction = "LONG ONLY" if operation else "SHORT ONLY"
        print(f"\n{'='*60}")
        print(f"📈 SIMPLE BACKTEST: {self.symbol}")
        print(f"{'='*60}")
        print(f"⏰ Timeframe: {timeframe}m")
        print(f"📊 EMA Period: {ema_period}")
        print(f"🕯️ Required Candles: {required_candles}")
        print(f"📏 Max Distance: {max_distance}%")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📅 Period: {days_back} days")
        print(f"🛡️ Risk Management: {'ON' if use_risk_management else 'OFF'}")
        print(f"🎯 Direction: {direction}")
        
        # Ottieni dati
        data = self.get_historical_data(timeframe, days_back)
        if data is None or len(data) < ema_period + required_candles:
            print(f"❌ Dati insufficienti")
            return None
        
        # Calcola EMA
        closes = data['close'].values
        ema_values = self.calculate_ema(closes, ema_period)
        
        print(f"📥 Processing {len(data)} candles")
        print(f"💲 Price Range: ${closes.min():,.2f} - ${closes.max():,.2f}")
        
        # Variabili backtesting
        capital = self.initial_capital
        position = None  # 'LONG', 'SHORT', None
        position_size = 0  # Quantità in USD
        entry_price = 0
        entry_time = None
        trades = []
        total_fees = 0
        
        # Loop principale
        for i in range(ema_period + required_candles, len(data)):
            current_price = closes[i]
            current_ema = ema_values[i]
            current_time = data.index[i]
            
            # === GESTIONE CHIUSURA POSIZIONE ===
            if position is not None:
                exit_signal = False
                exit_reason = ""
                
                if position == 'LONG':
                    # Trailing stop per LONG
                    candles_below = self.count_consecutive_candles_below_ema(
                        closes, ema_values, i, required_candles)
                    if candles_below >= required_candles:
                        exit_signal = True
                        exit_reason = "Trailing Stop"
                    
                    # Risk management per LONG
                    if use_risk_management:
                        price_change_pct = (current_price - entry_price) / entry_price * 100
                        if price_change_pct <= -self.stop_loss_pct:
                            exit_signal = True
                            exit_reason = f"Stop Loss ({self.stop_loss_pct}%)"
                        elif price_change_pct >= self.take_profit_pct:
                            exit_signal = True
                            exit_reason = f"Take Profit ({self.take_profit_pct}%)"
                
                elif position == 'SHORT':
                    # Trailing stop per SHORT
                    candles_above = self.count_consecutive_candles_above_ema(
                        closes, ema_values, i, required_candles)
                    if candles_above >= required_candles:
                        exit_signal = True
                        exit_reason = "Trailing Stop"
                    
                    # Risk management per SHORT
                    if use_risk_management:
                        price_change_pct = (entry_price - current_price) / entry_price * 100
                        if price_change_pct <= -self.stop_loss_pct:
                            exit_signal = True
                            exit_reason = f"Stop Loss ({self.stop_loss_pct}%)"
                        elif price_change_pct >= self.take_profit_pct:
                            exit_signal = True
                            exit_reason = f"Take Profit ({self.take_profit_pct}%)"
                
                # Chiudi posizione se c'è segnale
                if exit_signal:
                    # Calcola P&L
                    if position == 'LONG':
                        pnl_pct = (current_price - entry_price) / entry_price * 100
                        pnl = position_size * (pnl_pct / 100)
                    else:  # SHORT
                        pnl_pct = (entry_price - current_price) / entry_price * 100
                        pnl = position_size * (pnl_pct / 100)
                    
                    # Applica fee di chiusura
                    exit_fee = position_size * self.fee_rate
                    pnl -= exit_fee
                    total_fees += exit_fee
                    
                    # Aggiorna capitale
                    capital += pnl
                    
                    # Registra trade
                    trade = {
                        'side': position,
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position_size,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'duration_hours': (current_time - entry_time).total_seconds() / 3600
                    }
                    trades.append(trade)
                    
                    print(f"🔴 CLOSE {position}: ${current_price:,.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | Capital: ${capital:,.2f} | {exit_reason}")
                    
                    # Reset posizione
                    position = None
                    position_size = 0
                    entry_price = 0
                    entry_time = None
            
            # === APERTURA NUOVE POSIZIONI ===
            if position is None:
                # Calcola distanza da EMA
                distance_pct = abs(current_price - current_ema) / current_ema * 100
                
                if distance_pct <= max_distance:
                    if operation:  # LONG ONLY
                        # Segnale LONG
                        candles_above = self.count_consecutive_candles_above_ema(
                            closes, ema_values, i, required_candles)
                        
                        if candles_above >= required_candles and current_price > current_ema:
                            position = 'LONG'
                            entry_price = current_price
                            entry_time = current_time
                            position_size = capital * self.position_size_pct
                            
                            # Fee di apertura
                            entry_fee = position_size * self.fee_rate
                            capital -= entry_fee
                            total_fees += entry_fee
                            
                            print(f"🟢 OPEN LONG: ${current_price:,.2f} | Size: ${position_size:,.2f} | Dist: {(current_price-current_ema)/current_ema*100:+.2f}%")
                    
                    else:  # SHORT ONLY
                        # Segnale SHORT
                        candles_below = self.count_consecutive_candles_below_ema(
                            closes, ema_values, i, required_candles)
                        
                        if candles_below >= required_candles and current_price < current_ema:
                            position = 'SHORT'
                            entry_price = current_price
                            entry_time = current_time
                            position_size = capital * self.position_size_pct
                            
                            # Fee di apertura
                            entry_fee = position_size * self.fee_rate
                            capital -= entry_fee
                            total_fees += entry_fee
                            
                            print(f"🟢 OPEN SHORT: ${current_price:,.2f} | Size: ${position_size:,.2f} | Dist: {(current_price-current_ema)/current_ema*100:+.2f}%")
        
        # Chiudi posizione finale se aperta
        if position is not None:
            current_price = closes[-1]
            if position == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price * 100
                pnl = position_size * (pnl_pct / 100)
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
                pnl = position_size * (pnl_pct / 100)
            
            exit_fee = position_size * self.fee_rate
            pnl -= exit_fee
            total_fees += exit_fee
            capital += pnl
            
            trades.append({
                'side': position,
                'entry_time': entry_time,
                'exit_time': data.index[-1],
                'entry_price': entry_price,
                'exit_price': current_price,
                'position_size': position_size,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': 'End of Data',
                'duration_hours': (data.index[-1] - entry_time).total_seconds() / 3600
            })
            
            print(f"🔴 CLOSE {position}: ${current_price:,.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | End of Data")
        
        # === CALCOLO RISULTATI ===
        final_capital = capital
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Analisi trade
        if trades:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            win_rate = len(winning_trades) / len(trades) * 100
            
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            largest_win = max([t['pnl'] for t in trades])
            largest_loss = min([t['pnl'] for t in trades])
            
            # Profit Factor
            total_wins = sum([t['pnl'] for t in winning_trades])
            total_losses = abs(sum([t['pnl'] for t in losing_trades]))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        else:
            win_rate = 0
            avg_win = avg_loss = largest_win = largest_loss = profit_factor = 0
        
        # Risultati
        results = {
            'symbol': self.symbol,
            'timeframe': timeframe,
            'ema_period': ema_period,
            'required_candles': required_candles,
            'max_distance': max_distance,
            'days_back': days_back,
            'use_risk_management': use_risk_management,
            
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            
            'total_trades': len(trades),
            'winning_trades': len(winning_trades) if trades else 0,
            'losing_trades': len(losing_trades) if trades else 0,
            'win_rate': win_rate,
            
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'total_fees': total_fees,
            
            'trades': trades,
            'timestamp': datetime.now().isoformat()
        }
        
        # Stampa risultati
        self.print_results(results)
        
        # Salva risultati dettagliati per i grafici
        results['trades_data'] = trades
        results['price_data'] = {
            'timestamps': data.index.tolist(),
            'prices': closes.tolist(),
            'ema_values': ema_values.tolist()
        }
        
        # Crea grafico se richiesto
        if create_chart:
            chart_path = self.create_backtest_chart(results, self.symbol, timeframe, ema_period)
            results['chart_path'] = chart_path
        
        return results
    
    def create_backtest_chart(self, results, symbol, timeframe, ema_period):
        """
        Crea grafico del backtest con prezzi, EMA e trade points
        """
        try:
            # Setup matplotlib per ambiente non-GUI
            plt.style.use('default')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), 
                                         gridspec_kw={'height_ratios': [3, 1]})
            
            # Dati per il grafico
            price_data = results['price_data']
            timestamps = pd.to_datetime(price_data['timestamps'])
            prices = price_data['prices']
            ema_values = price_data['ema_values']
            trades = results['trades_data']
            
            # Grafico principale - Prezzi e EMA
            ax1.plot(timestamps, prices, label=f'{symbol} Price', color='black', linewidth=0.8)
            ax1.plot(timestamps, ema_values, label=f'EMA({ema_period})', color='blue', linewidth=1.2)
            
            # Aggiungi punti di entrata e uscita
            for trade in trades:
                entry_time = pd.to_datetime(trade['entry_time'])
                exit_time = pd.to_datetime(trade['exit_time'])
                entry_price = trade['entry_price']
                exit_price = trade['exit_price']
                side = trade['side']
                pnl = trade['pnl']
                
                # Colori basati su direzione e profitto
                if side == 'LONG':
                    entry_color = 'green' if pnl > 0 else 'darkgreen'
                    exit_color = 'lightgreen' if pnl > 0 else 'red'
                    entry_marker = '^'
                    exit_marker = 'v'
                else:  # SHORT
                    entry_color = 'red' if pnl > 0 else 'darkred'
                    exit_color = 'lightcoral' if pnl > 0 else 'darkred'
                    entry_marker = 'v'
                    exit_marker = '^'
                
                # Punti di entrata
                ax1.scatter(entry_time, entry_price, color=entry_color, 
                           marker=entry_marker, s=100, zorder=5,
                           label=f'{side} Entry' if side not in [t['side'] for t in trades[:trades.index(trade)]] else "")
                
                # Punti di uscita
                ax1.scatter(exit_time, exit_price, color=exit_color,
                           marker=exit_marker, s=100, zorder=5,
                           label=f'{side} Exit' if side not in [t['side'] for t in trades[:trades.index(trade)]] else "")
                
                # Linea di connessione
                alpha = 0.3
                color = 'green' if pnl > 0 else 'red'
                ax1.plot([entry_time, exit_time], [entry_price, exit_price], 
                        color=color, alpha=alpha, linewidth=1, linestyle='--')
            
            # Formattazione grafico principale
            ax1.set_title(f'{symbol} Backtest Results - {timeframe}m Timeframe\n'
                         f'Total Return: {results["total_return_pct"]:.2f}% | '
                         f'Win Rate: {results["win_rate"]:.1f}% | '
                         f'Trades: {results["total_trades"]}', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Price (USD)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper left')
            
            # Formatta asse X
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(timestamps)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # Grafico inferiore - Equity Curve
            capital_history = [results['initial_capital']]
            trade_times = [timestamps[0]]
            
            for trade in trades:
                # Aggiungi il punto di chiusura trade
                exit_time = pd.to_datetime(trade['exit_time'])
                current_capital = capital_history[-1] + trade['pnl']
                capital_history.append(current_capital)
                trade_times.append(exit_time)
            
            # Linea equity
            ax2.plot(trade_times, capital_history, color='purple', linewidth=2, marker='o', markersize=4)
            ax2.axhline(y=results['initial_capital'], color='gray', linestyle='--', alpha=0.7, label='Initial Capital')
            
            # Colorazione profitto/perdita
            final_capital = capital_history[-1]
            fill_color = 'lightgreen' if final_capital > results['initial_capital'] else 'lightcoral'
            ax2.fill_between(trade_times, capital_history, results['initial_capital'], 
                           alpha=0.3, color=fill_color)
            
            ax2.set_title('Equity Curve', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Capital (USD)', fontsize=10)
            ax2.set_xlabel('Time', fontsize=10)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Formatta asse X inferiore
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # Aggiungi statistiche come testo
            stats_text = (f"Max Drawdown: {results.get('max_drawdown', 0):.2f}%\n"
                         f"Profit Factor: {results['profit_factor']:.2f}\n"
                         f"Avg Win: ${results['avg_win']:.2f}\n"
                         f"Avg Loss: ${results['avg_loss']:.2f}\n"
                         f"Total Fees: ${results['total_fees']:.2f}")
            
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', 
                    facecolor='white', alpha=0.8), fontsize=9)
            
            # Salva grafico
            charts_dir = Path("backtest_charts")
            charts_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{symbol}_{timeframe}_{timestamp}.png"
            chart_path = charts_dir / filename
            
            plt.tight_layout()
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()  # Chiudi per liberare memoria
            
            print(f"📊 Grafico salvato: {chart_path}")
            return str(chart_path)
            
        except Exception as e:
            print(f"⚠️ Errore creazione grafico: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def print_results(self, results):
        """Stampa risultati formattati"""
        print(f"\n{'='*60}")
        print(f"📊 BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"💰 PERFORMANCE:")
        print(f"   Initial Capital: ${results['initial_capital']:,.2f}")
        print(f"   Final Capital: ${results['final_capital']:,.2f}")
        print(f"   Total Return: ${results['total_return']:+,.2f} ({results['total_return_pct']:+.2f}%)")
        
        print(f"\n📈 TRADES:")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Winning Trades: {results['winning_trades']}")
        print(f"   Losing Trades: {results['losing_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1f}%")
        
        if results['total_trades'] > 0:
            print(f"\n💵 P&L ANALYSIS:")
            print(f"   Average Win: ${results['avg_win']:+.2f}")
            print(f"   Average Loss: ${results['avg_loss']:+.2f}")
            print(f"   Largest Win: ${results['largest_win']:+.2f}")
            print(f"   Largest Loss: ${results['largest_loss']:+.2f}")
            print(f"   Profit Factor: {results['profit_factor']:.2f}")
            print(f"   Total Fees: ${results['total_fees']:,.2f}")
    
    def save_results(self, results):
        """Salva risultati in JSON"""
        try:
            # Crea directory se non esiste
            results_dir = Path("backtest_results")
            results_dir.mkdir(exist_ok=True)
            
            # Nome file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simple_backtest_{results['symbol']}_{results['timeframe']}_{timestamp}.json"
            filepath = results_dir / filename
            
            # Salva
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"💾 Results saved to: {filepath}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

def main():
    """Test del sistema"""
    print("🚀 Testing Simple Backtest Engine")
    
    # Crea engine
    engine = SimpleBacktestEngine("BTCUSDT", 1000)
    
    # Test base
    results = engine.run_backtest(
        ema_period=10,
        required_candles=3,
        max_distance=1.0,
        timeframe='30',
        days_back=14,  # Test con meno giorni per essere veloce
        use_risk_management=True
    )
    
    if results:
        print("✅ Test completato con successo!")
        engine.save_results(results)
    else:
        print("❌ Test fallito!")

if __name__ == "__main__":
    main()
