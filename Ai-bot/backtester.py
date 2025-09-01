"""
Backtester Module - Historical backtesting for strategy validation
Tests strategies against historical data to validate performance before live trading
"""

import sys
import os
import sys
import os
# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import dependencies
from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time
import logging
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns

# Import from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, '.env'))

# Get API credentials directly
API_KEY = os.getenv('BYBIT_API_KEY', '')
API_SECRET = os.getenv('BYBIT_API_SECRET', '')

# Import local modules
from signals import ScalpingSignalGenerator, Signal, SignalType
from strategy import MeanReversionStrategy, BreakoutStrategy, PositionSide, PositionStatus
from risk import RiskManager

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    """Results from backtesting"""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # Performance metrics
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    
    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Risk metrics
    volatility: float
    var_95: float
    calmar_ratio: float
    
    # Trade details
    trades: List[Dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)

class HistoricalDataManager:
    """
    Manages historical data for backtesting
    Downloads and preprocesses OHLCV data
    """
    
    def __init__(self):
        self.data_cache = {}
    
    def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime,
                           interval: str = "1") -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for backtesting
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            start_date: Start date for data
            end_date: End date for data
            interval: Timeframe (1, 5, 15, 60, 240, D)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Create session with API credentials
            session = HTTP(
                testnet=False,
                api_key=API_KEY,
                api_secret=API_SECRET,
            )
            
            # Convert dates to timestamps
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # Download data using direct API call
            try:
                kline_response = session.get_kline(
                    category="linear",
                    symbol=symbol,
                    interval=interval,
                    start=start_timestamp,
                    end=end_timestamp,
                    limit=1000
                )
                
                if kline_response.get('retCode') != 0:
                    logger.error(f"API error: {kline_response.get('retMsg', 'Unknown error')}")
                    return None
                
                kline_data = kline_response.get('result', {}).get('list', [])
                
            except Exception as api_error:
                logger.error(f"API call failed: {api_error}")
                return None
            
            if not kline_data:
                logger.error(f"No data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            
            # Convert data types
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            logger.info(f"Downloaded {len(df)} data points for {symbol} from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading historical data for {symbol}: {e}")
            return None
    
    def generate_synthetic_orderbook_data(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate synthetic orderbook and volume data for backtesting
        Since we don't have historical tick data, we simulate realistic market microstructure
        """
        np.random.seed(42)  # For reproducible results
        
        synthetic_data = price_data.copy()
        
        # Calculate returns and volatility
        returns = price_data['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        
        # Generate synthetic bid-ask spread (typically 0.01-0.05% for major pairs)
        spread_base = 0.0002  # 0.02% base spread
        spread_vol_factor = volatility.fillna(volatility.mean()) * 10
        spreads = spread_base + spread_vol_factor.clip(0, 0.001)
        
        # Generate synthetic orderbook imbalance (-1 to 1)
        # More imbalanced during trending moves
        momentum = returns.rolling(window=5).mean()
        imbalance_base = np.tanh(momentum.fillna(0) * 50)  # Scale momentum to imbalance
        imbalance_noise = np.random.normal(0, 0.3, len(price_data))
        orderbook_imbalance = (imbalance_base + imbalance_noise).clip(-1, 1)
        
        # Generate synthetic volume spikes
        volume_ma = price_data['volume'].rolling(window=20).mean()
        volume_ratio = price_data['volume'] / volume_ma.fillna(volume_ma.mean())
        
        # Add synthetic data to DataFrame
        synthetic_data['spread'] = spreads
        synthetic_data['orderbook_imbalance'] = orderbook_imbalance
        synthetic_data['volume_ratio'] = volume_ratio.fillna(1.0)
        synthetic_data['returns'] = returns.fillna(0)
        synthetic_data['volatility'] = volatility.fillna(volatility.mean())
        
        return synthetic_data

class BacktestEngine:
    """
    Main backtesting engine
    Simulates trading strategies on historical data
    """
    
    def __init__(self, initial_capital: float = 10000, commission_rate: float = 0.0002):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate  # 0.02% commissione ridotta per VIP/Maker
        
        self.data_manager = HistoricalDataManager()
        
        # Backtesting state
        self.current_capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.timestamps = []
        
        # Performance tracking
        self.peak_capital = initial_capital
        self.max_drawdown = 0
        
    def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime,
                    strategy_configs: Dict, signal_config: Dict, risk_config: Dict,
                    interval: str = "1") -> BacktestResult:
        """
        Run complete backtest for given parameters
        
        Args:
            symbol: Trading pair to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            strategy_configs: Configuration for strategies
            signal_config: Configuration for signal generation
            risk_config: Configuration for risk management
            interval: Data interval (1m, 5m, etc.)
            
        Returns:
            BacktestResult with comprehensive performance metrics
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Reset state
        self._reset_state()
        
        # Get historical data
        data = self.data_manager.get_historical_data(symbol, start_date, end_date, interval)
        if data is None or len(data) == 0:
            logger.error("No historical data available for backtesting")
            return None
        
        # Generate synthetic market microstructure data
        data = self.data_manager.generate_synthetic_orderbook_data(data)
        
        # Initialize components
        signal_generator = ScalpingSignalGenerator(symbol, signal_config)
        
        # Initialize strategies
        mean_rev_strategy = MeanReversionStrategy(strategy_configs.get('mean_reversion', {}))
        breakout_strategy = BreakoutStrategy(strategy_configs.get('breakout', {}))
        strategies = [mean_rev_strategy, breakout_strategy]
        
        # Initialize risk manager
        risk_manager = RiskManager(risk_config)
        risk_manager.update_portfolio(self.current_capital)
        
        # Run simulation
        self._simulate_trading(data, signal_generator, strategies, risk_manager, symbol)
        
        # Calculate results
        result = self._calculate_results(symbol, start_date, end_date)
        
        logger.info(f"Backtest completed. Final capital: ${result.final_capital:.2f}, "
                   f"Total return: {result.total_return_pct:.2f}%, "
                   f"Trades: {result.total_trades}, Win rate: {result.win_rate:.2f}%")
        
        return result
    
    def _reset_state(self):
        """Reset backtesting state"""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = []
        self.peak_capital = self.initial_capital
        self.max_drawdown = 0
    
    def _simulate_trading(self, data: pd.DataFrame, signal_generator, strategies, risk_manager, symbol: str):
        """
        Main simulation loop
        """
        logger.info(f"Simulating trading on {len(data)} data points...")
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            try:
                # Update signal generator with current market data
                signal_generator.update_data(
                    price=row['close'],
                    volume=row['volume'],
                    orderbook_imbalance=row['orderbook_imbalance'],
                    timestamp=timestamp.timestamp()
                )
                
                # Generate signals
                signals = signal_generator.generate_signals()
                
                # Process signals with strategies
                for signal in signals:
                    self._process_signal(signal, strategies, risk_manager, row, timestamp, symbol)
                
                # Update existing positions
                self._update_positions(row, strategies, timestamp)
                
                # Update equity curve
                self._update_equity_curve(timestamp)
                
                # Risk management checks
                if risk_manager.portfolio_risk.kill_switch_active:
                    logger.warning("Kill switch activated during backtest")
                    self._close_all_positions(row['close'], timestamp, "Kill Switch")
                
                # Progress logging
                if i % 1000 == 0:
                    progress = (i / len(data)) * 100
                    logger.info(f"Backtest progress: {progress:.1f}%")
                
            except Exception as e:
                logger.error(f"Error in simulation step {i}: {e}")
                continue
        
        # Close any remaining positions at the end
        if self.positions:
            self._close_all_positions(data.iloc[-1]['close'], data.index[-1], "End of Backtest")
    
    def _process_signal(self, signal: Signal, strategies, risk_manager, row, timestamp, symbol: str):
        """Process a trading signal"""
        try:
            # Find best strategy for this signal
            best_strategy = None
            for strategy in strategies:
                if strategy.should_enter(signal):
                    best_strategy = strategy
                    break
            
            if not best_strategy:
                return
            
            # Check risk management
            can_trade, position_size, risk_reason = risk_manager.evaluate_trade_risk(
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                side='long' if 'long' in signal.signal_type.value else 'short',
                available_capital=self.current_capital,
                signal_strength=signal.strength,
                open_positions=self.positions
            )
            
            if not can_trade:
                return
            
            # Calculate actual position size
            position_size = best_strategy.calculate_position_size(signal, self.current_capital)
            position_size = min(position_size, position_size)  # Use smaller of the two
            
            if position_size <= 0:
                return
            
            # Enter position
            self._enter_position(signal, best_strategy, position_size, row, timestamp, symbol)
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    def _enter_position(self, signal: Signal, strategy, size: float, row, timestamp, symbol: str):
        """Enter a new position"""
        try:
            # Create position
            side = PositionSide.LONG if 'long' in signal.signal_type.value else PositionSide.SHORT
            
            position = strategy.enter_position(symbol, signal, size)
            if not position:
                return
            
            # Calculate commission
            entry_cost = size * signal.entry_price
            commission = entry_cost * self.commission_rate
            
            # Update capital
            self.current_capital -= commission
            
            # Store position in backtest tracking
            position_id = f"{position.symbol}_{timestamp.timestamp()}"
            self.positions[position_id] = {
                'position': position,
                'strategy': strategy,
                'entry_commission': commission
            }
            
            logger.debug(f"Entered position: {position.symbol} {side.value} {size} @ ${signal.entry_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error entering position: {e}")
    
    def _update_positions(self, row, strategies, timestamp):
        """Update all open positions"""
        positions_to_close = []
        
        for pos_id, pos_data in self.positions.items():
            position = pos_data['position']
            strategy = pos_data['strategy']
            
            # Update position with current price (pass simulation timestamp)
            try:
                sim_ts = timestamp.timestamp()
            except Exception:
                sim_ts = None
            position.update_price(row['close'], sim_ts)
            
            # Check exit conditions
            should_exit, exit_reason = strategy.should_exit(position, row['close'])
            
            if should_exit:
                positions_to_close.append((pos_id, row['close'], exit_reason, timestamp))
        
        # Close positions that meet exit criteria
        for pos_id, exit_price, exit_reason, exit_time in positions_to_close:
            # convert exit_time to numeric epoch if it's a pandas Timestamp
            if hasattr(exit_time, 'timestamp'):
                exit_ts = exit_time.timestamp()
            else:
                exit_ts = exit_time
            self._close_position(pos_id, exit_price, exit_reason, exit_ts)
    
    def _close_position(self, position_id: str, exit_price: float, exit_reason: str, timestamp):
        """Close a position"""
        try:
            if position_id not in self.positions:
                return
            
            pos_data = self.positions[position_id]
            position = pos_data['position']
            strategy = pos_data['strategy']
            entry_commission = pos_data['entry_commission']
            
            # Close position in strategy, pass simulation timestamp
            closed_position = strategy.exit_position(position.symbol, exit_price, exit_reason, timestamp)
            if not closed_position:
                return
            
            # Calculate commission on exit
            exit_value = position.size * exit_price
            exit_commission = exit_value * self.commission_rate
            
            # Total commission
            total_commission = entry_commission + exit_commission
            
            # Net PnL after commissions
            gross_pnl = closed_position.pnl
            net_pnl = gross_pnl - total_commission
            
            # Update capital
            self.current_capital += net_pnl
            
            # Record trade
            trade_record = {
                'entry_time': datetime.fromtimestamp(position.entry_time),
                'exit_time': datetime.fromtimestamp(timestamp) if isinstance(timestamp, (int, float)) else timestamp,
                'symbol': position.symbol,
                'side': position.side.value,
                'size': position.size,
                'entry_price': position.entry_price,
                'exit_price': exit_price,
                'gross_pnl': gross_pnl,
                'commission': total_commission,
                'net_pnl': net_pnl,
                'exit_reason': exit_reason,
                'strategy': position.strategy,
                'duration_seconds': position.get_duration(),
                'signal_strength': position.signal_strength
            }
            
            self.trades.append(trade_record)
            
            # Remove from open positions
            del self.positions[position_id]
            
            logger.debug(f"Closed position: {position.symbol} {position.side.value} "
                        f"PnL: ${net_pnl:.2f} Reason: {exit_reason}")
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
    
    def _close_all_positions(self, price: float, timestamp, reason: str):
        """Close all open positions"""
        position_ids = list(self.positions.keys())
        for pos_id in position_ids:
            self._close_position(pos_id, price, reason, timestamp)
    
    def _update_equity_curve(self, timestamp):
        """Update equity curve with current portfolio value"""
        # Calculate unrealized PnL from open positions
        unrealized_pnl = 0
        for pos_data in self.positions.values():
            position = pos_data['position']
            unrealized_pnl += position.get_unrealized_pnl()
        
        current_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append(current_equity)
        self.timestamps.append(timestamp)
        
        # Update drawdown tracking
        self.peak_capital = max(self.peak_capital, current_equity)
        current_drawdown = (current_equity - self.peak_capital) / self.peak_capital
        self.max_drawdown = min(self.max_drawdown, current_drawdown)
    
    def _calculate_results(self, symbol: str, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Calculate comprehensive backtest results"""
        
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Trading metrics
        total_trades = len(self.trades)
        if total_trades > 0:
            winning_trades = len([t for t in self.trades if t['net_pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades) * 100
            
            wins = [t['net_pnl'] for t in self.trades if t['net_pnl'] > 0]
            losses = [t['net_pnl'] for t in self.trades if t['net_pnl'] < 0]
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = abs(np.mean(losses)) if losses else 0
            profit_factor = (sum(wins) / abs(sum(losses))) if losses else float('inf')
        else:
            winning_trades = losing_trades = 0
            win_rate = avg_win = avg_loss = profit_factor = 0
        
        # Risk metrics
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252 * 24 * 60)  # Annualized (1-minute data)
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252 * 24 * 60) if returns.std() > 0 else 0
            var_95 = np.percentile(returns, 5)
            calmar_ratio = (total_return_pct / 100) / abs(self.max_drawdown) if self.max_drawdown != 0 else 0
        else:
            volatility = sharpe_ratio = var_95 = calmar_ratio = 0
        
        return BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=self.max_drawdown * 100,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            volatility=volatility,
            var_95=var_95,
            calmar_ratio=calmar_ratio,
            trades=self.trades,
            equity_curve=self.equity_curve,
            timestamps=self.timestamps
        )

class BacktestAnalyzer:
    """
    Analyze backtest results and generate reports
    """
    
    @staticmethod
    def print_summary(result: BacktestResult):
        """Print backtest summary"""
        print("\n" + "="*50)
        print(f"BACKTEST SUMMARY - {result.symbol}")
        print("="*50)
        print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: ${result.initial_capital:,.2f}")
        print(f"Final Capital: ${result.final_capital:,.2f}")
        print(f"Total Return: ${result.total_return:,.2f} ({result.total_return_pct:.2f}%)")
        print(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Calmar Ratio: {result.calmar_ratio:.2f}")
        print()
        print("TRADING METRICS:")
        print(f"Total Trades: {result.total_trades}")
        print(f"Winning Trades: {result.winning_trades}")
        print(f"Losing Trades: {result.losing_trades}")
        print(f"Win Rate: {result.win_rate:.2f}%")
        print(f"Average Win: ${result.avg_win:.2f}")
        print(f"Average Loss: ${result.avg_loss:.2f}")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print("="*50)
    
    @staticmethod
    def plot_results(result: BacktestResult, save_path: str = None):
        """Plot backtest results"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # Ensure timestamps and equity curve have same length
            min_length = min(len(result.timestamps), len(result.equity_curve))
            timestamps = result.timestamps[:min_length]
            equity_curve = result.equity_curve[:min_length]
            
            # Equity curve
            ax1.plot(timestamps, equity_curve, linewidth=2, color='blue')
            ax1.set_title('Equity Curve')
            ax1.set_ylabel('Portfolio Value ($)')
            ax1.grid(True, alpha=0.3)
            
            # Drawdown
            equity_series = pd.Series(equity_curve, index=timestamps)
            peak_series = equity_series.expanding().max()
            drawdown_series = (equity_series - peak_series) / peak_series * 100
            
            ax2.fill_between(drawdown_series.index, drawdown_series.values, 0, 
                           color='red', alpha=0.7)
            ax2.set_title('Drawdown')
            ax2.set_ylabel('Drawdown (%)')
            ax2.grid(True, alpha=0.3)
            
            # Trade PnL distribution
            if result.trades:
                pnls = [trade['net_pnl'] for trade in result.trades]
                ax3.hist(pnls, bins=30, alpha=0.7, edgecolor='black')
                ax3.axvline(x=0, color='red', linestyle='--', alpha=0.8)
                ax3.set_title('Trade PnL Distribution')
                ax3.set_xlabel('PnL ($)')
                ax3.set_ylabel('Frequency')
                ax3.grid(True, alpha=0.3)
            
            # Monthly returns heatmap
            if len(timestamps) > 30:
                try:
                    monthly_returns = equity_series.resample('ME').last().pct_change().dropna() * 100
                    if len(monthly_returns) > 0:
                        monthly_returns_matrix = monthly_returns.values.reshape(-1, 1)
                        
                        sns.heatmap(monthly_returns_matrix.T, annot=True, fmt='.1f', 
                                   cmap='RdYlGn', center=0, ax=ax4)
                        ax4.set_title('Monthly Returns (%)')
                        ax4.set_xlabel('Month')
                        ax4.set_ylabel('')
                    else:
                        ax4.text(0.5, 0.5, 'No Monthly Data', ha='center', va='center', transform=ax4.transAxes)
                        ax4.set_title('Monthly Returns (%)')
                except Exception as e:
                    ax4.text(0.5, 0.5, f'Plotting Error: {str(e)[:50]}', ha='center', va='center', transform=ax4.transAxes)
                    ax4.set_title('Monthly Returns (%)')
            else:
                ax4.text(0.5, 0.5, 'Not Enough Data\nfor Monthly View', ha='center', va='center', transform=ax4.transAxes)
                ax4.set_title('Monthly Returns (%)')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Plot saved to {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting results: {e}")

# Example usage and configuration
def run_example_backtest():
    """Run example backtest"""
    
    # Configuration
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 2, 1)
    symbol = "BTCUSDT"
    initial_capital = 10000
    
    # Strategy configurations
    strategy_configs = {
        'mean_reversion': {
            'min_signal_strength': 0.6,
            'risk_per_trade': 0.01,
            'max_holding_time': 60,
            'profit_target_ratio': 0.5
        },
        'breakout': {
            'min_signal_strength': 0.7,
            'risk_per_trade': 0.01,
            'trailing_stop_distance': 0.5,
            'profit_target_multiple': 2.0,
            'max_holding_time': 15
        }
    }
    
    # Signal configuration
    signal_config = {
        'window_size': 60,
        'mean_reversion_threshold': 2.0,
        'breakout_threshold': 1.5,
        'volume_spike_threshold': 2.0,
        'ob_imbalance_threshold': 0.3,
        'min_signal_interval': 5
    }
    
    # Risk configuration
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
    
    # Run backtest
    backtester = BacktestEngine(initial_capital)
    result = backtester.run_backtest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        strategy_configs=strategy_configs,
        signal_config=signal_config,
        risk_config=risk_config,
        interval="1"  # 1-minute data
    )
    
    if result:
        # Print results
        BacktestAnalyzer.print_summary(result)
        
        # Plot results
        BacktestAnalyzer.plot_results(result, f"backtest_{symbol}_{start_date.strftime('%Y%m%d')}.png")
        
        return result
    else:
        print("Backtest failed")
        return None

if __name__ == "__main__":
    print("AI Scalping Bot Backtester")
    print("=" * 30)
    
    # Run example backtest
    result = run_example_backtest()
    
    if result:
        print(f"\nBacktest completed successfully!")
        print(f"Check the generated plot for visual analysis.")
