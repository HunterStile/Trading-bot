#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMA Strategy
Strategia basata su EMA singola con trailing stop
Migrata dal backtest.py originale
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base_strategy import BaseStrategy
from trading_functions import media_esponenziale
from typing import Dict, List

class EMAStrategy(BaseStrategy):
    """
    Strategia EMA singola con trailing stop
    - Entrata: N candele consecutive sopra/sotto EMA
    - Uscita: N candele consecutive nella direzione opposta
    """
    
    def __init__(self, timeframe: str = "D"):
        super().__init__("EMA Single", timeframe)
        
        # Parametri default
        self.set_parameters(
            ema_period=21,
            candele_richieste=3,
            distanza_max_percent=1.0,
            stop_loss_percent=3.0,
            take_profit_percent=6.0
        )
    
    def calculate_indicators(self, ohlcv_data: List) -> Dict:
        """
        Calcola l'EMA e la distanza dal prezzo
        
        Args:
            ohlcv_data: Lista di candele [timestamp, open, high, low, close, volume]
            
        Returns:
            Dict con indicatori calcolati
        """
        if not ohlcv_data or len(ohlcv_data) < self.parameters['ema_period']:
            return {
                'ema': [],
                'prices': [],
                'timestamps': []
            }
        
        # Estrai i prezzi di chiusura
        closes = [float(candle[4]) for candle in ohlcv_data]
        timestamps = [int(candle[0]) for candle in ohlcv_data]
        
        # Calcola EMA
        ema_values = media_esponenziale(closes, self.parameters['ema_period'])
        
        return {
            'ema': ema_values,
            'prices': closes,
            'timestamps': timestamps,
            'opens': [float(candle[1]) for candle in ohlcv_data],
            'highs': [float(candle[2]) for candle in ohlcv_data],
            'lows': [float(candle[3]) for candle in ohlcv_data],
            'volumes': [float(candle[5]) for candle in ohlcv_data]
        }
    
    def generate_signals(self, data: Dict) -> str:
        """
        Genera segnali basati su EMA
        
        Args:
            data: Dizionario con indicatori e dati di mercato
            
        Returns:
            'buy', 'sell', 'close', 'hold'
        """
        if not data or 'ema' not in data or 'prices' not in data:
            return 'hold'
        
        ema_values = data['ema']
        prices = data['prices']
        
        if len(prices) < self.parameters['candele_richieste']:
            return 'hold'
        
        current_price = prices[-1]
        current_ema = ema_values[-1]
        
        # Calcola distanza percentuale dall'EMA
        distanza_percent = ((current_price - current_ema) / current_ema) * 100
        
        # Se abbiamo già una posizione, controlla le condizioni di uscita
        if self.is_position_open():
            return self._check_exit_conditions(data)
        
        # Controlla condizioni di entrata
        return self._check_entry_conditions(data, distanza_percent)
    
    def _check_entry_conditions(self, data: Dict, distanza_percent: float) -> str:
        """
        Controlla le condizioni di entrata
        
        Args:
            data: Dati di mercato
            distanza_percent: Distanza percentuale dall'EMA
            
        Returns:
            'buy', 'sell', 'hold'
        """
        ema_values = data['ema']
        prices = data['prices']
        candele_richieste = self.parameters['candele_richieste']
        distanza_max = self.parameters['distanza_max_percent']
        
        # Controlla candele consecutive sopra EMA (segnale LONG)
        candele_sopra = self._conta_candele_consecutive(prices, ema_values, candele_richieste, sopra=True)
        
        if (candele_sopra >= candele_richieste and 
            0 <= distanza_percent <= distanza_max):
            return 'buy'
        
        # Controlla candele consecutive sotto EMA (segnale SHORT)
        candele_sotto = self._conta_candele_consecutive(prices, ema_values, candele_richieste, sopra=False)
        
        if (candele_sotto >= candele_richieste and 
            -distanza_max <= distanza_percent <= 0):
            return 'sell'
        
        return 'hold'
    
    def _check_exit_conditions(self, data: Dict) -> str:
        """
        Controlla le condizioni di uscita (trailing stop)
        
        Args:
            data: Dati di mercato
            
        Returns:
            'close', 'hold'
        """
        ema_values = data['ema']
        prices = data['prices']
        candele_richieste = self.parameters['candele_richieste']
        
        if self.current_position == 'long':
            # Chiudi LONG se N candele consecutive sotto EMA
            candele_sotto = self._conta_candele_consecutive(prices, ema_values, candele_richieste, sopra=False)
            if candele_sotto >= candele_richieste:
                return 'close'
        
        elif self.current_position == 'short':
            # Chiudi SHORT se N candele consecutive sopra EMA
            candele_sopra = self._conta_candele_consecutive(prices, ema_values, candele_richieste, sopra=True)
            if candele_sopra >= candele_richieste:
                return 'close'
        
        return 'hold'
    
    def _conta_candele_consecutive(self, prices: List, ema_values: List, numero_candele: int, sopra: bool) -> int:
        """
        Conta le candele consecutive sopra o sotto EMA
        
        Args:
            prices: Lista prezzi
            ema_values: Lista valori EMA
            numero_candele: Numero di candele da controllare
            sopra: True per sopra EMA, False per sotto
            
        Returns:
            Numero di candele consecutive
        """
        if len(prices) < numero_candele or len(ema_values) < numero_candele:
            return 0
        
        candele_consecutive = 0
        
        for i in range(numero_candele):
            idx = -(i + 1)  # Parti dall'ultima candela
            
            if sopra:
                if prices[idx] > ema_values[idx]:
                    candele_consecutive += 1
                else:
                    break
            else:
                if prices[idx] < ema_values[idx]:
                    candele_consecutive += 1
                else:
                    break
        
        return candele_consecutive
    
    def validate_signal(self, signal: str, current_price: float, data: Dict) -> bool:
        """
        Valida il segnale prima dell'esecuzione
        
        Args:
            signal: Segnale da validare
            current_price: Prezzo corrente
            data: Dati di mercato
            
        Returns:
            True se valido, False altrimenti
        """
        # Controlli base
        if signal not in ['buy', 'sell', 'close']:
            return True
        
        # Non permettere apertura di nuove posizioni se una è già aperta
        if signal in ['buy', 'sell'] and self.is_position_open():
            return False
        
        # Non permettere chiusura se non c'è posizione aperta
        if signal == 'close' and not self.is_position_open():
            return False
        
        return True
    
    def get_strategy_description(self) -> str:
        """
        Restituisce una descrizione della strategia
        
        Returns:
            Descrizione della strategia
        """
        return f"""
EMA Strategy - {self.timeframe}
═══════════════════════════════
📊 EMA Period: {self.parameters['ema_period']}
🕯️  Candele richieste: {self.parameters['candele_richieste']}
📏 Distanza max EMA: {self.parameters['distanza_max_percent']}%
🛑 Stop Loss: {self.parameters['stop_loss_percent']}%
🎯 Take Profit: {self.parameters['take_profit_percent']}%

📋 LOGICA:
• LONG: {self.parameters['candele_richieste']} candele sopra EMA + distanza ≤ {self.parameters['distanza_max_percent']}%
• SHORT: {self.parameters['candele_richieste']} candele sotto EMA + distanza ≤ {self.parameters['distanza_max_percent']}%
• EXIT: {self.parameters['candele_richieste']} candele nella direzione opposta (trailing stop)
        """.strip()
