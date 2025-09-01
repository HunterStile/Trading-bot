"""
Strategy Module - Trading strategy implementations
Mean reversion and breakout strategies with entry/exit logic
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import numpy as np

from signals import Signal, SignalType

logger = logging.getLogger(__name__)

class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"

class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"

@dataclass
class Position:
    """Trading position data structure"""
    symbol: str
    side: PositionSide
    entry_price: float
    size: float
    entry_time: float
    strategy: str
    signal_strength: float
    
    # Exit parameters
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    max_holding_time: Optional[float] = None
    
    # Status tracking
    status: PositionStatus = PositionStatus.PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[float] = None
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None
    
    # Runtime data
    highest_price: float = field(init=False)
    lowest_price: float = field(init=False)
    current_price: float = field(init=False)
    last_update_time: float = field(init=False)
    
    def __post_init__(self):
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price
        self.current_price = self.entry_price
        # Use entry_time as initial last update time (simulation timestamp expected)
        try:
            self.last_update_time = float(self.entry_time)
        except Exception:
            self.last_update_time = time.time()
    
    def update_price(self, price: float, timestamp: float = None):
        """Update current price and track extremes. Accepts simulation timestamp (epoch seconds)."""
        self.current_price = price
        self.highest_price = max(self.highest_price, price)
        self.lowest_price = min(self.lowest_price, price)
        if timestamp is not None:
            try:
                self.last_update_time = float(timestamp)
            except Exception:
                # fallback to entry_time if conversion fails
                pass
    
    def get_unrealized_pnl(self) -> float:
        """Calculate unrealized PnL"""
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size
    
    def get_duration(self) -> float:
        """Get position duration in seconds using simulation times when available."""
        # Prefer explicit exit_time, then last_update_time (simulation), then wall clock
        if self.exit_time:
            current_time = self.exit_time
        elif getattr(self, 'last_update_time', None) is not None:
            current_time = self.last_update_time
        else:
            current_time = time.time()

        return float(current_time) - float(self.entry_time)

class BaseStrategy:
    """Base class for trading strategies"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.positions = {}  # symbol -> position
        self.closed_positions = deque(maxlen=1000)
        
        # Strategy statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
    def should_enter(self, signal: Signal) -> bool:
        """Determine if strategy should enter based on signal"""
        raise NotImplementedError
    
    def should_exit(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """Determine if position should be closed"""
        raise NotImplementedError
    
    def calculate_position_size(self, signal: Signal, available_capital: float) -> float:
        """Calculate position size for the signal"""
        raise NotImplementedError
    
    def enter_position(self, symbol: str, signal: Signal, size: float) -> Position:
        """Create new position from signal"""
        side = PositionSide.LONG if 'long' in signal.signal_type.value else PositionSide.SHORT
        
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=signal.entry_price,
            size=size,
            entry_time=signal.timestamp,
            strategy=self.name,
            signal_strength=signal.strength,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            max_holding_time=self.max_holding_time  # Usa il valore della strategia specifica
        )
        
        self.positions[symbol] = position
        logger.info(f"Entered {side.value} position for {symbol} at ${signal.entry_price:.4f}, size: {size}")
        
        return position
    
    def exit_position(self, symbol: str, exit_price: float, reason: str, timestamp: float = None) -> Optional[Position]:
        """Close existing position"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.exit_price = exit_price
        # Use provided simulation timestamp when available
        if timestamp is not None:
            position.exit_time = float(timestamp)
        else:
            position.exit_time = time.time()
        position.status = PositionStatus.CLOSED
        position.exit_reason = reason
        position.pnl = position.get_unrealized_pnl()
        
        # Update statistics
        self.total_trades += 1
        self.total_pnl += position.pnl
        if position.pnl > 0:
            self.winning_trades += 1
        
        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[symbol]
        
        logger.info(f"Closed {position.side.value} position for {symbol} at ${exit_price:.4f}, "
                   f"PnL: ${position.pnl:.2f}, Reason: {reason}")
        
        return position
    
    def update_positions(self, market_data: Dict[str, float]):
        """Update all open positions with current market data"""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]
                position.update_price(current_price)
                
                # Check exit conditions
                should_exit, exit_reason = self.should_exit(position, current_price)
                if should_exit:
                    positions_to_close.append((symbol, current_price, exit_reason))
        
        # Close positions that meet exit criteria
        for symbol, exit_price, reason in positions_to_close:
            self.exit_position(symbol, exit_price, reason)
    
    def get_strategy_stats(self) -> Dict:
        """Get strategy performance statistics"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        avg_pnl = self.total_pnl / self.total_trades if self.total_trades > 0 else 0
        
        recent_trades = list(self.closed_positions)[-50:]  # Last 50 trades
        recent_pnl = [p.pnl for p in recent_trades]
        
        return {
            'strategy_name': self.name,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl_per_trade': avg_pnl,
            'recent_avg_pnl': np.mean(recent_pnl) if recent_pnl else 0,
            'open_positions': len(self.positions),
            'sharpe_ratio': self._calculate_sharpe_ratio(recent_pnl)
        }
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio from trade returns"""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = np.array(returns) - risk_free_rate
        return np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0

class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion scalping strategy
    Enters when price deviates significantly from VWAP with confirming signals
    """
    
    def __init__(self, config: Dict):
        super().__init__("MeanReversion", config)
        
        # Strategy-specific parameters
        self.min_signal_strength = config.get('mean_reversion_min_signal_strength', 0.4)
        self.risk_per_trade = config.get('mean_reversion_risk_per_trade', 0.015)
        self.max_holding_time = config.get('mean_reversion_max_holding_time', 900)  # 15 minuti
        self.profit_target_ratio = config.get('mean_reversion_profit_target_ratio', 0.8)
    
    def should_enter(self, signal: Signal) -> bool:
        """Check if signal meets mean reversion entry criteria"""
        # Only process mean reversion signals
        if signal.signal_type not in [SignalType.MEAN_REVERSION_LONG, SignalType.MEAN_REVERSION_SHORT]:
            return False
        
        # Signal strength must meet minimum threshold
        if signal.strength < self.min_signal_strength:
            return False
        
        # Additional validation based on metadata
        if signal.metadata:
            # Ensure significant deviation from VWAP
            price_deviation = abs(signal.metadata.get('price_deviation', 0))
            if price_deviation < 1.5:  # Minimum 1.5 standard deviations
                return False
            
            # Require order book imbalance confirmation
            ob_imbalance = signal.metadata.get('ob_imbalance', 0)
            if abs(ob_imbalance) < 0.2:  # Minimum 20% imbalance
                return False
        
        return True
    
    def should_exit(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """Check mean reversion exit conditions"""
        # Stop loss hit
        if position.side == PositionSide.LONG:
            if current_price <= position.stop_loss:
                return True, "Stop Loss"
        else:
            if current_price >= position.stop_loss:
                return True, "Stop Loss"
        
        # Take profit hit (partial move to VWAP)
        if position.side == PositionSide.LONG:
            if current_price >= position.take_profit:
                return True, "Take Profit"
        else:
            if current_price <= position.take_profit:
                return True, "Take Profit"
        
        # Maximum holding time exceeded
        if position.get_duration() > self.max_holding_time:
            return True, "Timeout"
        
        # Emergency exit if loss exceeds 2x expected
        unrealized_pnl = position.get_unrealized_pnl()
        expected_risk = abs(position.entry_price - position.stop_loss) * position.size
        if unrealized_pnl < -2 * expected_risk:
            return True, "Emergency Stop"
        
        return False, ""
    
    def calculate_position_size(self, signal: Signal, available_capital: float) -> float:
        """Calculate position size based on risk management"""
        # Risk amount (1% of capital)
        risk_amount = available_capital * self.risk_per_trade
        
        # Distance to stop loss
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        
        # Position size = risk amount / risk per unit
        size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Apply maximum position size limits
        max_position_value = available_capital * 0.1  # Max 10% of capital per trade
        max_size = max_position_value / signal.entry_price
        
        return min(size, max_size)

class BreakoutStrategy(BaseStrategy):
    """
    Breakout scalping strategy
    Enters on VWAP breakouts with volume confirmation and trailing stops
    """
    
    def __init__(self, config: Dict):
        super().__init__("Breakout", config)
        
        # Strategy-specific parameters
        self.min_signal_strength = config.get('breakout_min_signal_strength', 0.5)
        self.risk_per_trade = config.get('breakout_risk_per_trade', 0.02)
        self.trailing_stop_distance = config.get('breakout_trailing_stop_distance', 0.3)
        self.profit_target_multiple = config.get('breakout_profit_target_multiple', 2.5)
        self.max_holding_time = config.get('breakout_max_holding_time', 1800)  # 30 minuti
    
    def should_enter(self, signal: Signal) -> bool:
        """Check if signal meets breakout entry criteria"""
        # Only process breakout signals
        if signal.signal_type not in [SignalType.BREAKOUT_LONG, SignalType.BREAKOUT_SHORT]:
            return False
        
        # Signal strength must meet minimum threshold
        if signal.strength < self.min_signal_strength:
            return False
        
        # Additional validation based on metadata
        if signal.metadata:
            # Require volume spike
            volume_spike = signal.metadata.get('volume_spike', 1.0)
            if volume_spike < 1.5:  # Minimum 50% above average volume
                return False
            
            # Require momentum alignment
            momentum = signal.metadata.get('momentum', 0)
            price_deviation = signal.metadata.get('price_deviation', 0)
            if np.sign(momentum) != np.sign(price_deviation):
                return False
        
        return True
    
    def should_exit(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """Check breakout exit conditions with trailing stop"""
        # Stop loss hit
        if position.side == PositionSide.LONG:
            if current_price <= position.stop_loss:
                return True, "Stop Loss"
        else:
            if current_price >= position.stop_loss:
                return True, "Stop Loss"
        
        # Update trailing stop
        if position.trailing_stop is None:
            position.trailing_stop = position.stop_loss
        
        # Trailing stop logic
        if position.side == PositionSide.LONG:
            # Update trailing stop if price moves favorably
            new_trailing_stop = current_price * (1 - self.trailing_stop_distance / 100)
            if new_trailing_stop > position.trailing_stop:
                position.trailing_stop = new_trailing_stop
            
            # Check trailing stop hit
            if current_price <= position.trailing_stop:
                return True, "Trailing Stop"
        else:
            # Short position trailing stop
            new_trailing_stop = current_price * (1 + self.trailing_stop_distance / 100)
            if new_trailing_stop < position.trailing_stop:
                position.trailing_stop = new_trailing_stop
            
            # Check trailing stop hit
            if current_price >= position.trailing_stop:
                return True, "Trailing Stop"
        
        # Take profit target
        if position.side == PositionSide.LONG:
            if current_price >= position.take_profit:
                return True, "Take Profit"
        else:
            if current_price <= position.take_profit:
                return True, "Take Profit"
        
        # Maximum holding time (short for breakouts)
        if position.get_duration() > self.max_holding_time:
            return True, "Timeout"
        
        return False, ""
    
    def calculate_position_size(self, signal: Signal, available_capital: float) -> float:
        """Calculate position size for breakout strategy"""
        # Risk amount (1% of capital)
        risk_amount = available_capital * self.risk_per_trade
        
        # Distance to stop loss
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        
        # Position size = risk amount / risk per unit
        size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Apply maximum position size limits (more conservative for breakouts)
        max_position_value = available_capital * 0.05  # Max 5% of capital per trade
        max_size = max_position_value / signal.entry_price
        
        return min(size, max_size)

class StrategyManager:
    """
    Manages multiple trading strategies
    Coordinates strategy execution and position management
    """
    
    def __init__(self, strategies: List[BaseStrategy]):
        self.strategies = {strategy.name: strategy for strategy in strategies}
        self.active_symbols = set()
        
        # Portfolio-level limits
        self.max_concurrent_positions = 5
        self.max_positions_per_symbol = 1
    
    def process_signals(self, signals: Dict[str, List[Signal]], available_capital: float) -> List[Tuple[str, str, Position]]:
        """
        Process signals from all strategies
        Returns list of (symbol, strategy_name, position) for new entries
        """
        new_positions = []
        
        # Count current positions
        total_positions = sum(len(strategy.positions) for strategy in self.strategies.values())
        
        if total_positions >= self.max_concurrent_positions:
            logger.warning("Maximum concurrent positions reached")
            return new_positions
        
        # Process signals for each symbol
        for symbol, symbol_signals in signals.items():
            # Check if symbol already has max positions
            symbol_positions = sum(1 for strategy in self.strategies.values() if symbol in strategy.positions)
            if symbol_positions >= self.max_positions_per_symbol:
                continue
            
            # Find best signal for this symbol
            best_signal = None
            best_strategy = None
            best_score = 0
            
            for signal in symbol_signals:
                for strategy in self.strategies.values():
                    if strategy.should_enter(signal):
                        # Score = signal strength * strategy performance
                        strategy_stats = strategy.get_strategy_stats()
                        strategy_score = strategy_stats.get('win_rate', 0.5)  # Default 50%
                        score = signal.strength * strategy_score
                        
                        if score > best_score:
                            best_score = score
                            best_signal = signal
                            best_strategy = strategy
            
            # Enter position with best strategy
            if best_signal and best_strategy:
                position_size = best_strategy.calculate_position_size(best_signal, available_capital)
                if position_size > 0:
                    position = best_strategy.enter_position(symbol, best_signal, position_size)
                    new_positions.append((symbol, best_strategy.name, position))
                    self.active_symbols.add(symbol)
        
        return new_positions
    
    def update_all_positions(self, market_data: Dict[str, float]):
        """Update all positions across all strategies"""
        for strategy in self.strategies.values():
            strategy.update_positions(market_data)
        
        # Update active symbols
        self.active_symbols = set()
        for strategy in self.strategies.values():
            self.active_symbols.update(strategy.positions.keys())
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        strategy_stats = {}
        total_positions = 0
        total_pnl = 0
        
        for name, strategy in self.strategies.items():
            stats = strategy.get_strategy_stats()
            strategy_stats[name] = stats
            total_positions += stats['open_positions']
            total_pnl += stats['total_pnl']
        
        return {
            'strategies': strategy_stats,
            'total_open_positions': total_positions,
            'total_portfolio_pnl': total_pnl,
            'active_symbols': list(self.active_symbols),
            'max_positions_limit': self.max_concurrent_positions
        }
    
    def get_open_positions(self) -> Dict[str, List[Position]]:
        """Get all open positions organized by strategy"""
        open_positions = {}
        for name, strategy in self.strategies.items():
            if strategy.positions:
                open_positions[name] = list(strategy.positions.values())
        return open_positions
    
    def force_close_all_positions(self, market_data: Dict[str, float], reason: str = "Force Close"):
        """Emergency close all open positions"""
        for strategy in self.strategies.values():
            for symbol in list(strategy.positions.keys()):
                if symbol in market_data:
                    strategy.exit_position(symbol, market_data[symbol], reason)
        
        logger.warning(f"Force closed all positions: {reason}")

# Example usage and configuration
if __name__ == "__main__":
    # Strategy configurations
    mean_reversion_config = {
        'min_signal_strength': 0.6,
        'risk_per_trade': 0.01,
        'max_holding_time': 60,
        'profit_target_ratio': 0.5
    }
    
    breakout_config = {
        'min_signal_strength': 0.7,
        'risk_per_trade': 0.01,
        'trailing_stop_distance': 0.5,
        'profit_target_multiple': 2.0,
        'max_holding_time': 15
    }
    
    # Initialize strategies
    mean_rev_strategy = MeanReversionStrategy(mean_reversion_config)
    breakout_strategy = BreakoutStrategy(breakout_config)
    
    # Create strategy manager
    strategy_manager = StrategyManager([mean_rev_strategy, breakout_strategy])
    
    print("Strategy Manager initialized with:")
    print(f"- {mean_rev_strategy.name}")
    print(f"- {breakout_strategy.name}")
    print(f"- Max concurrent positions: {strategy_manager.max_concurrent_positions}")
