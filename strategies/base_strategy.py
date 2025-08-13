#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classe Base per tutte le Strategie di Trading
Definisce l'interfaccia comune che ogni strategia deve implementare
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class BaseStrategy(ABC):
    """
    Classe base astratta per tutte le strategie di trading.
    Ogni strategia deve implementare i metodi astratti definiti qui.
    """
    
    def __init__(self, name: str, timeframe: str = "D"):
        """
        Inizializza la strategia base
        
        Args:
            name: Nome della strategia
            timeframe: Timeframe di trading (D, 4h, 1h, etc.)
        """
        self.name = name
        self.timeframe = timeframe
        self.parameters = {}
        self.current_position = None  # None, 'long', 'short'
        self.entry_price = 0
        self.entry_time = None
        
    @abstractmethod
    def generate_signals(self, data: Dict) -> str:
        """
        Genera segnali di trading basati sui dati di mercato
        
        Args:
            data: Dizionario con dati OHLCV e indicatori
            
        Returns:
            'buy', 'sell', 'hold' o 'close'
        """
        pass
    
    @abstractmethod
    def calculate_indicators(self, ohlcv_data: List) -> Dict:
        """
        Calcola tutti gli indicatori necessari per la strategia
        
        Args:
            ohlcv_data: Lista di candele [timestamp, open, high, low, close, volume]
            
        Returns:
            Dizionario con tutti gli indicatori calcolati
        """
        pass
    
    def set_parameters(self, **kwargs):
        """
        Imposta i parametri della strategia
        
        Args:
            **kwargs: Parametri specifici della strategia
        """
        self.parameters.update(kwargs)
        
    def get_parameters(self) -> Dict:
        """
        Restituisce i parametri correnti della strategia
        
        Returns:
            Dizionario con i parametri
        """
        return self.parameters.copy()
    
    def validate_signal(self, signal: str, current_price: float, data: Dict) -> bool:
        """
        Valida un segnale prima di eseguirlo (opzionale, override se necessario)
        
        Args:
            signal: Segnale generato ('buy', 'sell', etc.)
            current_price: Prezzo corrente
            data: Dati di mercato correnti
            
        Returns:
            True se il segnale è valido, False altrimenti
        """
        return True
    
    def calculate_position_size(self, capital: float, price: float, risk_percent: float = 2.0) -> float:
        """
        Calcola la dimensione della posizione basata sul capitale e rischio
        
        Args:
            capital: Capitale disponibile
            price: Prezzo corrente
            risk_percent: Percentuale di rischio per trade
            
        Returns:
            Importo da investire
        """
        return capital * (risk_percent / 100)
    
    def calculate_stop_loss(self, entry_price: float, position_type: str) -> float:
        """
        Calcola il livello di stop loss (override se necessario)
        
        Args:
            entry_price: Prezzo di entrata
            position_type: 'long' o 'short'
            
        Returns:
            Prezzo di stop loss
        """
        stop_loss_percent = self.parameters.get('stop_loss_percent', 3.0)
        
        if position_type == 'long':
            return entry_price * (1 - stop_loss_percent / 100)
        else:  # short
            return entry_price * (1 + stop_loss_percent / 100)
    
    def calculate_take_profit(self, entry_price: float, position_type: str) -> float:
        """
        Calcola il livello di take profit (override se necessario)
        
        Args:
            entry_price: Prezzo di entrata
            position_type: 'long' o 'short'
            
        Returns:
            Prezzo di take profit
        """
        take_profit_percent = self.parameters.get('take_profit_percent', 6.0)
        
        if position_type == 'long':
            return entry_price * (1 + take_profit_percent / 100)
        else:  # short
            return entry_price * (1 - take_profit_percent / 100)
    
    def update_position(self, position_type: str, entry_price: float, entry_time: datetime):
        """
        Aggiorna lo stato della posizione corrente
        
        Args:
            position_type: 'long', 'short', o None per chiudere
            entry_price: Prezzo di entrata
            entry_time: Timestamp di entrata
        """
        self.current_position = position_type
        self.entry_price = entry_price
        self.entry_time = entry_time
    
    def close_position(self):
        """
        Chiude la posizione corrente
        """
        self.current_position = None
        self.entry_price = 0
        self.entry_time = None
    
    def is_position_open(self) -> bool:
        """
        Controlla se c'è una posizione aperta
        
        Returns:
            True se c'è una posizione aperta, False altrimenti
        """
        return self.current_position is not None
    
    def get_strategy_info(self) -> Dict:
        """
        Restituisce informazioni sulla strategia
        
        Returns:
            Dizionario con info sulla strategia
        """
        return {
            'name': self.name,
            'timeframe': self.timeframe,
            'parameters': self.parameters,
            'current_position': self.current_position,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time
        }
    
    def __str__(self) -> str:
        """
        Rappresentazione stringa della strategia
        """
        return f"{self.name} Strategy (TF: {self.timeframe})"
    
    def __repr__(self) -> str:
        """
        Rappresentazione per debug
        """
        return f"<{self.__class__.__name__}: {self.name}, TF: {self.timeframe}>"
