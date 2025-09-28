"""
Volume Profile Calculator
Calcola POC (Point of Control), VAH (Value Area High), VAL (Value Area Low)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VolumeProfileLevel:
    """Singolo livello del volume profile"""
    price: float
    volume: float
    buy_volume: float
    sell_volume: float
    delta: float  # buy_volume - sell_volume
    
@dataclass 
class VolumeProfileMetrics:
    """Metriche complete del volume profile"""
    poc_price: float           # Point of Control
    poc_volume: float          # Volume al POC
    vah_price: float           # Value Area High
    val_price: float           # Value Area Low
    value_area_volume: float   # Volume nell'area valore (70%)
    total_volume: float        # Volume totale
    levels: List[VolumeProfileLevel]  # Tutti i livelli

class VolumeProfileCalculator:
    """
    Calcola il Volume Profile con POC, VAH, VAL per analisi orderflow
    """
    
    def __init__(self, tick_size: float = 0.1, value_area_percentage: float = 0.70):
        self.tick_size = tick_size
        self.value_area_percentage = value_area_percentage
        
    def calculate_profile(self, trades_data: pd.DataFrame) -> VolumeProfileMetrics:
        """
        Calcola il volume profile da dati di trades
        
        Args:
            trades_data: DataFrame con colonne ['price', 'volume', 'side']
                        side: 'buy' or 'sell'
        
        Returns:
            VolumeProfileMetrics con POC, VAH, VAL
        """
        try:
            if trades_data.empty:
                logger.warning("Dati trades vuoti")
                return self._empty_metrics()
                
            # Raggruppa per livelli di prezzo (tick size)
            levels = self._group_by_price_levels(trades_data)
            
            # Calcola POC (Point of Control)
            poc_price, poc_volume = self._calculate_poc(levels)
            
            # Calcola Value Area (VAH/VAL)
            vah_price, val_price, va_volume = self._calculate_value_area(levels)
            
            # Crea lista livelli ordinata
            level_objects = []
            for price in sorted(levels.keys()):
                level_data = levels[price]
                level_objects.append(VolumeProfileLevel(
                    price=price,
                    volume=level_data['volume'],
                    buy_volume=level_data['buy_volume'],
                    sell_volume=level_data['sell_volume'],
                    delta=level_data['buy_volume'] - level_data['sell_volume']
                ))
            
            total_volume = sum(level['volume'] for level in levels.values())
            
            return VolumeProfileMetrics(
                poc_price=poc_price,
                poc_volume=poc_volume,
                vah_price=vah_price,
                val_price=val_price,
                value_area_volume=va_volume,
                total_volume=total_volume,
                levels=level_objects
            )
            
        except Exception as e:
            logger.error(f"Errore calcolo volume profile: {e}")
            return self._empty_metrics()
    
    def _group_by_price_levels(self, trades_data: pd.DataFrame) -> Dict[float, Dict]:
        """Raggruppa trades per livelli di prezzo"""
        levels = {}
        
        for _, trade in trades_data.iterrows():
            # Arrotonda al tick size più vicino
            price_level = round(trade['price'] / self.tick_size) * self.tick_size
            
            if price_level not in levels:
                levels[price_level] = {
                    'volume': 0.0,
                    'buy_volume': 0.0,
                    'sell_volume': 0.0
                }
            
            volume = trade['volume']
            levels[price_level]['volume'] += volume
            
            if trade['side'] == 'buy':
                levels[price_level]['buy_volume'] += volume
            else:
                levels[price_level]['sell_volume'] += volume
                
        return levels
    
    def _calculate_poc(self, levels: Dict[float, Dict]) -> Tuple[float, float]:
        """Calcola Point of Control (livello con maggior volume)"""
        if not levels:
            return 0.0, 0.0
            
        max_volume = 0
        poc_price = 0
        
        for price, data in levels.items():
            if data['volume'] > max_volume:
                max_volume = data['volume']
                poc_price = price
                
        return poc_price, max_volume
    
    def _calculate_value_area(self, levels: Dict[float, Dict]) -> Tuple[float, float, float]:
        """
        Calcola Value Area High (VAH) e Value Area Low (VAL)
        L'area valore contiene il 70% del volume totale
        """
        if not levels:
            return 0.0, 0.0, 0.0
            
        # Ordina livelli per volume (decrescente)
        sorted_levels = sorted(levels.items(), key=lambda x: x[1]['volume'], reverse=True)
        
        total_volume = sum(data['volume'] for data in levels.values())
        target_volume = total_volume * self.value_area_percentage
        
        # Accumula volume partendo dai livelli con maggior volume
        accumulated_volume = 0
        value_area_prices = []
        
        for price, data in sorted_levels:
            accumulated_volume += data['volume']
            value_area_prices.append(price)
            
            if accumulated_volume >= target_volume:
                break
        
        if not value_area_prices:
            return 0.0, 0.0, 0.0
            
        # VAH = prezzo più alto nell'area valore
        # VAL = prezzo più basso nell'area valore
        vah_price = max(value_area_prices)
        val_price = min(value_area_prices)
        
        return vah_price, val_price, accumulated_volume
    
    def _empty_metrics(self) -> VolumeProfileMetrics:
        """Restituisce metriche vuote in caso di errore"""
        return VolumeProfileMetrics(
            poc_price=0.0,
            poc_volume=0.0,
            vah_price=0.0,
            val_price=0.0,
            value_area_volume=0.0,
            total_volume=0.0,
            levels=[]
        )
    
    def get_support_resistance_levels(self, metrics: VolumeProfileMetrics, 
                                    min_volume_threshold: float = 0.05) -> List[float]:
        """
        Identifica livelli di supporto/resistenza basati sul volume profile
        
        Args:
            metrics: Metriche volume profile
            min_volume_threshold: Soglia minima volume (% del totale)
            
        Returns:
            Lista prezzi con volume significativo
        """
        if not metrics.levels:
            return []
            
        threshold_volume = metrics.total_volume * min_volume_threshold
        significant_levels = []
        
        for level in metrics.levels:
            if level.volume >= threshold_volume:
                significant_levels.append(level.price)
                
        return sorted(significant_levels)
    
    def analyze_delta_profile(self, metrics: VolumeProfileMetrics) -> Dict:
        """
        Analizza il delta (buy vs sell pressure) per livello
        
        Returns:
            Analisi delta con livelli di accumulation/distribution
        """
        if not metrics.levels:
            return {}
            
        total_buy_volume = sum(level.buy_volume for level in metrics.levels)
        total_sell_volume = sum(level.sell_volume for level in metrics.levels)
        total_delta = total_buy_volume - total_sell_volume
        
        # Trova livelli con delta significativo
        strong_buy_levels = []
        strong_sell_levels = []
        
        for level in metrics.levels:
            delta_ratio = abs(level.delta) / level.volume if level.volume > 0 else 0
            
            if delta_ratio > 0.3:  # 30% di squilibrio
                if level.delta > 0:
                    strong_buy_levels.append({
                        'price': level.price,
                        'delta': level.delta,
                        'ratio': delta_ratio
                    })
                else:
                    strong_sell_levels.append({
                        'price': level.price,
                        'delta': level.delta,
                        'ratio': delta_ratio
                    })
        
        return {
            'total_delta': total_delta,
            'total_buy_volume': total_buy_volume,
            'total_sell_volume': total_sell_volume,
            'net_pressure': 'buy' if total_delta > 0 else 'sell',
            'strong_buy_levels': strong_buy_levels,
            'strong_sell_levels': strong_sell_levels
        }


def test_volume_profile():
    """Test del volume profile calculator"""
    import random
    
    # Genera dati di test
    np.random.seed(42)
    base_price = 50000
    
    trades = []
    for _ in range(1000):
        price = base_price + np.random.normal(0, 100)
        volume = np.random.exponential(10)
        side = 'buy' if random.random() > 0.5 else 'sell'
        trades.append({'price': price, 'volume': volume, 'side': side})
    
    df = pd.DataFrame(trades)
    
    # Test calculator
    calculator = VolumeProfileCalculator(tick_size=1.0)
    metrics = calculator.calculate_profile(df)
    
    print(f"📊 Volume Profile Test Results:")
    print(f"   POC: ${metrics.poc_price:.2f} (Volume: {metrics.poc_volume:.2f})")
    print(f"   VAH: ${metrics.vah_price:.2f}")
    print(f"   VAL: ${metrics.val_price:.2f}")
    print(f"   Total Volume: {metrics.total_volume:.2f}")
    print(f"   Levels: {len(metrics.levels)}")
    
    # Test delta analysis
    delta_analysis = calculator.analyze_delta_profile(metrics)
    print(f"\n📈 Delta Analysis:")
    print(f"   Net Pressure: {delta_analysis['net_pressure']}")
    print(f"   Total Delta: {delta_analysis['total_delta']:.2f}")
    print(f"   Strong Buy Levels: {len(delta_analysis['strong_buy_levels'])}")
    print(f"   Strong Sell Levels: {len(delta_analysis['strong_sell_levels'])}")

if __name__ == "__main__":
    test_volume_profile()