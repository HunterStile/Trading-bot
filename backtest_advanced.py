#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Backtesting Engine
Engine di backtest modulare che può usare qualsiasi strategia
Supporta multiple strategie, risk management avanzato e analisi dettagliate
"""

import sys
from datetime import datetime, timedelta
import traceback
from typing import Dict, List, Optional, Type
import importlib

try:
    from config import *
    from trading_functions import get_kline_data, get_kline_data_with_dates
    from strategies.base_strategy import BaseStrategy
    from strategies.ema_strategy import EMAStrategy
    from strategies.triple_confirmation import TripleConfirmationStrategy
    print("✅ Import delle configurazioni avanzate riuscito!")
except ImportError as e:
    print(f"❌ Errore nell'import: {e}")
    sys.exit(1)

class AdvancedBacktestEngine:
    """
    Engine di backtest avanzato con supporto per strategie modulari
    """
    
    def __init__(self, simbolo: str, strategy: BaseStrategy, capitale_iniziale: float = 10000):
        """
        Inizializza l'engine di backtest
        
        Args:
            simbolo: Simbolo da testare (es. BTCUSDT)
            strategy: Istanza della strategia da testare
            capitale_iniziale: Capitale iniziale per il test
        """
        self.simbolo = simbolo
        self.strategy = strategy
        self.capitale_iniziale = capitale_iniziale
        self.capitale_attuale = capitale_iniziale
        self.categoria = "linear"
        
        # Stato del backtest
        self.posizione_aperta = False
        self.tipo_posizione = None  # 'long', 'short'
        self.prezzo_entrata = 0
        self.quantita = 0
        self.timestamp_entrata = 0
        
        # Tracking drawdown per trade
        self.trade_peak_value = 0
        self.trade_max_drawdown = 0
        
        # Risultati
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
        # Statistiche
        self.max_drawdown = 0
        self.peak_capital = capitale_iniziale
        
        # Date specifiche per test
        self.specific_start_date = None
        self.specific_end_date = None
        
    def run_backtest(self, timeframe: str = "D", giorni_backtest: int = 365, 
                    percentuale_capitale_per_trade: float = 100) -> Dict:
        """
        Esegue il backtest completo
        
        Args:
            timeframe: Timeframe per il test
            giorni_backtest: Numero di giorni da testare
            percentuale_capitale_per_trade: Percentuale di capitale da usare per trade
            
        Returns:
            Dizionario con i risultati del backtest
        """
        self.print_header(f"BACKTEST AVANZATO - {self.simbolo}")
        print(f"📈 Simbolo: {self.simbolo}")
        print(f"🎯 Strategia: {self.strategy.name}")
        print(f"⏰ Timeframe: {timeframe}")
        print(f"💰 Capitale iniziale: ${self.capitale_iniziale:,.2f}")
        print(f"💰 Capitale per trade: {percentuale_capitale_per_trade}%")
        print(f"📅 Periodo test: {giorni_backtest} giorni")
        
        # Calcola il numero di candele necessarie
        limit = self._calculate_limit(timeframe, giorni_backtest)
        print(f"📥 Richieste {giorni_backtest} giorni di dati...")
        
        # Ottieni dati storici - usa download con date specifiche se impostate
        if self.specific_start_date and self.specific_end_date:
            print(f"📅 Download con date specifiche: {self.specific_start_date} → {self.specific_end_date}")
            kline_data = self._get_extended_historical_data(timeframe, giorni_backtest)
        else:
            print(f"📥 Download: {limit} candele...")
            kline_data = get_kline_data(self.categoria, self.simbolo, timeframe, limit=limit)
        
        if not kline_data or len(kline_data) < 50:  # Minimo dati necessari
            print("❌ Dati insufficienti per il backtest")
            return self._empty_results()
        
        # Prepara i dati (inverti per avere ordine cronologico)
        ohlcv_data = list(reversed(kline_data))
        
        print(f"✅ Elaboro {len(ohlcv_data)} candele per il backtest...")
        
        # Calcola indicatori usando la strategia
        print("📊 Calcolo indicatori...")
        indicators = self.strategy.calculate_indicators(ohlcv_data)
        
        if indicators.get('insufficient_data', False):
            print("❌ Dati insufficienti per calcolare gli indicatori")
            return self._empty_results()
        
        print(f"📊 Range prezzi: ${min(indicators['closes']):.2f} - ${max(indicators['closes']):.2f}")
        
        # Mostra range date se disponibili
        if indicators['timestamps']:
            start_dt = datetime.fromtimestamp(indicators['timestamps'][0]/1000)
            end_dt = datetime.fromtimestamp(indicators['timestamps'][-1]/1000)
            print(f"📅 Range date: {start_dt.strftime('%d-%b-%Y')} → {end_dt.strftime('%d-%b-%Y')}")
        
        # Esegui simulazione trading
        print("🔄 Avvio simulazione trading...")
        self._simulate_trading(indicators, percentuale_capitale_per_trade)
        
        # Chiudi eventuale posizione aperta alla fine
        if self.posizione_aperta:
            self._close_position(indicators['closes'][-1], indicators['timestamps'][-1], "FINE BACKTEST")
        
        # Genera risultati
        results = self._generate_results()
        
        # Mostra analisi
        self._print_results(results)
        
        return results
    
    def _simulate_trading(self, indicators: Dict, percentuale_capitale: float):
        """
        Simula il trading usando la strategia
        
        Args:
            indicators: Dizionario con tutti gli indicatori
            percentuale_capitale: Percentuale di capitale per trade
        """
        data_length = len(indicators['closes'])
        
        # Inizia da un punto con dati sufficienti per gli indicatori
        start_index = max(50, len(indicators['ema']) - data_length + 50) if 'ema' in indicators else 50
        
        for i in range(start_index, data_length):
            # Prepara dati per la strategia (fino al punto corrente)
            current_data = self._prepare_current_data(indicators, i)
            
            # Genera segnale
            signal = self.strategy.generate_signals(current_data)
            
            current_price = indicators['closes'][i]
            current_timestamp = indicators['timestamps'][i]
            
            # Valida segnale
            if not self.strategy.validate_signal(signal, current_price, current_data):
                signal = 'hold'
            
            # Esegui azione basata sul segnale
            self._execute_signal(signal, current_price, current_timestamp, percentuale_capitale)
            
            # Aggiorna drawdown del trade se posizione aperta
            if self.posizione_aperta:
                self._update_trade_drawdown(current_price)
            
            # Registra equity curve
            self._update_equity_curve(current_price, current_timestamp)
    
    def _prepare_current_data(self, indicators: Dict, current_index: int) -> Dict:
        """
        Prepara i dati fino al punto corrente per la strategia
        
        Args:
            indicators: Tutti gli indicatori
            current_index: Indice corrente
            
        Returns:
            Dati fino al punto corrente
        """
        current_data = {}
        
        for key, values in indicators.items():
            if isinstance(values, list) and len(values) > current_index:
                current_data[key] = values[:current_index + 1]
            else:
                current_data[key] = values
        
        return current_data
    
    def _execute_signal(self, signal: str, price: float, timestamp: int, percentuale_capitale: float):
        """
        Esegue il segnale di trading
        
        Args:
            signal: Segnale da eseguire
            price: Prezzo corrente
            timestamp: Timestamp corrente
            percentuale_capitale: Percentuale di capitale da usare
        """
        if signal == 'buy' and not self.posizione_aperta:
            self._open_position('long', price, timestamp, percentuale_capitale)
            
        elif signal == 'sell' and not self.posizione_aperta:
            self._open_position('short', price, timestamp, percentuale_capitale)
            
        elif signal == 'close' and self.posizione_aperta:
            self._close_position(price, timestamp, "SEGNALE STRATEGIA")
    
    def _open_position(self, tipo: str, price: float, timestamp: int, percentuale_capitale: float):
        """
        Apre una nuova posizione
        
        Args:
            tipo: 'long' o 'short'
            price: Prezzo di entrata
            timestamp: Timestamp di entrata
            percentuale_capitale: Percentuale di capitale da usare
        """
        if self.posizione_aperta:
            return False
        
        # Calcola capitale da investire
        capitale_investito = (self.capitale_attuale * percentuale_capitale) / 100
        
        # Calcola quantità
        self.quantita = capitale_investito / price
        
        # Aggiorna stato
        self.posizione_aperta = True
        self.tipo_posizione = tipo
        self.prezzo_entrata = price
        self.timestamp_entrata = timestamp
        
        # Inizializza tracking drawdown per questo trade
        self.trade_peak_value = capitale_investito  # Valore iniziale del trade
        self.trade_max_drawdown = 0
        
        # Aggiorna strategia
        dt = datetime.fromtimestamp(timestamp / 1000)
        self.strategy.update_position(tipo, price, dt)
        
        # Registra trade
        self._add_trade('COMPRA' if tipo == 'long' else 'VENDI', price, self.quantita, 
                       timestamp, f"{tipo.upper()}: Apertura posizione")
        
        # Formatta data per il log
        dt = datetime.fromtimestamp(timestamp / 1000)
        data_formattata = dt.strftime('%d-%b-%Y %H:%M')
        
        print(f"   💰 Aperta posizione {tipo.upper()}: "
              f"{self.quantita:.6f} {self.simbolo[:3]} @ ${price:,.2f} "
              f"({data_formattata}) - Investiti: ${capitale_investito:.2f}")
        
        return True
    
    def _close_position(self, price: float, timestamp: int, motivo: str):
        """
        Chiude la posizione corrente
        
        Args:
            price: Prezzo di chiusura
            timestamp: Timestamp di chiusura
            motivo: Motivo della chiusura
        """
        if not self.posizione_aperta:
            return False
        
        # Calcola P&L
        capitale_investito = self.quantita * self.prezzo_entrata
        valore_attuale = self.quantita * price
        
        if self.tipo_posizione == 'long':
            pnl = valore_attuale - capitale_investito
            self.capitale_attuale = valore_attuale
        else:  # short
            pnl = capitale_investito - valore_attuale
            self.capitale_attuale = capitale_investito + pnl
        
        percentuale_pnl = (pnl / capitale_investito) * 100
        
        # Registra trade con max drawdown
        tipo_chiusura = 'VENDI' if self.tipo_posizione == 'long' else 'COMPRA'
        motivo_completo = f"{motivo} - P&L: ${pnl:.2f} ({percentuale_pnl:+.2f}%) - Max DD: {self.trade_max_drawdown:.2f}%"
        self._add_trade(tipo_chiusura, price, self.quantita, timestamp, motivo_completo)
        
        # Formatta data per il log
        dt = datetime.fromtimestamp(timestamp / 1000)
        data_formattata = dt.strftime('%d-%b-%Y %H:%M')
        
        print(f"   🔚 Chiusa posizione {self.tipo_posizione.upper()}: "
              f"{self.quantita:.6f} {self.simbolo[:3]} @ ${price:,.2f} "
              f"({data_formattata}) - P&L: ${pnl:.2f} ({percentuale_pnl:+.2f}%) "
              f"- Max DD: {self.trade_max_drawdown:.2f}% - Capitale: ${self.capitale_attuale:.2f}")
        
        # Aggiorna drawdown
        self._update_drawdown()
        
        # Reset stato
        self.posizione_aperta = False
        self.tipo_posizione = None
        self.prezzo_entrata = 0
        self.quantita = 0
        self.timestamp_entrata = 0
        
        # Reset drawdown del trade
        self.trade_peak_value = 0
        self.trade_max_drawdown = 0
        
        # Aggiorna strategia
        self.strategy.close_position()
        
        return True
    
    def _add_trade(self, tipo: str, price: float, quantita: float, timestamp: int, motivo: str):
        """
        Aggiunge un trade alla lista
        """
        trade = {
            'timestamp': timestamp,
            'tipo': tipo,
            'prezzo': price,
            'quantita': quantita,
            'capitale': self.capitale_attuale,
            'motivo': motivo
        }
        self.trades.append(trade)
    
    def _update_equity_curve(self, price: float, timestamp: int):
        """
        Aggiorna la curva dell'equity
        """
        # Calcola valore unrealized se posizione aperta
        unrealized_pnl = 0
        if self.posizione_aperta:
            capitale_investito = self.quantita * self.prezzo_entrata
            valore_attuale = self.quantita * price
            
            if self.tipo_posizione == 'long':
                unrealized_pnl = valore_attuale - capitale_investito
            else:
                unrealized_pnl = capitale_investito - valore_attuale
        
        equity_point = {
            'timestamp': timestamp,
            'prezzo': price,
            'capitale_realized': self.capitale_attuale,
            'capitale_unrealized': self.capitale_attuale + unrealized_pnl,
            'unrealized_pnl': unrealized_pnl
        }
        self.equity_curve.append(equity_point)
    
    def _update_trade_drawdown(self, current_price: float):
        """
        Aggiorna il drawdown del trade corrente
        
        Args:
            current_price: Prezzo corrente
        """
        if not self.posizione_aperta:
            return
        
        # Calcola valore corrente del trade
        capitale_investito = self.quantita * self.prezzo_entrata
        valore_attuale = self.quantita * current_price
        
        if self.tipo_posizione == 'long':
            current_trade_value = valore_attuale
        else:  # short
            # Per short: valore = capitale_investito + (capitale_investito - valore_attuale)
            current_trade_value = capitale_investito + (capitale_investito - valore_attuale)
        
        # Aggiorna peak value del trade
        if current_trade_value > self.trade_peak_value:
            self.trade_peak_value = current_trade_value
        
        # Calcola drawdown del trade
        if self.trade_peak_value > 0:
            current_trade_drawdown = ((self.trade_peak_value - current_trade_value) / self.trade_peak_value) * 100
            if current_trade_drawdown > self.trade_max_drawdown:
                self.trade_max_drawdown = current_trade_drawdown
    
    def _update_drawdown(self):
        """
        Aggiorna il maximum drawdown
        """
        if self.capitale_attuale > self.peak_capital:
            self.peak_capital = self.capitale_attuale
        
        current_drawdown = ((self.peak_capital - self.capitale_attuale) / self.peak_capital) * 100
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
    
    def _calculate_limit(self, timeframe: str, giorni: int) -> int:
        """
        Calcola il numero di candele necessarie
        """
        if timeframe == "M":
            limit = max(24, giorni // 30 + 10)
        elif timeframe == "W":
            limit = max(52, giorni // 7 + 10)
        elif timeframe == "D":
            limit = max(giorni + 50, 100)
        elif timeframe == "720":  # 12 ore
            limit = (giorni * 2) + 50
        elif timeframe == "360":  # 6 ore
            limit = (giorni * 4) + 50
        elif timeframe == "240":  # 4 ore
            limit = (giorni * 6) + 50
        elif timeframe == "120":  # 2 ore
            limit = (giorni * 12) + 50
        elif timeframe == "60":   # 1 ora
            limit = (giorni * 24) + 50
        elif timeframe == "30":   # 30 minuti
            limit = (giorni * 48) + 50
        elif timeframe == "15":   # 15 minuti
            limit = (giorni * 96) + 50
        elif timeframe == "5":    # 5 minuti
            limit = (giorni * 288) + 50
        elif timeframe == "3":    # 3 minuti
            limit = (giorni * 480) + 50
        elif timeframe == "1":    # 1 minuto
            limit = (giorni * 1440) + 50
        else:
            limit = 500
        
        return limit  # Rimosso limite artificiale di 1000
    
    def _empty_results(self) -> Dict:
        """
        Restituisce risultati vuoti in caso di errore
        """
        return {
            'success': False,
            'error': 'Dati insufficienti',
            'capital_initial': self.capitale_iniziale,
            'capital_final': self.capitale_iniziale,
            'total_return': 0,
            'total_return_percent': 0,
            'total_trades': 0,
            'win_rate': 0,
            'max_drawdown': 0
        }
    
    def _generate_results(self) -> Dict:
        """
        Genera statistiche complete del backtest
        """
        # Statistiche base
        rendimento_totale = self.capitale_attuale - self.capitale_iniziale
        rendimento_percentuale = (rendimento_totale / self.capitale_iniziale) * 100
        numero_trades = len(self.trades) // 2
        
        # Analizza trades
        trades_analysis = self._analyze_trades()
        
        # Statistiche avanzate
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        return {
            'success': True,
            'strategy_name': self.strategy.name,
            'symbol': self.simbolo,
            'timeframe': self.strategy.timeframe,
            
            # Capitale
            'capital_initial': self.capitale_iniziale,
            'capital_final': self.capitale_attuale,
            'peak_capital': self.peak_capital,
            
            # Rendimenti
            'total_return': rendimento_totale,
            'total_return_percent': rendimento_percentuale,
            
            # Trades
            'total_trades': numero_trades,
            'winning_trades': trades_analysis['winning_trades'],
            'losing_trades': trades_analysis['losing_trades'],
            'win_rate': trades_analysis['win_rate'],
            
            # P&L
            'best_trade': trades_analysis['best_trade'],
            'worst_trade': trades_analysis['worst_trade'],
            'avg_win': trades_analysis['avg_win'],
            'avg_loss': trades_analysis['avg_loss'],
            
            # Rischio
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            
            # Dati grezzi
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'strategy_parameters': self.strategy.get_parameters()
        }
    
    def _analyze_trades(self) -> Dict:
        """
        Analizza tutti i trades eseguiti
        """
        if len(self.trades) < 2:
            return {
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        trades_pnl = []
        
        # Calcola P&L per ogni trade completo
        for i in range(0, len(self.trades), 2):
            if i + 1 < len(self.trades):
                apertura = self.trades[i]
                chiusura = self.trades[i + 1]
                
                if apertura['tipo'] == 'COMPRA':
                    pnl = (chiusura['prezzo'] - apertura['prezzo']) * apertura['quantita']
                else:
                    pnl = (apertura['prezzo'] - chiusura['prezzo']) * apertura['quantita']
                
                trades_pnl.append(pnl)
        
        if not trades_pnl:
            return {
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        winning_trades = [t for t in trades_pnl if t > 0]
        losing_trades = [t for t in trades_pnl if t < 0]
        
        return {
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades_pnl)) * 100 if trades_pnl else 0,
            'best_trade': max(trades_pnl) if trades_pnl else 0,
            'worst_trade': min(trades_pnl) if trades_pnl else 0,
            'avg_win': sum(winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(losing_trades) / len(losing_trades) if losing_trades else 0
        }
    
    def _calculate_sharpe_ratio(self) -> float:
        """
        Calcola il Sharpe Ratio semplificato
        """
        if len(self.equity_curve) < 2:
            return 0
        
        # Calcola rendimenti giornalieri
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_capital = self.equity_curve[i-1]['capitale_unrealized']
            curr_capital = self.equity_curve[i]['capitale_unrealized']
            
            if prev_capital > 0:
                daily_return = (curr_capital - prev_capital) / prev_capital
                returns.append(daily_return)
        
        if len(returns) < 2:
            return 0
        
        # Calcola media e std
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_return = variance ** 0.5
        
        # Sharpe ratio (assumendo risk-free rate = 0)
        return (avg_return / std_return) if std_return > 0 else 0
    
    def print_header(self, title: str):
        """
        Stampa header formattato
        """
        print("\n" + "="*60)
        print(f"📊 {title}")
        print("="*60)
    
    def _print_results(self, results: Dict):
        """
        Stampa i risultati del backtest
        """
        if not results['success']:
            print(f"\n❌ BACKTEST FALLITO: {results.get('error', 'Errore sconosciuto')}")
            return
        
        self.print_header("RISULTATI BACKTEST AVANZATO")
        
        # Statistiche generali
        print(f"🎯 Strategia: {results['strategy_name']}")
        print(f"📈 Simbolo: {results['symbol']}")
        print(f"⏰ Timeframe: {results['timeframe']}")
        print(f"💰 Capitale iniziale: ${results['capital_initial']:,.2f}")
        print(f"💰 Capitale finale: ${results['capital_final']:,.2f}")
        print(f"📈 Rendimento: ${results['total_return']:,.2f} ({results['total_return_percent']:.2f}%)")
        print(f"📊 Max Drawdown: {results['max_drawdown']:.2f}%")
        print(f"📊 Sharpe Ratio: {results['sharpe_ratio']:.3f}")
        
        # Trades
        print(f"\n🔄 ANALISI TRADES:")
        print(f"📊 Numero totale trades: {results['total_trades']}")
        print(f"✅ Trades vincenti: {results['winning_trades']}")
        print(f"❌ Trades perdenti: {results['losing_trades']}")
        print(f"🎯 Win Rate: {results['win_rate']:.1f}%")
        
        if results['winning_trades'] > 0:
            print(f"💚 Guadagno medio vincente: ${results['avg_win']:.2f}")
        
        if results['losing_trades'] > 0:
            print(f"💔 Perdita media perdente: ${results['avg_loss']:.2f}")
        
        print(f"🎯 Miglior trade: ${results['best_trade']:.2f}")
        print(f"💥 Peggior trade: ${results['worst_trade']:.2f}")
        
        # Ultimi trades con date complete
        if results['trades']:
            print(f"\n📋 ULTIMI TRADES:")
            for trade in results['trades'][-6:]:
                dt = datetime.fromtimestamp(trade['timestamp']/1000)
                # Formato data più leggibile: 17-Sep-2020 02:00
                data_formattata = dt.strftime('%d-%b-%Y %H:%M')
                print(f"   {trade['tipo']} {trade['quantita']:.6f} @ ${trade['prezzo']:.2f} "
                      f"({data_formattata}) - {trade['motivo']}")
        
        # Raccomandazioni
        print(f"\n💡 RACCOMANDAZIONI:")
        if results['total_return_percent'] > 10:
            print("   ✅ Strategia molto promettente! Ottimi risultati")
        elif results['total_return_percent'] > 5:
            print("   ✅ Strategia promettente! Considera l'uso con capitale reale")
        elif results['total_return_percent'] > 0:
            print("   ⚠️  Strategia marginalmente profittevole. Ottimizza i parametri")
        else:
            print("   ❌ Strategia non profittevole. Rivedi parametri o strategia")
        
        if results['win_rate'] > 60:
            print("   ✅ Win rate eccellente (>60%)")
        elif results['win_rate'] > 50:
            print("   ⚠️  Win rate accettabile (>50%)")
        else:
            print("   ❌ Win rate troppo basso (<50%)")
        
        if results['max_drawdown'] < 10:
            print("   ✅ Drawdown accettabile (<10%)")
        elif results['max_drawdown'] < 20:
            print("   ⚠️  Drawdown moderato (10-20%)")
        else:
            print("   ❌ Drawdown elevato (>20%) - Riduci rischio")

    def _get_extended_historical_data(self, timeframe: str, giorni_backtest: int) -> List:
        """
        Scarica dati storici per periodo specifico usando date impostate o giorni di backtest
        
        Args:
            timeframe: Timeframe dei dati
            giorni_backtest: Numero di giorni richiesti (può essere ignorato se usiamo date specifiche)
            
        Returns:
            Lista completa di candele OHLCV
        """
        if self.specific_start_date and self.specific_end_date:
            # Usa date specifiche
            start_date = datetime.strptime(self.specific_start_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.specific_end_date, "%Y-%m-%d") + timedelta(days=1)  # Include l'ultimo giorno
            print(f"📅 Periodo specifico: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
            
            # Converti in timestamp (millisecondi per Bybit)
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
        else:
            # Usa giorni_backtest
            end_date = datetime.now()
            start_date = end_date - timedelta(days=giorni_backtest + 10)
            print(f"📅 Periodo calcolato: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
            
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
        
        # Calcola candele per giorno
        candele_per_giorno = self._get_candles_per_day(timeframe)
        giorni_totali = (end_date - start_date).days
        candele_totali_stimate = giorni_totali * candele_per_giorno
        
        print(f"📊 Periodo: {giorni_totali} giorni = ~{candele_totali_stimate} candele")
        
        # Se possiamo scaricare tutto in una volta (≤1000 candele)
        if candele_totali_stimate <= 1000:
            print(f"📥 Download diretto con date: {start_timestamp} → {end_timestamp}")
            
            # Usa la nuova funzione con date specifiche
            kline_data = get_kline_data_with_dates(
                self.categoria, 
                self.simbolo, 
                timeframe,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                limit=min(candele_totali_stimate + 50, 1000)
            )
            
            if kline_data:
                print(f"✅ Scaricate {len(kline_data)} candele per il periodo richiesto")
                return kline_data
            else:
                print("❌ Nessun dato ottenuto con date specifiche, provo download normale")
                return get_kline_data(self.categoria, self.simbolo, timeframe, limit=1000)
        
        else:
            # Per periodi molto lunghi, usa download multipli
            print(f"📥 Download multipli necessari ({candele_totali_stimate} candele)")
            return self._download_with_date_chunks(timeframe, start_date, end_date)
    
    def _get_candles_per_day(self, timeframe: str) -> int:
        """
        Calcola quante candele ci sono in un giorno per il timeframe
        """
        if timeframe == "D":
            return 1
        elif timeframe == "720":  # 12 ore
            return 2
        elif timeframe == "360":  # 6 ore
            return 4
        elif timeframe == "240":  # 4 ore
            return 6
        elif timeframe == "120":  # 2 ore
            return 12
        elif timeframe == "60":   # 1 ora
            return 24
        elif timeframe == "30":   # 30 minuti
            return 48
        elif timeframe == "15":   # 15 minuti
            return 96
        elif timeframe == "5":    # 5 minuti
            return 288
        elif timeframe == "3":    # 3 minuti
            return 480
        elif timeframe == "1":    # 1 minuto
            return 1440
        else:
            return 24  # Default 1 ora
    
    def _download_with_date_chunks(self, timeframe: str, start_date: datetime, end_date: datetime) -> List:
        """
        Scarica dati in chunk usando date specifiche (per periodi molto lunghi)
        """
        import time as time_module
        
        all_data = []
        candele_per_giorno = self._get_candles_per_day(timeframe)
        
        # Calcola dimensione chunk (giorni per avere ~900 candele per evitare il limite 1000)
        giorni_per_chunk = max(1, min(900 // candele_per_giorno, 30))
        
        current_end = end_date
        chunk_num = 0
        
        print(f"📦 Chunk size: {giorni_per_chunk} giorni (~{giorni_per_chunk * candele_per_giorno} candele)")
        
        while current_end > start_date:
            chunk_num += 1
            current_start = max(start_date, current_end - timedelta(days=giorni_per_chunk))
            
            print(f"📥 Chunk {chunk_num}: {current_start.strftime('%Y-%m-%d')} → {current_end.strftime('%Y-%m-%d')}")
            
            try:
                # Converti datetime a timestamp (millisecondi)
                start_timestamp = int(current_start.timestamp() * 1000)
                end_timestamp = int(current_end.timestamp() * 1000)
                
                # Usa download con date specifiche
                chunk_data = get_kline_data_with_dates(
                    self.categoria,
                    self.simbolo,
                    timeframe,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    limit=1000
                )
                
                if chunk_data:
                    all_data.extend(chunk_data)
                    print(f"   ✅ Scaricate {len(chunk_data)} candele")
                else:
                    print(f"   ⚠️  Nessuna candela per questo chunk")
                
                # Pausa per evitare rate limiting
                time_module.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Errore chunk {chunk_num}: {e}")
            
            # Sposta alla data precedente
            current_end = current_start - timedelta(days=1)
        
        # Rimuovi duplicati e ordina
        if all_data:
            # Rimuovi duplicati basati su timestamp
            seen_timestamps = set()
            unique_data = []
            
            for candle in all_data:
                timestamp = int(candle[0])
                if timestamp not in seen_timestamps:
                    seen_timestamps.add(timestamp)
                    unique_data.append(candle)
            
            # Ordina per timestamp (più recente prima, come Bybit)
            unique_data.sort(key=lambda x: int(x[0]), reverse=True)
            
            print(f"✅ Download completato: {len(unique_data)} candele uniche")
            return unique_data
        
        print("❌ Nessun dato scaricato")
        return []

# ═══════════════════════════════════════════════════════════════
# 🎯 FUNZIONI DI UTILITÀ E MENU
# ═══════════════════════════════════════════════════════════════

def get_available_strategies() -> Dict[str, Type[BaseStrategy]]:
    """
    Restituisce tutte le strategie disponibili
    
    Returns:
        Dizionario {nome: classe_strategia}
    """
    return {
        'EMA': EMAStrategy,
        'Triple Confirmation': TripleConfirmationStrategy
    }

def create_strategy(strategy_name: str, timeframe: str = "D") -> Optional[BaseStrategy]:
    """
    Crea un'istanza della strategia richiesta
    
    Args:
        strategy_name: Nome della strategia
        timeframe: Timeframe per la strategia
        
    Returns:
        Istanza della strategia o None se non trovata
    """
    strategies = get_available_strategies()
    
    if strategy_name in strategies:
        return strategies[strategy_name](timeframe)
    
    return None

def menu_advanced_backtest():
    """
    Menu principale per il backtest avanzato
    """
    print("\n🚀 ADVANCED BACKTESTING ENGINE")
    print("="*50)
    
    while True:
        print("\n📊 MENU BACKTEST AVANZATO:")
        print("1. 🎯 Triple Confirmation Strategy - BTCUSDT Daily")
        print("2. 📈 EMA Strategy - BTCUSDT Daily") 
        print("3. 🔧 Test strategia personalizzata")
        print("4. ⚡ Confronto strategie")
        print("5. 📅 Test periodo specifico (Bear/Bull/Crash)")
        print("6. 📋 Lista strategie disponibili")
        print("0. ❌ Esci")
        
        scelta = input("\n👉 Scegli un'opzione: ").strip()
        
        if scelta == "1":
            test_triple_confirmation()
        elif scelta == "2":
            test_ema_strategy()
        elif scelta == "3":
            test_custom_strategy()
        elif scelta == "4":
            compare_strategies()
        elif scelta == "5":
            test_specific_period()
        elif scelta == "6":
            list_strategies()
        elif scelta == "0":
            print("👋 Uscita dal backtesting avanzato...")
            break
        else:
            print("❌ Opzione non valida!")

def test_triple_confirmation():
    """
    Test della Triple Confirmation Strategy
    """
    print(f"\n🎯 TRIPLE CONFIRMATION STRATEGY TEST")
    
    simbolo = input("📝 Simbolo (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    timeframe = input("⏰ Timeframe (default D): ").strip() or "D"
    giorni = int(input("📅 Giorni backtest (default 365): ") or "365")
    capitale = float(input("💰 Capitale iniziale (default 10000): ") or "10000")
    
    # Crea strategia
    strategy = TripleConfirmationStrategy(timeframe)
    
    # Mostra descrizione strategia
    print(strategy.get_strategy_description())
    
    # Configura parametri se richiesto
    if input("\n🔧 Vuoi modificare i parametri? (s/N): ").strip().lower() == 's':
        customize_strategy_parameters(strategy)
    
    # Esegui backtest
    engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
    results = engine.run_backtest(timeframe, giorni, 100)  # Usa tutto il capitale
    
    return results

def test_ema_strategy():
    """
    Test della EMA Strategy
    """
    print(f"\n📈 EMA STRATEGY TEST")
    
    simbolo = input("📝 Simbolo (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    timeframe = input("⏰ Timeframe (default D): ").strip() or "D"
    giorni = int(input("📅 Giorni backtest (default 365): ") or "365")
    capitale = float(input("💰 Capitale iniziale (default 10000): ") or "10000")
    
    # Crea strategia
    strategy = EMAStrategy(timeframe)
    
    # Mostra descrizione strategia
    print(strategy.get_strategy_description())
    
    # Configura parametri se richiesto
    if input("\n🔧 Vuoi modificare i parametri? (s/N): ").strip().lower() == 's':
        customize_strategy_parameters(strategy)
    
    # Esegui backtest
    engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
    results = engine.run_backtest(timeframe, giorni, 100)
    
    return results

def test_custom_strategy():
    """
    Test di una strategia personalizzata
    """
    print(f"\n🔧 TEST STRATEGIA PERSONALIZZATA")
    
    # Selezione strategia
    strategies = get_available_strategies()
    print("\n📋 Strategie disponibili:")
    for i, name in enumerate(strategies.keys(), 1):
        print(f"   {i}. {name}")
    
    try:
        choice = int(input("\n👉 Scegli strategia (numero): ")) - 1
        strategy_name = list(strategies.keys())[choice]
    except (ValueError, IndexError):
        print("❌ Selezione non valida")
        return
    
    # Parametri
    simbolo = input("📝 Simbolo (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    timeframe = input("⏰ Timeframe (default D): ").strip() or "D"
    giorni = int(input("📅 Giorni backtest (default 365): ") or "365")
    capitale = float(input("💰 Capitale iniziale (default 10000): ") or "10000")
    
    # Crea strategia
    strategy = create_strategy(strategy_name, timeframe)
    if not strategy:
        print("❌ Errore nella creazione della strategia")
        return
    
    # Configura parametri
    print(strategy.get_strategy_description())
    if input("\n🔧 Vuoi modificare i parametri? (s/N): ").strip().lower() == 's':
        customize_strategy_parameters(strategy)
    
    # Esegui backtest
    engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
    results = engine.run_backtest(timeframe, giorni, 100)
    
    return results

def customize_strategy_parameters(strategy: BaseStrategy):
    """
    Permette di personalizzare i parametri di una strategia
    
    Args:
        strategy: Strategia da personalizzare
    """
    print(f"\n🔧 PERSONALIZZAZIONE PARAMETRI - {strategy.name}")
    print("💡 Premi Enter per mantenere il valore corrente")
    
    current_params = strategy.get_parameters()
    new_params = {}
    
    for param_name, current_value in current_params.items():
        try:
            user_input = input(f"   {param_name} (current: {current_value}): ").strip()
            if user_input:
                # Prova a convertire nel tipo appropriato
                if isinstance(current_value, bool):
                    new_params[param_name] = user_input.lower() in ['true', 't', 'yes', 'y', '1']
                elif isinstance(current_value, int):
                    new_params[param_name] = int(user_input)
                elif isinstance(current_value, float):
                    new_params[param_name] = float(user_input)
                else:
                    new_params[param_name] = user_input
            else:
                new_params[param_name] = current_value
        except ValueError:
            print(f"   ⚠️  Valore non valido per {param_name}, mantengo {current_value}")
            new_params[param_name] = current_value
    
    strategy.set_parameters(**new_params)
    print("✅ Parametri aggiornati!")

def compare_strategies():
    """
    Confronta multiple strategie sullo stesso simbolo e timeframe
    """
    print(f"\n⚡ CONFRONTO STRATEGIE")
    
    simbolo = input("📝 Simbolo (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    timeframe = input("⏰ Timeframe (default D): ").strip() or "D"
    giorni = int(input("📅 Giorni backtest (default 365): ") or "365")
    capitale = float(input("💰 Capitale iniziale (default 10000): ") or "10000")
    
    strategies = get_available_strategies()
    results = {}
    
    print(f"\n🔄 Testando tutte le strategie su {simbolo} ({timeframe})...")
    
    for strategy_name, strategy_class in strategies.items():
        print(f"\n📊 Testando {strategy_name}...")
        
        try:
            strategy = strategy_class(timeframe)
            engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
            result = engine.run_backtest(timeframe, giorni, 100)
            
            if result['success']:
                results[strategy_name] = result
            else:
                print(f"❌ Errore nel test di {strategy_name}")
                
        except Exception as e:
            print(f"❌ Errore nel test di {strategy_name}: {e}")
    
    # Mostra confronto
    if results:
        print_strategy_comparison(results)
    else:
        print("❌ Nessun risultato valido ottenuto")

def print_strategy_comparison(results: Dict):
    """
    Stampa il confronto tra strategie
    
    Args:
        results: Dizionario con i risultati di ogni strategia
    """
    print("\n🏆 CONFRONTO RISULTATI STRATEGIE:")
    print("="*80)
    
    # Ordina per rendimento
    sorted_results = sorted(results.items(), 
                          key=lambda x: x[1]['total_return_percent'], 
                          reverse=True)
    
    print(f"{'STRATEGIA':<25} {'RENDIMENTO':<15} {'WIN RATE':<12} {'TRADES':<8} {'DRAWDOWN':<12}")
    print("-" * 80)
    
    for i, (strategy_name, result) in enumerate(sorted_results):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📊"
        
        print(f"{emoji} {strategy_name:<23} "
              f"{result['total_return_percent']:+.2f}%{'':<8} "
              f"{result['win_rate']:.1f}%{'':<7} "
              f"{result['total_trades']:<8} "
              f"{result['max_drawdown']:.2f}%")
    
    # Dettagli del vincitore
    if sorted_results:
        best_strategy, best_result = sorted_results[0]
        print(f"\n🏆 VINCITORE: {best_strategy}")
        print(f"📈 Rendimento: {best_result['total_return_percent']:.2f}%")
        print(f"💰 Capitale finale: ${best_result['capital_final']:,.2f}")
        print(f"🎯 Win Rate: {best_result['win_rate']:.1f}%")
        print(f"📊 Max Drawdown: {best_result['max_drawdown']:.2f}%")

def list_strategies():
    """
    Lista tutte le strategie disponibili con descrizioni
    """
    print(f"\n📋 STRATEGIE DISPONIBILI:")
    print("="*50)
    
    strategies = get_available_strategies()
    
    for i, (name, strategy_class) in enumerate(strategies.items(), 1):
        # Crea istanza temporanea per ottenere descrizione
        temp_strategy = strategy_class()
        
        print(f"\n{i}. 🎯 {name}")
        print(f"   Classe: {strategy_class.__name__}")
        print(f"   Descrizione: {temp_strategy.__doc__ or 'Nessuna descrizione disponibile'}")
        
        # Mostra parametri principali
        params = temp_strategy.get_parameters()
        if params:
            main_params = list(params.items())[:3]  # Primi 3 parametri
            param_str = ", ".join([f"{k}={v}" for k, v in main_params])
            print(f"   Parametri principali: {param_str}")

def test_specific_period():
    """
    Test su un periodo specifico con date precise
    """
    print(f"\n📅 TEST PERIODO SPECIFICO")
    
    simbolo = input("📝 Simbolo (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    timeframe = input("⏰ Timeframe (default D): ").strip() or "D"
    
    print("\n📅 Seleziona periodo:")
    print("1. 🐻 Bear Market 2022 (Gen-Dic 2022)")
    print("2. 🐂 Bull Run 2021 (Gen-Dic 2021)")
    print("3. 📉 Crash COVID 2020 (Feb-Ago 2020)")
    print("4. 🚀 Halving 2020 (Gen 2020-Gen 2021)")
    print("5. ⚡ Volatile 2018 (Gen-Dic 2018)")
    print("6. 🔧 Periodo personalizzato")
    
    choice = input("\n👉 Scegli periodo: ").strip()
    
    if choice == "1":
        start_date = "2022-01-01"
        end_date = "2022-12-31"
        description = "Bear Market 2022"
    elif choice == "2":
        start_date = "2021-01-01"
        end_date = "2021-12-31"
        description = "Bull Run 2021"
    elif choice == "3":
        start_date = "2020-02-01"
        end_date = "2020-08-31"
        description = "Crash COVID 2020"
    elif choice == "4":
        start_date = "2020-01-01"
        end_date = "2021-01-31"
        description = "Halving Cycle 2020"
    elif choice == "5":
        start_date = "2018-01-01"
        end_date = "2018-12-31"
        description = "Volatile 2018"
    elif choice == "6":
        start_date = input("📅 Data inizio (YYYY-MM-DD): ").strip()
        end_date = input("📅 Data fine (YYYY-MM-DD): ").strip()
        description = f"Periodo {start_date} - {end_date}"
    else:
        print("❌ Scelta non valida")
        return
    
    capitale = float(input("💰 Capitale iniziale (default 10000): ") or "10000")
    
    print(f"\n🔧 Seleziona strategia:")
    strategies = get_available_strategies()
    for i, name in enumerate(strategies.keys(), 1):
        print(f"   {i}. {name}")
    
    try:
        strategy_choice = int(input("\n👉 Scegli strategia: ")) - 1
        strategy_name = list(strategies.keys())[strategy_choice]
        strategy = create_strategy(strategy_name, timeframe)
    except (ValueError, IndexError):
        print("❌ Selezione non valida")
        return
    
    if not strategy:
        print("❌ Errore nella creazione della strategia")
        return
    
    # Calcola giorni
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    giorni = (end_dt - start_dt).days
    
    print(f"\n🎯 BACKTEST: {description}")
    print(f"📅 Periodo: {start_date} → {end_date} ({giorni} giorni)")
    print(f"🎯 Strategia: {strategy.name}")
    print(strategy.get_strategy_description())
    
    # Esegui backtest
    engine = AdvancedBacktestEngine(simbolo, strategy, capitale)
    engine.specific_start_date = start_date
    engine.specific_end_date = end_date
    results = engine.run_backtest(timeframe, giorni, 100)
    
    return results

if __name__ == "__main__":
    try:
        menu_advanced_backtest()
    except KeyboardInterrupt:
        print("\n\n⏹️  Backtesting avanzato interrotto dall'utente")
    except Exception as e:
        print(f"\n💥 Errore imprevisto: {e}")
        print(f"📝 Traceback:\n{traceback.format_exc()}")
