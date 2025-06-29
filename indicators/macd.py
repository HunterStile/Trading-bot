#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MACD (Moving Average Convergence Divergence) Indicator
Calcola MACD line, Signal line e Histogram per identificare trend e momentum
"""

def calculate_ema(prices, period):
    """
    Calcola l'Exponential Moving Average
    
    Args:
        prices: Lista dei prezzi
        period: Periodo per EMA
        
    Returns:
        Lista dei valori EMA
    """
    if len(prices) < period:
        return [prices[0]] * len(prices) if prices else []
    
    multiplier = 2 / (period + 1)
    ema_values = []
    
    # Prima EMA è la media semplice
    sma = sum(prices[:period]) / period
    ema_values.extend([prices[0]] * (period - 1))
    ema_values.append(sma)
    
    # Calcola EMA successive
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)
    
    return ema_values

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """
    Calcola MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: Lista dei prezzi di chiusura
        fast_period: Periodo EMA veloce (default 12)
        slow_period: Periodo EMA lenta (default 26)
        signal_period: Periodo per signal line (default 9)
        
    Returns:
        Dict con 'macd_line', 'signal_line', 'histogram'
    """
    if len(prices) < slow_period:
        # Valori neutri se dati insufficienti
        return {
            'macd_line': [0] * len(prices),
            'signal_line': [0] * len(prices),
            'histogram': [0] * len(prices)
        }
    
    # Calcola EMA veloce e lenta
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    # Calcola MACD line (differenza tra EMA veloce e lenta)
    macd_line = []
    for i in range(len(prices)):
        macd_line.append(fast_ema[i] - slow_ema[i])
    
    # Calcola Signal line (EMA della MACD line)
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Calcola Histogram (differenza tra MACD line e Signal line)
    histogram = []
    for i in range(len(macd_line)):
        histogram.append(macd_line[i] - signal_line[i])
    
    return {
        'macd_line': macd_line,
        'signal_line': signal_line,
        'histogram': histogram
    }

def macd_signals(macd_data):
    """
    Genera segnali basati sui crossover del MACD
    
    Args:
        macd_data: Dizionario con dati MACD da calculate_macd()
        
    Returns:
        Lista di segnali: 'bullish_cross', 'bearish_cross', 'none'
    """
    macd_line = macd_data['macd_line']
    signal_line = macd_data['signal_line']
    
    if len(macd_line) < 2:
        return ['none'] * len(macd_line)
    
    signals = ['none']  # Primo valore
    
    for i in range(1, len(macd_line)):
        prev_macd = macd_line[i-1]
        curr_macd = macd_line[i]
        prev_signal = signal_line[i-1]
        curr_signal = signal_line[i]
        
        # Crossover rialzista: MACD line incrocia sopra Signal line
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            signals.append('bullish_cross')
        # Crossover ribassista: MACD line incrocia sotto Signal line
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            signals.append('bearish_cross')
        else:
            signals.append('none')
    
    return signals

def macd_trend_strength(macd_data):
    """
    Valuta la forza del trend basata sui valori MACD
    
    Args:
        macd_data: Dizionario con dati MACD
        
    Returns:
        Lista di valori: 'strong_bullish', 'weak_bullish', 'neutral', 'weak_bearish', 'strong_bearish'
    """
    macd_line = macd_data['macd_line']
    signal_line = macd_data['signal_line']
    histogram = macd_data['histogram']
    
    trends = []
    
    for i in range(len(macd_line)):
        macd = macd_line[i]
        signal = signal_line[i]
        hist = histogram[i]
        
        # Trend rialzista forte: MACD > Signal e Histogram crescente
        if macd > signal and hist > 0:
            if i > 0 and hist > histogram[i-1]:
                trends.append('strong_bullish')
            else:
                trends.append('weak_bullish')
        # Trend ribassista forte: MACD < Signal e Histogram decrescente
        elif macd < signal and hist < 0:
            if i > 0 and hist < histogram[i-1]:
                trends.append('strong_bearish')
            else:
                trends.append('weak_bearish')
        else:
            trends.append('neutral')
    
    return trends

def macd_zero_line_cross(macd_data):
    """
    Identifica i crossover della linea zero del MACD
    
    Args:
        macd_data: Dizionario con dati MACD
        
    Returns:
        Lista di segnali: 'zero_cross_up', 'zero_cross_down', 'none'
    """
    macd_line = macd_data['macd_line']
    
    if len(macd_line) < 2:
        return ['none'] * len(macd_line)
    
    signals = ['none']  # Primo valore
    
    for i in range(1, len(macd_line)):
        prev_macd = macd_line[i-1]
        curr_macd = macd_line[i]
        
        # Crossover sopra zero
        if prev_macd <= 0 and curr_macd > 0:
            signals.append('zero_cross_up')
        # Crossover sotto zero
        elif prev_macd >= 0 and curr_macd < 0:
            signals.append('zero_cross_down')
        else:
            signals.append('none')
    
    return signals
