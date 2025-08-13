#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volume Indicators
Calcola indicatori basati sul volume per confermare i segnali di prezzo
"""

def calculate_volume_sma(volumes, period=20):
    """
    Calcola la media mobile semplice del volume
    
    Args:
        volumes: Lista dei volumi
        period: Periodo per la media mobile (default 20)
        
    Returns:
        Lista dei valori SMA del volume
    """
    if len(volumes) < period:
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        return [avg_vol] * len(volumes)
    
    sma_values = []
    
    # Riempi i primi valori con la media disponibile
    for i in range(period):
        if i == 0:
            sma_values.append(volumes[0])
        else:
            sma_values.append(sum(volumes[:i+1]) / (i+1))
    
    # Calcola SMA per il resto
    for i in range(period, len(volumes)):
        sma = sum(volumes[i-period+1:i+1]) / period
        sma_values.append(sma)
    
    return sma_values

def volume_analysis(volumes, volume_sma, multiplier=1.5):
    """
    Analizza il volume rispetto alla sua media mobile
    
    Args:
        volumes: Lista dei volumi
        volume_sma: Lista della media mobile del volume
        multiplier: Moltiplicatore per volume alto (default 1.5)
        
    Returns:
        Lista di segnali: 'high_volume', 'low_volume', 'normal_volume'
    """
    signals = []
    
    for i in range(len(volumes)):
        vol = volumes[i]
        avg_vol = volume_sma[i]
        
        if vol >= avg_vol * multiplier:
            signals.append('high_volume')
        elif vol <= avg_vol / multiplier:
            signals.append('low_volume')
        else:
            signals.append('normal_volume')
    
    return signals

def volume_price_trend(prices, volumes):
    """
    Calcola il Volume Price Trend (VPT)
    Indica se il volume supporta la direzione del prezzo
    
    Args:
        prices: Lista dei prezzi di chiusura
        volumes: Lista dei volumi
        
    Returns:
        Lista dei valori VPT
    """
    if len(prices) < 2 or len(volumes) < 2:
        return [0] * len(prices)
    
    vpt_values = [0]  # Primo valore
    
    for i in range(1, len(prices)):
        price_change = (prices[i] - prices[i-1]) / prices[i-1]
        vpt = vpt_values[-1] + (volumes[i] * price_change)
        vpt_values.append(vpt)
    
    return vpt_values

def on_balance_volume(prices, volumes):
    """
    Calcola l'On Balance Volume (OBV)
    Accumula volume basato sulla direzione del prezzo
    
    Args:
        prices: Lista dei prezzi di chiusura
        volumes: Lista dei volumi
        
    Returns:
        Lista dei valori OBV
    """
    if len(prices) < 2 or len(volumes) < 2:
        return [0] * len(prices)
    
    obv_values = [0]  # Primo valore
    
    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            # Prezzo in salita: aggiungi volume
            obv = obv_values[-1] + volumes[i]
        elif prices[i] < prices[i-1]:
            # Prezzo in discesa: sottrai volume
            obv = obv_values[-1] - volumes[i]
        else:
            # Prezzo invariato: OBV invariato
            obv = obv_values[-1]
        
        obv_values.append(obv)
    
    return obv_values

def volume_breakout_confirmation(prices, volumes, volume_sma, lookback=5, volume_threshold=1.5):
    """
    Conferma i breakout di prezzo con l'analisi del volume
    
    Args:
        prices: Lista dei prezzi
        volumes: Lista dei volumi
        volume_sma: Media mobile del volume
        lookback: Periodo per identificare breakout
        volume_threshold: Soglia volume per conferma
        
    Returns:
        Lista di segnali: 'confirmed_breakout_up', 'confirmed_breakout_down', 'weak_breakout', 'none'
    """
    if len(prices) < lookback + 1:
        return ['none'] * len(prices)
    
    signals = ['none'] * lookback
    
    for i in range(lookback, len(prices)):
        # Calcola massimo e minimo nel periodo di lookback
        recent_high = max(prices[i-lookback:i])
        recent_low = min(prices[i-lookback:i])
        current_price = prices[i]
        current_volume = volumes[i]
        avg_volume = volume_sma[i]
        
        # Controlla se c'è volume elevato
        high_volume = current_volume >= avg_volume * volume_threshold
        
        # Breakout rialzista
        if current_price > recent_high:
            if high_volume:
                signals.append('confirmed_breakout_up')
            else:
                signals.append('weak_breakout')
        # Breakout ribassista
        elif current_price < recent_low:
            if high_volume:
                signals.append('confirmed_breakout_down')
            else:
                signals.append('weak_breakout')
        else:
            signals.append('none')
    
    return signals

def volume_trend_analysis(volumes, period=10):
    """
    Analizza il trend del volume
    
    Args:
        volumes: Lista dei volumi
        period: Periodo per l'analisi del trend
        
    Returns:
        Lista di segnali: 'volume_increasing', 'volume_decreasing', 'volume_stable'
    """
    if len(volumes) < period:
        return ['volume_stable'] * len(volumes)
    
    signals = ['volume_stable'] * (period - 1)
    
    for i in range(period - 1, len(volumes)):
        recent_volumes = volumes[i-period+1:i+1]
        
        # Calcola il trend lineare semplificato
        first_half = sum(recent_volumes[:period//2]) / (period//2)
        second_half = sum(recent_volumes[period//2:]) / (period - period//2)
        
        change_ratio = (second_half - first_half) / first_half if first_half > 0 else 0
        
        if change_ratio > 0.1:  # Volume in aumento del 10%+
            signals.append('volume_increasing')
        elif change_ratio < -0.1:  # Volume in diminuzione del 10%+
            signals.append('volume_decreasing')
        else:
            signals.append('volume_stable')
    
    return signals
