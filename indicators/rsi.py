#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSI (Relative Strength Index) Indicator
Calcola l'indice di forza relativa per identificare condizioni di ipercomprato/ipervenduto
"""

def calculate_rsi(prices, period=14):
    """
    Calcola il Relative Strength Index (RSI)
    
    Args:
        prices: Lista dei prezzi di chiusura
        period: Periodo per il calcolo del RSI (default 14)
        
    Returns:
        Lista dei valori RSI
    """
    if len(prices) < period + 1:
        return [50] * len(prices)  # Valore neutro se dati insufficienti
    
    # Calcola le variazioni di prezzo
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    # Separa guadagni e perdite
    gains = [max(delta, 0) for delta in deltas]
    losses = [abs(min(delta, 0)) for delta in deltas]
    
    # Calcola la media mobile dei guadagni e delle perdite
    rsi_values = [50]  # Primo valore neutro
    
    # Calcola il primo RSI con media semplice
    if len(gains) >= period:
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
        
        # Calcola RSI successivi con media mobile esponenziale
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
    
    # Riempi con valori neutri se necessario
    while len(rsi_values) < len(prices):
        rsi_values.append(50)
    
    return rsi_values

def rsi_signals(rsi_values, oversold_level=30, overbought_level=70):
    """
    Genera segnali basati sui livelli di RSI
    
    Args:
        rsi_values: Lista dei valori RSI
        oversold_level: Livello di ipervenduto (default 30)
        overbought_level: Livello di ipercomprato (default 70)
        
    Returns:
        Lista di segnali: 'oversold', 'overbought', 'neutral'
    """
    signals = []
    
    for rsi in rsi_values:
        if rsi <= oversold_level:
            signals.append('oversold')
        elif rsi >= overbought_level:
            signals.append('overbought')
        else:
            signals.append('neutral')
    
    return signals

def rsi_divergence(prices, rsi_values, lookback=5):
    """
    Identifica divergenze tra prezzo e RSI
    
    Args:
        prices: Lista dei prezzi
        rsi_values: Lista dei valori RSI
        lookback: Periodo di lookback per identificare divergenze
        
    Returns:
        Lista di segnali: 'bullish_div', 'bearish_div', 'none'
    """
    if len(prices) < lookback * 2 or len(rsi_values) < lookback * 2:
        return ['none'] * len(prices)
    
    signals = ['none'] * lookback
    
    for i in range(lookback, len(prices) - lookback):
        # Trova massimi e minimi locali
        price_high = max(prices[i-lookback:i+lookback+1])
        price_low = min(prices[i-lookback:i+lookback+1])
        rsi_high = max(rsi_values[i-lookback:i+lookback+1])
        rsi_low = min(rsi_values[i-lookback:i+lookback+1])
        
        current_price = prices[i]
        current_rsi = rsi_values[i]
        
        # Divergenza rialzista: prezzo fa minimi più bassi, RSI fa minimi più alti
        if (current_price <= price_low and current_rsi > rsi_low and 
            current_rsi < 50):  # RSI in territorio ribassista
            signals.append('bullish_div')
        # Divergenza ribassista: prezzo fa massimi più alti, RSI fa massimi più bassi
        elif (current_price >= price_high and current_rsi < rsi_high and 
              current_rsi > 50):  # RSI in territorio rialzista
            signals.append('bearish_div')
        else:
            signals.append('none')
    
    # Riempi la fine
    while len(signals) < len(prices):
        signals.append('none')
    
    return signals
