#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Triple Confirmation Strategy
Strategia avanzata che combina EMA + RSI + MACD per segnali ad alta probabilità
Ottimizzata per timeframe giornalieri
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base_strategy import BaseStrategy
from indicators.rsi import calculate_rsi, rsi_signals
from indicators.macd import calculate_macd, macd_signals
from indicators.volume import calculate_volume_sma, volume_analysis
from trading_functions import media_esponenziale
from typing import Dict, List

class TripleConfirmationStrategy(BaseStrategy):
    """
    Triple Confirmation Strategy per timeframe giornalieri
    
    COMPONENTI:
    1. EMA 21 - Trend principale
    2. RSI 14 - Momentum
    3. MACD (12,26,9) - Convergenza/Divergenza
    4. Volume - Conferma
    
    SEGNALI LONG:
    - Prezzo > EMA 21
    - RSI > 50 (momentum rialzista)
    - MACD Line > Signal Line
    - Volume > media (conferma)
    
    SEGNALI SHORT:
    - Prezzo < EMA 21
    - RSI < 50 (momentum ribassista)
    - MACD Line < Signal Line
    - Volume > media (conferma)
    """
    
    def __init__(self, timeframe: str = "D"):
        super().__init__("Triple Confirmation", timeframe)
        
        # Parametri default ottimizzati per daily
        self.set_parameters(
            # EMA
            ema_period=21,
            
            # RSI
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30,
            
            # MACD
            macd_fast=12,
            macd_slow=26,
            macd_signal=9,
            
            # Volume
            volume_period=20,
            volume_multiplier=1.2,  # Volume deve essere 20% sopra media
            
            # Risk Management
            stop_loss_percent=3.0,
            take_profit_percent=6.0,
            trailing_stop=True,
            
            # Filtri aggiuntivi
            min_trend_strength=0.5,  # Percentuale minima trend EMA
            require_all_signals=True  # Richiede tutti e 3 i segnali
        )
    
    def calculate_indicators(self, ohlcv_data: List) -> Dict:
        """
        Calcola tutti gli indicatori necessari
        
        Args:
            ohlcv_data: Lista di candele [timestamp, open, high, low, close, volume]
            
        Returns:
            Dict con tutti gli indicatori
        """
        if not ohlcv_data or len(ohlcv_data) < max(self.parameters['ema_period'], 
                                                   self.parameters['rsi_period'],
                                                   self.parameters['macd_slow']):
            return {'insufficient_data': True}
        
        # Estrai dati OHLCV
        timestamps = [int(candle[0]) for candle in ohlcv_data]
        opens = [float(candle[1]) for candle in ohlcv_data]
        highs = [float(candle[2]) for candle in ohlcv_data]
        lows = [float(candle[3]) for candle in ohlcv_data]
        closes = [float(candle[4]) for candle in ohlcv_data]
        volumes = [float(candle[5]) for candle in ohlcv_data]
        
        # 1. Calcola EMA
        ema_values = media_esponenziale(closes, self.parameters['ema_period'])
        
        # 2. Calcola RSI
        rsi_values = calculate_rsi(closes, self.parameters['rsi_period'])
        rsi_signal = rsi_signals(rsi_values, 
                                self.parameters['rsi_oversold'], 
                                self.parameters['rsi_overbought'])
        
        # 3. Calcola MACD
        macd_data = calculate_macd(closes, 
                                  self.parameters['macd_fast'],
                                  self.parameters['macd_slow'], 
                                  self.parameters['macd_signal'])
        macd_signal = macd_signals(macd_data)
        
        # 4. Calcola indicatori di Volume
        volume_sma = calculate_volume_sma(volumes, self.parameters['volume_period'])
        volume_signal = volume_analysis(volumes, volume_sma, self.parameters['volume_multiplier'])
        
        return {
            'timestamps': timestamps,
            'opens': opens,
            'highs': highs,
            'lows': lows,
            'closes': closes,
            'volumes': volumes,
            
            # Indicatori
            'ema': ema_values,
            'rsi': rsi_values,
            'rsi_signals': rsi_signal,
            'macd': macd_data,
            'macd_signals': macd_signal,
            'volume_sma': volume_sma,
            'volume_signals': volume_signal,
            
            'insufficient_data': False
        }
    
    def generate_signals(self, data: Dict) -> str:
        """
        Genera segnali basati sulla triple confirmation
        
        Args:
            data: Dizionario con tutti gli indicatori
            
        Returns:
            'buy', 'sell', 'close', 'hold'
        """
        if data.get('insufficient_data', True):
            return 'hold'
        
        # Se abbiamo una posizione aperta, controlla uscita
        if self.is_position_open():
            return self._check_exit_conditions(data)
        
        # Altrimenti controlla entrata
        return self._check_entry_conditions(data)
    
    def _check_entry_conditions(self, data: Dict) -> str:
        """
        Controlla tutte le condizioni per l'entrata
        
        Args:
            data: Dati di mercato e indicatori
            
        Returns:
            'buy', 'sell', 'hold'
        """
        current_price = data['closes'][-1]
        current_ema = data['ema'][-1]
        current_rsi = data['rsi'][-1]
        current_macd = data['macd']['macd_line'][-1]
        current_signal = data['macd']['signal_line'][-1]
        current_volume_signal = data['volume_signals'][-1]
        
        # Calcola trend strength
        trend_strength = ((current_price - current_ema) / current_ema) * 100
        
        # ═══════════════════════════════════════
        # 🚀 CONDIZIONI LONG
        # ═══════════════════════════════════════
        long_conditions = {
            'trend': current_price > current_ema,  # Prezzo sopra EMA
            'momentum': current_rsi > 50,          # RSI rialzista
            'macd': current_macd > current_signal, # MACD crossover rialzista
            'volume': current_volume_signal == 'high_volume',  # Volume elevato
            'trend_strength': abs(trend_strength) >= self.parameters['min_trend_strength']
        }
        
        # ═══════════════════════════════════════
        # 📉 CONDIZIONI SHORT  
        # ═══════════════════════════════════════
        short_conditions = {
            'trend': current_price < current_ema,  # Prezzo sotto EMA
            'momentum': current_rsi < 50,          # RSI ribassista
            'macd': current_macd < current_signal, # MACD crossover ribassista
            'volume': current_volume_signal == 'high_volume',  # Volume elevato
            'trend_strength': abs(trend_strength) >= self.parameters['min_trend_strength']
        }
        
        # Controlla se usare tutti i segnali o solo alcuni
        if self.parameters['require_all_signals']:
            # Tutte le condizioni devono essere soddisfatte
            if all(long_conditions.values()):
                return 'buy'
            elif all(short_conditions.values()):
                return 'sell'
        else:
            # Almeno 3 su 5 condizioni devono essere soddisfatte
            long_score = sum(long_conditions.values())
            short_score = sum(short_conditions.values())
            
            if long_score >= 3:
                return 'buy'
            elif short_score >= 3:
                return 'sell'
        
        return 'hold'
    
    def _check_exit_conditions(self, data: Dict) -> str:
        """
        Controlla le condizioni di uscita
        
        Args:
            data: Dati di mercato
            
        Returns:
            'close', 'hold'
        """
        if not self.parameters['trailing_stop']:
            # Se non usiamo trailing stop, usa stop/take profit fissi
            return self._check_fixed_exit(data)
        
        # Trailing stop basato su EMA
        return self._check_trailing_stop(data)
    
    def _check_trailing_stop(self, data: Dict) -> str:
        """
        Trailing stop basato su EMA e MACD
        
        Args:
            data: Dati di mercato
            
        Returns:
            'close', 'hold'
        """
        current_price = data['closes'][-1]
        current_ema = data['ema'][-1]
        current_macd = data['macd']['macd_line'][-1]
        current_signal = data['macd']['signal_line'][-1]
        current_rsi = data['rsi'][-1]
        
        if self.current_position == 'long':
            # Chiudi LONG se:
            # 1. Prezzo scende sotto EMA, E
            # 2. MACD diventa ribassista, E  
            # 3. RSI scende sotto 50
            exit_conditions = [
                current_price < current_ema,
                current_macd < current_signal,
                current_rsi < 50
            ]
            
            # Chiudi se almeno 2 condizioni su 3 sono negative
            if sum(exit_conditions) >= 2:
                return 'close'
                
        elif self.current_position == 'short':
            # Chiudi SHORT se:
            # 1. Prezzo sale sopra EMA, E
            # 2. MACD diventa rialzista, E
            # 3. RSI sale sopra 50
            exit_conditions = [
                current_price > current_ema,
                current_macd > current_signal,
                current_rsi > 50
            ]
            
            # Chiudi se almeno 2 condizioni su 3 sono positive
            if sum(exit_conditions) >= 2:
                return 'close'
        
        return 'hold'
    
    def _check_fixed_exit(self, data: Dict) -> str:
        """
        Stop loss e take profit fissi
        
        Args:
            data: Dati di mercato
            
        Returns:
            'close', 'hold'
        """
        current_price = data['closes'][-1]
        
        if self.current_position == 'long':
            stop_loss = self.calculate_stop_loss(self.entry_price, 'long')
            take_profit = self.calculate_take_profit(self.entry_price, 'long')
            
            if current_price <= stop_loss or current_price >= take_profit:
                return 'close'
                
        elif self.current_position == 'short':
            stop_loss = self.calculate_stop_loss(self.entry_price, 'short')
            take_profit = self.calculate_take_profit(self.entry_price, 'short')
            
            if current_price >= stop_loss or current_price <= take_profit:
                return 'close'
        
        return 'hold'
    
    def validate_signal(self, signal: str, current_price: float, data: Dict) -> bool:
        """
        Validazione aggiuntiva dei segnali
        
        Args:
            signal: Segnale da validare
            current_price: Prezzo corrente
            data: Dati di mercato
            
        Returns:
            True se valido, False altrimenti
        """
        # Validazione base dalla classe padre
        if not super().validate_signal(signal, current_price, data):
            return False
        
        # Validazioni specifiche per Triple Confirmation
        if signal in ['buy', 'sell']:
            # Non fare trade se RSI è in zona estrema
            current_rsi = data['rsi'][-1]
            
            if signal == 'buy' and current_rsi > self.parameters['rsi_overbought']:
                return False  # Non comprare se RSI ipercomprato
                
            if signal == 'sell' and current_rsi < self.parameters['rsi_oversold']:
                return False  # Non vendere short se RSI ipervenduto
        
        return True
    
    def get_strategy_description(self) -> str:
        """
        Descrizione completa della strategia
        
        Returns:
            Descrizione dettagliata
        """
        return f"""
🎯 TRIPLE CONFIRMATION STRATEGY - {self.timeframe}
═══════════════════════════════════════════════════

📊 INDICATORI:
• EMA Period: {self.parameters['ema_period']}
• RSI Period: {self.parameters['rsi_period']} (OB: {self.parameters['rsi_overbought']}, OS: {self.parameters['rsi_oversold']})
• MACD: ({self.parameters['macd_fast']}, {self.parameters['macd_slow']}, {self.parameters['macd_signal']})
• Volume SMA: {self.parameters['volume_period']} periods

🚀 SEGNALI LONG:
✓ Prezzo > EMA {self.parameters['ema_period']}
✓ RSI > 50 (momentum rialzista)
✓ MACD Line > Signal Line
✓ Volume > {self.parameters['volume_multiplier']}x media

📉 SEGNALI SHORT:
✓ Prezzo < EMA {self.parameters['ema_period']}
✓ RSI < 50 (momentum ribassista)  
✓ MACD Line < Signal Line
✓ Volume > {self.parameters['volume_multiplier']}x media

🛡️ RISK MANAGEMENT:
• Stop Loss: {self.parameters['stop_loss_percent']}%
• Take Profit: {self.parameters['take_profit_percent']}%
• Trailing Stop: {'Attivo' if self.parameters['trailing_stop'] else 'Disattivo'}
• Trend Strength Min: {self.parameters['min_trend_strength']}%

🎛️ CONFIGURAZIONE:
• Richiede tutti i segnali: {'Sì' if self.parameters['require_all_signals'] else 'No (3/5)'}
• Timeframe ottimale: Daily/4H
• Tipo strategia: Trend Following + Momentum
        """.strip()
