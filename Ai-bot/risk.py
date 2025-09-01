"""
Risk Management Module
Comprehensive risk management for scalping operations
Includes position sizing, stop-loss management, and portfolio-level risk controls
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    total_exposure: float
    max_loss_potential: float
    current_drawdown: float
    daily_pnl: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    max_drawdown: float
    risk_level: RiskLevel

class PositionRiskManager:
    """
    Individual position risk management
    Handles position sizing, stop-loss, and position-level risk controls
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Position sizing parameters
        self.default_risk_per_trade = config.get('risk_per_trade', 0.01)  # 1% of capital
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)  # 2% max
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% of capital
        
        # Stop-loss parameters
        self.min_stop_distance = config.get('min_stop_distance', 0.001)  # 0.1% minimum
        self.max_stop_distance = config.get('max_stop_distance', 0.05)   # 5% maximum
        self.use_atr_stops = config.get('use_atr_stops', True)
        
        # Position limits
        self.max_leverage = config.get('max_leverage', 3.0)
        
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              available_capital: float, signal_strength: float = 1.0,
                              volatility: float = None) -> float:
        """
        Calculate optimal position size based on risk parameters
        
        Args:
            entry_price: Intended entry price
            stop_loss: Stop loss price
            available_capital: Available trading capital
            signal_strength: Signal confidence (0-1)
            volatility: Current volatility measure
            
        Returns:
            Position size in base currency
        """
        # Base risk amount
        base_risk = available_capital * self.default_risk_per_trade
        
        # Adjust risk based on signal strength
        risk_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5x to 1.0x
        adjusted_risk = base_risk * risk_multiplier
        
        # Adjust for volatility if available
        if volatility:
            vol_adjustment = max(0.5, min(2.0, 1.0 / volatility))  # Inverse relationship
            adjusted_risk *= vol_adjustment
        
        # Ensure risk is within limits
        adjusted_risk = min(adjusted_risk, available_capital * self.max_risk_per_trade)
        
        # Calculate position size
        risk_distance = abs(entry_price - stop_loss)
        if risk_distance < self.min_stop_distance * entry_price:
            logger.warning(f"Stop loss too tight: {risk_distance/entry_price:.4f}, adjusting")
            risk_distance = self.min_stop_distance * entry_price
            
        if risk_distance > self.max_stop_distance * entry_price:
            logger.warning(f"Stop loss too wide: {risk_distance/entry_price:.4f}, adjusting")
            risk_distance = self.max_stop_distance * entry_price
        
        position_size = adjusted_risk / risk_distance if risk_distance > 0 else 0
        
        # Apply maximum position size limit
        max_size_by_capital = (available_capital * self.max_position_size) / entry_price
        position_size = min(position_size, max_size_by_capital)
        
        # Apply leverage limit
        max_size_by_leverage = (available_capital * self.max_leverage) / entry_price
        position_size = min(position_size, max_size_by_leverage)
        
        return max(0, position_size)
    
    def validate_stop_loss(self, entry_price: float, stop_loss: float, side: str) -> Tuple[bool, float]:
        """
        Validate and adjust stop loss levels
        
        Args:
            entry_price: Position entry price
            stop_loss: Proposed stop loss price
            side: 'long' or 'short'
            
        Returns:
            (is_valid, adjusted_stop_loss)
        """
        stop_distance = abs(entry_price - stop_loss) / entry_price
        
        # Check minimum distance
        if stop_distance < self.min_stop_distance:
            logger.warning(f"Stop loss too tight: {stop_distance:.4f}, adjusting to minimum")
            if side.lower() == 'long':
                adjusted_stop = entry_price * (1 - self.min_stop_distance)
            else:
                adjusted_stop = entry_price * (1 + self.min_stop_distance)
            return True, adjusted_stop
        
        # Check maximum distance
        if stop_distance > self.max_stop_distance:
            logger.warning(f"Stop loss too wide: {stop_distance:.4f}, adjusting to maximum")
            if side.lower() == 'long':
                adjusted_stop = entry_price * (1 - self.max_stop_distance)
            else:
                adjusted_stop = entry_price * (1 + self.max_stop_distance)
            return True, adjusted_stop
        
        return True, stop_loss
    
    def calculate_dynamic_stop(self, entry_price: float, side: str, atr: float, 
                             atr_multiplier: float = 2.0) -> float:
        """Calculate dynamic stop loss based on ATR"""
        if not self.use_atr_stops or not atr:
            return entry_price
        
        stop_distance = atr * atr_multiplier
        
        if side.lower() == 'long':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

class PortfolioRiskManager:
    """
    Portfolio-level risk management
    Monitors overall portfolio risk and implements kill switches
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Portfolio risk limits
        self.max_daily_loss = config.get('max_daily_loss', -0.02)  # -2% daily loss limit
        self.max_total_exposure = config.get('max_total_exposure', 0.5)  # 50% of capital
        self.max_correlation_exposure = config.get('max_correlation_exposure', 0.3)  # 30% in correlated positions
        self.max_positions = config.get('max_positions', 10)
        
        # Drawdown limits
        self.max_drawdown = config.get('max_drawdown', -0.05)  # -5% maximum drawdown
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        
        # Risk monitoring
        self.daily_start_capital = 0
        self.current_capital = 0
        self.daily_pnl = 0
        self.peak_capital = 0
        self.consecutive_losses = 0
        self.risk_status = RiskLevel.LOW
        
        # Trade history for risk calculations
        self.trade_history = deque(maxlen=100)
        self.daily_pnl_history = deque(maxlen=30)  # Last 30 days
        
        # Kill switch status
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        
    def update_capital(self, current_capital: float, trade_pnl: float = None):
        """Update portfolio capital and risk metrics"""
        # Initialize daily start capital if not set
        if self.daily_start_capital == 0:
            self.daily_start_capital = current_capital
            self.peak_capital = current_capital
        
        self.current_capital = current_capital
        self.peak_capital = max(self.peak_capital, current_capital)
        
        # Update daily PnL
        self.daily_pnl = current_capital - self.daily_start_capital
        
        # Track individual trade
        if trade_pnl is not None:
            self.trade_history.append({
                'pnl': trade_pnl,
                'timestamp': time.time()
            })
            
            # Track consecutive losses
            if trade_pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
        
        # Update risk level
        self._update_risk_level()
        
        # Check kill switch conditions
        self._check_kill_switch()
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        # Current drawdown
        current_drawdown = (self.current_capital - self.peak_capital) / self.peak_capital
        
        # Calculate VaR 95%
        recent_pnls = [trade['pnl'] for trade in self.trade_history if 
                      time.time() - trade['timestamp'] < 86400]  # Last 24 hours
        var_95 = np.percentile(recent_pnls, 5) if len(recent_pnls) > 10 else 0
        
        # Calculate Sharpe ratio
        if len(recent_pnls) > 1:
            sharpe = np.mean(recent_pnls) / np.std(recent_pnls) if np.std(recent_pnls) > 0 else 0
        else:
            sharpe = 0
        
        # Maximum drawdown
        daily_pnls = list(self.daily_pnl_history)
        if daily_pnls:
            cumulative = np.cumsum(daily_pnls)
            max_dd = np.min(cumulative - np.maximum.accumulate(cumulative))
        else:
            max_dd = 0
        
        return RiskMetrics(
            total_exposure=0,  # Will be calculated externally
            max_loss_potential=0,  # Will be calculated externally
            current_drawdown=current_drawdown,
            daily_pnl=self.daily_pnl,
            var_95=var_95,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            risk_level=self.risk_status
        )
    
    def check_position_limits(self, open_positions: Dict, new_position_size: float) -> Tuple[bool, str]:
        """Check if new position violates portfolio limits"""
        # Check maximum number of positions
        if len(open_positions) >= self.max_positions:
            return False, f"Maximum positions limit reached: {self.max_positions}"
        
        # Check total exposure (will be implemented with position data)
        total_exposure = sum(pos.get('size', 0) * pos.get('price', 0) for pos in open_positions.values())
        new_exposure = total_exposure + new_position_size
        
        max_allowed_exposure = self.current_capital * self.max_total_exposure
        if new_exposure > max_allowed_exposure:
            return False, f"Total exposure limit exceeded: {new_exposure:.2f} > {max_allowed_exposure:.2f}"
        
        return True, ""
    
    def should_reduce_risk(self) -> Tuple[bool, str]:
        """Determine if risk should be reduced"""
        reasons = []
        
        # Check daily loss limit
        daily_loss_pct = self.daily_pnl / self.daily_start_capital if self.daily_start_capital > 0 else 0
        if daily_loss_pct <= self.max_daily_loss:
            reasons.append(f"Daily loss limit hit: {daily_loss_pct:.2%}")
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            reasons.append(f"Consecutive losses limit: {self.consecutive_losses}")
        
        # Check drawdown
        current_dd = (self.current_capital - self.peak_capital) / self.peak_capital
        if current_dd <= self.max_drawdown:
            reasons.append(f"Maximum drawdown hit: {current_dd:.2%}")
        
        return len(reasons) > 0, "; ".join(reasons)
    
    def _update_risk_level(self):
        """Update current risk level based on metrics"""
        daily_loss_pct = abs(self.daily_pnl / self.daily_start_capital) if self.daily_start_capital > 0 else 0
        drawdown_pct = abs((self.current_capital - self.peak_capital) / self.peak_capital)
        
        # Determine risk level
        if daily_loss_pct >= abs(self.max_daily_loss) * 0.8 or drawdown_pct >= abs(self.max_drawdown) * 0.8:
            self.risk_status = RiskLevel.CRITICAL
        elif daily_loss_pct >= abs(self.max_daily_loss) * 0.6 or drawdown_pct >= abs(self.max_drawdown) * 0.6:
            self.risk_status = RiskLevel.HIGH
        elif daily_loss_pct >= abs(self.max_daily_loss) * 0.3 or drawdown_pct >= abs(self.max_drawdown) * 0.3:
            self.risk_status = RiskLevel.MEDIUM
        else:
            self.risk_status = RiskLevel.LOW
    
    def _check_kill_switch(self):
        """Check if kill switch should be activated"""
        if self.kill_switch_active:
            return
        
        reasons = []
        
        # Daily loss limit
        daily_loss_pct = self.daily_pnl / self.daily_start_capital if self.daily_start_capital > 0 else 0
        if daily_loss_pct <= self.max_daily_loss:
            reasons.append(f"Daily loss limit exceeded: {daily_loss_pct:.2%}")
        
        # Maximum drawdown
        current_dd = (self.current_capital - self.peak_capital) / self.peak_capital
        if current_dd <= self.max_drawdown:
            reasons.append(f"Maximum drawdown exceeded: {current_dd:.2%}")
        
        # Activate kill switch if any condition is met
        if reasons:
            self.kill_switch_active = True
            self.kill_switch_reason = "; ".join(reasons)
            logger.critical(f"KILL SWITCH ACTIVATED: {self.kill_switch_reason}")
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new trading day)"""
        # Save yesterday's PnL
        if self.daily_start_capital > 0:
            daily_return = self.daily_pnl / self.daily_start_capital
            self.daily_pnl_history.append(daily_return)
        
        # Reset daily metrics
        self.daily_start_capital = self.current_capital
        self.daily_pnl = 0
        self.consecutive_losses = 0
        
        # Reset kill switch if not critical
        if self.risk_status != RiskLevel.CRITICAL:
            self.kill_switch_active = False
            self.kill_switch_reason = ""
        
        logger.info("Daily risk metrics reset")
    
    def force_reset_kill_switch(self, reason: str = "Manual reset"):
        """Manually reset kill switch (use with caution)"""
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        logger.warning(f"Kill switch manually reset: {reason}")

class RiskManager:
    """
    Main risk management coordinator
    Combines position and portfolio risk management
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.position_risk = PositionRiskManager(config.get('position_risk', {}))
        self.portfolio_risk = PortfolioRiskManager(config.get('portfolio_risk', {}))
        
        # Risk monitoring
        self.risk_alerts = deque(maxlen=50)
        
    def evaluate_trade_risk(self, entry_price: float, stop_loss: float, side: str,
                           available_capital: float, signal_strength: float = 1.0,
                           open_positions: Dict = None) -> Tuple[bool, float, str]:
        """
        Comprehensive trade risk evaluation
        
        Returns:
            (can_trade, position_size, reason)
        """
        if open_positions is None:
            open_positions = {}
        
        # Check kill switch
        if self.portfolio_risk.kill_switch_active:
            return False, 0, f"Kill switch active: {self.portfolio_risk.kill_switch_reason}"
        
        # Check if risk should be reduced
        should_reduce, reduce_reason = self.portfolio_risk.should_reduce_risk()
        if should_reduce:
            # Allow trading but with reduced size
            signal_strength *= 0.5
            self._add_risk_alert(f"Risk reduction active: {reduce_reason}")
        
        # Validate stop loss
        valid_stop, adjusted_stop = self.position_risk.validate_stop_loss(entry_price, stop_loss, side)
        if not valid_stop:
            return False, 0, "Invalid stop loss"
        
        # Calculate position size
        position_size = self.position_risk.calculate_position_size(
            entry_price, adjusted_stop, available_capital, signal_strength
        )
        
        if position_size <= 0:
            return False, 0, "Position size too small"
        
        # Check portfolio limits
        position_value = position_size * entry_price
        can_add, limit_reason = self.portfolio_risk.check_position_limits(open_positions, position_value)
        if not can_add:
            return False, 0, limit_reason
        
        return True, position_size, "Risk checks passed"
    
    def update_portfolio(self, current_capital: float, trade_pnl: float = None):
        """Update portfolio risk metrics"""
        self.portfolio_risk.update_capital(current_capital, trade_pnl)
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        metrics = self.portfolio_risk.get_risk_metrics()
        
        return {
            'risk_level': metrics.risk_level.value,
            'daily_pnl': metrics.daily_pnl,
            'daily_pnl_pct': metrics.daily_pnl / self.portfolio_risk.daily_start_capital * 100 
                             if self.portfolio_risk.daily_start_capital > 0 else 0,
            'current_drawdown': metrics.current_drawdown * 100,
            'max_drawdown': metrics.max_drawdown * 100,
            'var_95': metrics.var_95,
            'sharpe_ratio': metrics.sharpe_ratio,
            'consecutive_losses': self.portfolio_risk.consecutive_losses,
            'kill_switch_active': self.portfolio_risk.kill_switch_active,
            'kill_switch_reason': self.portfolio_risk.kill_switch_reason,
            'recent_alerts': list(self.risk_alerts)[-10:]  # Last 10 alerts
        }
    
    def _add_risk_alert(self, message: str):
        """Add risk alert to history"""
        alert = {
            'timestamp': time.time(),
            'message': message
        }
        self.risk_alerts.append(alert)
        logger.warning(f"Risk Alert: {message}")
    
    def force_close_recommended(self) -> Tuple[bool, str]:
        """Check if forced position closure is recommended"""
        if self.portfolio_risk.kill_switch_active:
            return True, "Kill switch active"
        
        if self.portfolio_risk.risk_status == RiskLevel.CRITICAL:
            return True, "Critical risk level reached"
        
        return False, ""
    
    def reset_daily_metrics(self):
        """Reset daily risk metrics"""
        self.portfolio_risk.reset_daily_metrics()

# Example usage and testing
if __name__ == "__main__":
    # Risk management configuration
    risk_config = {
        'position_risk': {
            'risk_per_trade': 0.01,
            'max_risk_per_trade': 0.02,
            'max_position_size': 0.1,
            'min_stop_distance': 0.001,
            'max_stop_distance': 0.05,
            'max_leverage': 3.0
        },
        'portfolio_risk': {
            'max_daily_loss': -0.02,
            'max_total_exposure': 0.5,
            'max_drawdown': -0.05,
            'max_consecutive_losses': 5,
            'max_positions': 10
        }
    }
    
    # Initialize risk manager
    risk_manager = RiskManager(risk_config)
    
    # Test trade evaluation
    available_capital = 10000
    entry_price = 50000
    stop_loss = 49500  # 1% stop
    
    can_trade, position_size, reason = risk_manager.evaluate_trade_risk(
        entry_price, stop_loss, 'long', available_capital, 0.8
    )
    
    print(f"Can trade: {can_trade}")
    print(f"Position size: {position_size:.4f}")
    print(f"Reason: {reason}")
    
    # Update portfolio
    risk_manager.update_portfolio(available_capital)
    
    # Get risk summary
    summary = risk_manager.get_risk_summary()
    print(f"Risk Summary: {summary}")
