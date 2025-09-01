"""
Signals Module - Technical indicators and microstructural analysis
Calculates VWAP, volatility, order book imbalance, and other scalping signals
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import deque
import time
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types for different strategies"""
    MEAN_REVERSION_LONG = "mean_reversion_long"
    MEAN_REVERSION_SHORT = "mean_reversion_short"
    BREAKOUT_LONG = "breakout_long"
    BREAKOUT_SHORT = "breakout_short"
    NO_SIGNAL = "no_signal"

@dataclass
class Signal:
    """Signal data structure"""
    signal_type: SignalType
    strength: float  # 0-1, confidence level
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: float
    metadata: Dict = None

class TechnicalIndicators:
    """
    Technical indicators optimized for high-frequency scalping
    Uses sliding windows for real-time calculation
    """
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.prices = deque(maxlen=window_size)
        self.volumes = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        
        # VWAP calculation
        self.price_volume = deque(maxlen=window_size)
        self.cumulative_pv = 0
        self.cumulative_volume = 0
        
        # Volatility calculation
        self.returns = deque(maxlen=window_size)
    
    def add_tick(self, price: float, volume: float, timestamp: float = None):
        """Add new tick data point"""
        if timestamp is None:
            timestamp = time.time()
        
        # Remove oldest values from cumulative sums if at capacity
        if len(self.prices) == self.window_size:
            old_pv = self.price_volume[0]
            old_volume = self.volumes[0]
            self.cumulative_pv -= old_pv
            self.cumulative_volume -= old_volume
        
        # Add new values
        pv = price * volume
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        self.price_volume.append(pv)
        
        # Update cumulative sums
        self.cumulative_pv += pv
        self.cumulative_volume += volume
        
        # Calculate returns
        if len(self.prices) >= 2:
            return_val = (price - self.prices[-2]) / self.prices[-2]
            self.returns.append(return_val)
    
    def get_vwap(self) -> Optional[float]:
        """Calculate Volume Weighted Average Price"""
        if self.cumulative_volume == 0:
            return None
        return self.cumulative_pv / self.cumulative_volume
    
    def get_volatility(self) -> Optional[float]:
        """Calculate rolling volatility (standard deviation of returns)"""
        if len(self.returns) < 10:
            return None
        return np.std(list(self.returns))
    
    def get_price_deviation_from_vwap(self, current_price: float) -> Optional[float]:
        """Get price deviation from VWAP in volatility units"""
        vwap = self.get_vwap()
        volatility = self.get_volatility()
        
        if vwap is None or volatility is None or volatility == 0:
            return None
        
        return (current_price - vwap) / volatility
    
    def get_volume_spike(self, current_volume: float, lookback: int = 20) -> float:
        """Detect volume spikes compared to recent average"""
        if len(self.volumes) < lookback:
            return 1.0
        
        recent_volumes = list(self.volumes)[-lookback:]
        avg_volume = np.mean(recent_volumes)
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def get_momentum(self, periods: int = 10) -> Optional[float]:
        """Calculate price momentum over specified periods"""
        if len(self.prices) < periods + 1:
            return None
        
        current_price = self.prices[-1]
        past_price = self.prices[-(periods + 1)]
        
        return (current_price - past_price) / past_price

class ScalpingSignalGenerator:
    """
    Main signal generator for scalping strategies
    Combines multiple indicators for signal generation
    """
    
    def __init__(self, symbol: str, config: Dict):
        self.symbol = symbol
        self.config = config
        
        # Initialize indicators
        self.indicators = TechnicalIndicators(config.get('window_size', 60))
        
        self.mean_reversion_threshold = config.get('mean_reversion_threshold', 3.0)  # volatility units
        self.breakout_threshold = config.get('breakout_threshold', 2.0)  # volatility units
        self.volume_spike_threshold = config.get('volume_spike_threshold', 2.5)
        self.ob_imbalance_threshold = config.get('ob_imbalance_threshold', 0.35)
        # Strategy parameters (more selective defaults)

        # Signal history
        self.signal_history = deque(maxlen=100)
        self.last_signal_time = 0
        self.min_signal_interval = config.get('min_signal_interval', 10)  # seconds (reduce noise)
    
    def update_data(self, price: float, volume: float, orderbook_imbalance: float, timestamp: float = None):
        """Update indicators with new market data"""
        if timestamp is None:
            timestamp = time.time()
        
        self.indicators.add_tick(price, volume, timestamp)
        self.current_price = price
        self.current_volume = volume
        self.current_ob_imbalance = orderbook_imbalance
        self.current_timestamp = timestamp
    
    def generate_signals(self) -> List[Signal]:
        """Generate trading signals based on current market conditions"""
        signals = []
        
        # Avoid generating signals too frequently
        if self.current_timestamp - self.last_signal_time < self.min_signal_interval:
            return signals
        
        # Get current indicators
        vwap = self.indicators.get_vwap()
        volatility = self.indicators.get_volatility()
        price_deviation = self.indicators.get_price_deviation_from_vwap(self.current_price)
        volume_spike = self.indicators.get_volume_spike(self.current_volume)
        momentum = self.indicators.get_momentum()
        
        if None in [vwap, volatility, price_deviation, momentum]:
            return signals
        
        # Mean Reversion Strategy
        mean_rev_signal = self._check_mean_reversion(
            price_deviation, volume_spike, momentum
        )
        if mean_rev_signal:
            signals.append(mean_rev_signal)
        
        # Breakout Strategy
        breakout_signal = self._check_breakout(
            price_deviation, volume_spike, momentum
        )
        if breakout_signal:
            signals.append(breakout_signal)
        
        # Update signal history
        for signal in signals:
            self.signal_history.append(signal)
            self.last_signal_time = self.current_timestamp
        
        return signals
    
    def _check_mean_reversion(self, price_deviation: float, volume_spike: float, momentum: float) -> Optional[Signal]:
        """Check for mean reversion signals"""
        # Price must deviate significantly from VWAP
        if abs(price_deviation) < self.mean_reversion_threshold:
            return None
        
        # Order book imbalance should confirm the reversal and be above threshold
        expected_imbalance_direction = -np.sign(price_deviation)
        if np.sign(self.current_ob_imbalance) != expected_imbalance_direction:
            return None
        if abs(self.current_ob_imbalance) < self.ob_imbalance_threshold:
            return None
        
        # Calculate signal strength
        deviation_strength = min(abs(price_deviation) / self.mean_reversion_threshold, 3.0) / 3.0
        imbalance_strength = min(abs(self.current_ob_imbalance), 1.0)
        volume_strength = min(volume_spike / self.volume_spike_threshold, 2.0) / 2.0
        
        signal_strength = (deviation_strength + imbalance_strength + volume_strength) / 3.0
        
        # Minimum signal strength threshold (more selective)
        if signal_strength < 0.65:
            return None
        
        # Determine signal direction con stop loss e take profit più realistici
        if price_deviation > 0:  # Price above VWAP, expect reversion down
            signal_type = SignalType.MEAN_REVERSION_SHORT
            entry_price = self.current_price
            # Take profit: fixed small move toward mean (0.6%) for scalping
            take_profit = entry_price * 0.994  # short: expect price to move down
            # Stop loss: tighter 0.5% above entry
            stop_loss = entry_price * 1.005
        else:  # Price below VWAP, expect reversion up
            signal_type = SignalType.MEAN_REVERSION_LONG
            entry_price = self.current_price
            # Take profit: fixed small move toward mean (0.6%) for scalping
            take_profit = entry_price * 1.006
            # Stop loss: tighter 0.5% below entry
            stop_loss = entry_price * 0.995
        
        return Signal(
            signal_type=signal_type,
            strength=signal_strength,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=self.current_timestamp,
            metadata={
                'price_deviation': price_deviation,
                'ob_imbalance': self.current_ob_imbalance,
                'volume_spike': volume_spike,
                'vwap': self.indicators.get_vwap(),
                'volatility': self.indicators.get_volatility()
            }
        )
    
    def _check_breakout(self, price_deviation: float, volume_spike: float, momentum: float) -> Optional[Signal]:
        """Check for breakout signals"""
        # Price must break through VWAP +/- threshold
        if abs(price_deviation) < self.breakout_threshold:
            return None
        
        # Require volume spike
        if volume_spike < self.volume_spike_threshold:
            return None
        
        # Momentum should align with breakout direction
        if np.sign(momentum) != np.sign(price_deviation):
            return None
        
        # Order book imbalance should support the breakout direction
        if np.sign(self.current_ob_imbalance) != np.sign(price_deviation):
            return None
        
        # Calculate signal strength
        deviation_strength = min(abs(price_deviation) / self.breakout_threshold, 3.0) / 3.0
        volume_strength = min(volume_spike / self.volume_spike_threshold, 3.0) / 3.0
        momentum_strength = min(abs(momentum) * 100, 2.0) / 2.0  # momentum is typically small
        imbalance_strength = min(abs(self.current_ob_imbalance), 1.0)
        
        signal_strength = (deviation_strength + volume_strength + momentum_strength + imbalance_strength) / 4.0
        
        # Minimum signal strength threshold (more selective)
        if signal_strength < 0.7:
            return None
        
        # Determine signal direction con livelli fissi
        if price_deviation > 0:  # Upward breakout
            signal_type = SignalType.BREAKOUT_LONG
            entry_price = self.current_price
            # Stop loss e take profit fissi per breakout (improve R:R)
            stop_loss = entry_price * 0.995  # 0.5% stop loss
            take_profit = entry_price * 1.015  # 1.5% take profit (~3:1 R/R)
        else:  # Downward breakout
            signal_type = SignalType.BREAKOUT_SHORT
            entry_price = self.current_price
            stop_loss = entry_price * 1.005  # 0.5% stop loss
            take_profit = entry_price * 0.985  # 1.5% take profit (~3:1 R/R)
        
        return Signal(
            signal_type=signal_type,
            strength=signal_strength,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=self.current_timestamp,
            metadata={
                'price_deviation': price_deviation,
                'ob_imbalance': self.current_ob_imbalance,
                'volume_spike': volume_spike,
                'momentum': momentum,
                'vwap': self.indicators.get_vwap(),
                'volatility': self.indicators.get_volatility()
            }
        )
    
    def get_signal_summary(self) -> Dict:
        """Get summary of recent signals"""
        if not self.signal_history:
            return {'total_signals': 0}
        
        recent_signals = [s for s in self.signal_history if self.current_timestamp - s.timestamp < 3600]  # Last hour
        
        signal_counts = {}
        for signal in recent_signals:
            signal_type = signal.signal_type.value
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
        
        avg_strength = np.mean([s.strength for s in recent_signals]) if recent_signals else 0
        
        return {
            'total_signals': len(recent_signals),
            'signal_counts': signal_counts,
            'avg_strength': avg_strength,
            'last_signal_time': self.signal_history[-1].timestamp if self.signal_history else 0
        }

class MultiSymbolSignalManager:
    """
    Manages signal generation for multiple symbols
    Provides portfolio-level signal coordination
    """
    
    def __init__(self, symbols: List[str], config: Dict):
        self.symbols = symbols
        self.config = config
        self.generators = {}
        
        # Initialize signal generators for each symbol
        for symbol in symbols:
            self.generators[symbol] = ScalpingSignalGenerator(symbol, config)
    
    def update_market_data(self, symbol: str, price: float, volume: float, 
                          orderbook_imbalance: float, timestamp: float = None):
        """Update market data for specific symbol"""
        if symbol in self.generators:
            self.generators[symbol].update_data(price, volume, orderbook_imbalance, timestamp)
    
    def get_all_signals(self) -> Dict[str, List[Signal]]:
        """Get signals from all symbols"""
        all_signals = {}
        for symbol, generator in self.generators.items():
            signals = generator.generate_signals()
            if signals:
                all_signals[symbol] = signals
        return all_signals
    
    def get_best_signal(self) -> Optional[Tuple[str, Signal]]:
        """Get the highest strength signal across all symbols"""
        best_signal = None
        best_symbol = None
        best_strength = 0
        
        all_signals = self.get_all_signals()
        for symbol, signals in all_signals.items():
            for signal in signals:
                if signal.strength > best_strength:
                    best_strength = signal.strength
                    best_signal = signal
                    best_symbol = symbol
        
        return (best_symbol, best_signal) if best_signal else None
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio-wide signal summary"""
        summaries = {}
        for symbol, generator in self.generators.items():
            summaries[symbol] = generator.get_signal_summary()
        
        total_signals = sum(s['total_signals'] for s in summaries.values())
        
        return {
            'symbols': summaries,
            'total_portfolio_signals': total_signals,
            'active_symbols': len([s for s in summaries.values() if s['total_signals'] > 0])
        }

# Example usage
if __name__ == "__main__":
    # Test signal generation
    config = {
        'window_size': 60,
        'mean_reversion_threshold': 2.0,
        'breakout_threshold': 1.5,
        'volume_spike_threshold': 2.0,
        'ob_imbalance_threshold': 0.3,
        'min_signal_interval': 5
    }
    
    generator = ScalpingSignalGenerator("BTCUSDT", config)
    
    # Simulate some market data
    import random
    base_price = 50000
    
    for i in range(100):
        price = base_price + random.gauss(0, 100)
        volume = random.uniform(0.1, 2.0)
        ob_imbalance = random.uniform(-0.5, 0.5)
        
        generator.update_data(price, volume, ob_imbalance)
        signals = generator.generate_signals()
        
        if signals:
            for signal in signals:
                print(f"Signal: {signal.signal_type.value}, Strength: {signal.strength:.2f}, Price: ${signal.entry_price:.2f}")
        
        time.sleep(0.1)  # Simulate real-time data
