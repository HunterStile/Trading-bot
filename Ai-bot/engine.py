"""
Trading Engine - Main orchestrator for the AI scalping bot
Coordinates all components: data feed, signals, strategies, risk management, and execution
"""

import asyncio
import time
import logging
import signal
import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import threading
from queue import Queue

# Import local modules
from data_feed import MarketDataManager
from signals import MultiSymbolSignalManager, Signal
from strategy import StrategyManager, MeanReversionStrategy, BreakoutStrategy
from risk import RiskManager
from execution import ExecutionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_scalping_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BotConfig:
    """Configuration for the AI scalping bot"""
    # Trading parameters
    symbols: List[str]
    initial_capital: float
    is_testnet: bool = False
    
    # Data feed settings
    data_update_interval: float = 1.0  # seconds
    
    # Signal generation settings
    signal_config: Dict = None
    
    # Strategy settings
    strategy_config: Dict = None
    
    # Risk management settings
    risk_config: Dict = None
    
    # Execution settings
    execution_config: Dict = None
    
    # Logging settings
    log_trades: bool = True
    trade_log_file: str = "trades.csv"
    
    def __post_init__(self):
        """Set default configurations if not provided"""
        if self.signal_config is None:
            self.signal_config = {
                'window_size': 60,
                'mean_reversion_threshold': 2.0,
                'breakout_threshold': 1.5,
                'volume_spike_threshold': 2.0,
                'ob_imbalance_threshold': 0.3,
                'min_signal_interval': 5
            }
        
        if self.strategy_config is None:
            self.strategy_config = {
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
        
        if self.risk_config is None:
            self.risk_config = {
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

class TradingEngine:
    """
    Main trading engine that orchestrates all components
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.running = False
        self.current_capital = config.initial_capital
        
        # Initialize components
        self.data_manager = None
        self.signal_manager = None
        self.strategy_manager = None
        self.risk_manager = None
        self.execution_manager = None
        
        # Performance tracking
        self.start_time = None
        self.trade_count = 0
        self.total_pnl = 0.0
        
        # Trade logging
        self.trade_logger = TradeLogger(config.trade_log_file) if config.log_trades else None
        
        # Status monitoring
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds
        
        # Shutdown handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def initialize(self):
        """Initialize all trading components"""
        try:
            logger.info("Initializing AI Scalping Bot...")
            
            # Initialize market data manager
            self.data_manager = MarketDataManager(
                symbols=self.config.symbols,
                is_testnet=self.config.is_testnet
            )
            
            # Initialize signal manager
            self.signal_manager = MultiSymbolSignalManager(
                symbols=self.config.symbols,
                config=self.config.signal_config
            )
            
            # Initialize strategies
            mean_rev_strategy = MeanReversionStrategy(self.config.strategy_config['mean_reversion'])
            breakout_strategy = BreakoutStrategy(self.config.strategy_config['breakout'])
            self.strategy_manager = StrategyManager([mean_rev_strategy, breakout_strategy])
            
            # Initialize risk manager
            self.risk_manager = RiskManager(self.config.risk_config)
            self.risk_manager.update_portfolio(self.current_capital)
            
            # Initialize execution manager
            self.execution_manager = ExecutionManager(
                symbols=self.config.symbols,
                is_testnet=self.config.is_testnet
            )
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trading engine: {e}")
            return False
    
    async def start(self):
        """Start the trading engine"""
        if not await self.initialize():
            logger.error("Failed to initialize, exiting")
            return
        
        logger.info("Starting AI Scalping Bot...")
        self.running = True
        self.start_time = time.time()
        
        # Start market data feed
        data_task = asyncio.create_task(self.data_manager.start())
        
        # Start main trading loop
        trading_task = asyncio.create_task(self._trading_loop())
        
        # Start monitoring task
        monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        try:
            # Run until stopped
            await asyncio.gather(data_task, trading_task, monitoring_task)
        except asyncio.CancelledError:
            logger.info("Trading engine stopped")
        except Exception as e:
            logger.error(f"Error in trading engine: {e}")
        finally:
            await self.shutdown()
    
    async def _trading_loop(self):
        """Main trading logic loop"""
        logger.info("Starting trading loop...")
        
        while self.running:
            try:
                start_loop_time = time.time()
                
                # Update market data and generate signals
                market_prices = {}
                market_volumes = {}
                orderbook_imbalances = {}
                
                for symbol in self.config.symbols:
                    # Get current market data
                    ticker = self.data_manager.get_ticker(symbol)
                    if ticker:
                        price = ticker['last_price']
                        market_prices[symbol] = price
                        
                        # Get volume data
                        volume_profile = self.data_manager.get_volume_profile(symbol, 60)
                        market_volumes[symbol] = volume_profile.get('total_volume', 0)
                        
                        # Get orderbook imbalance
                        ob_imbalance = self.data_manager.get_orderbook_imbalance(symbol)
                        orderbook_imbalances[symbol] = ob_imbalance or 0
                        
                        # Update signal generator
                        self.signal_manager.update_market_data(
                            symbol, price, market_volumes[symbol], 
                            orderbook_imbalances[symbol]
                        )
                
                # Generate signals
                all_signals = self.signal_manager.get_all_signals()
                
                # Process signals with strategies
                if all_signals:
                    new_positions = self.strategy_manager.process_signals(
                        all_signals, self.current_capital
                    )
                    
                    # Execute new positions
                    for symbol, strategy_name, position in new_positions:
                        await self._execute_position_entry(symbol, position)
                
                # Update existing positions
                self.strategy_manager.update_all_positions(market_prices)
                
                # Check for position exits
                open_positions = self.strategy_manager.get_open_positions()
                for strategy_name, positions in open_positions.items():
                    for position in positions:
                        if position.status.value == 'closed':
                            await self._execute_position_exit(position)
                
                # Check risk management
                force_close, reason = self.risk_manager.force_close_recommended()
                if force_close:
                    logger.warning(f"Force closing all positions: {reason}")
                    await self._emergency_close_all()
                
                # Update performance metrics
                await self._update_performance()
                
                # Control loop timing
                loop_time = time.time() - start_loop_time
                if loop_time < self.config.data_update_interval:
                    await asyncio.sleep(self.config.data_update_interval - loop_time)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(1)
    
    async def _execute_position_entry(self, symbol: str, position):
        """Execute position entry"""
        try:
            # Check risk before execution
            can_trade, pos_size, risk_reason = self.risk_manager.evaluate_trade_risk(
                entry_price=position.entry_price,
                stop_loss=position.stop_loss,
                side=position.side.value,
                available_capital=self.current_capital,
                signal_strength=position.signal_strength
            )
            
            if not can_trade:
                logger.warning(f"Trade rejected by risk management: {risk_reason}")
                return
            
            # Execute the position
            success, order = self.execution_manager.enter_position(
                symbol=symbol,
                side=position.side.value,
                size=pos_size
            )
            
            if success and order:
                logger.info(f"Position opened: {symbol} {position.side.value} {pos_size}")
                
                # Log trade
                if self.trade_logger:
                    self.trade_logger.log_trade_entry(
                        symbol=symbol,
                        side=position.side.value,
                        size=pos_size,
                        entry_price=order.avg_fill_price or position.entry_price,
                        strategy=position.strategy,
                        signal_strength=position.signal_strength
                    )
                
                self.trade_count += 1
            else:
                logger.error(f"Failed to open position: {symbol} {position.side.value}")
                
        except Exception as e:
            logger.error(f"Error executing position entry: {e}")
    
    async def _execute_position_exit(self, position):
        """Execute position exit"""
        try:
            success, order = self.execution_manager.exit_position(
                symbol=position.symbol,
                size=position.size
            )
            
            if success and order:
                # Calculate PnL
                pnl = position.pnl
                self.total_pnl += pnl
                
                logger.info(f"Position closed: {position.symbol} PnL: ${pnl:.2f}")
                
                # Update risk management
                self.risk_manager.update_portfolio(self.current_capital, pnl)
                
                # Log trade
                if self.trade_logger:
                    self.trade_logger.log_trade_exit(
                        symbol=position.symbol,
                        exit_price=order.avg_fill_price or position.current_price,
                        pnl=pnl,
                        exit_reason=position.exit_reason,
                        duration=position.get_duration()
                    )
            else:
                logger.error(f"Failed to close position: {position.symbol}")
                
        except Exception as e:
            logger.error(f"Error executing position exit: {e}")
    
    async def _emergency_close_all(self):
        """Emergency close all positions"""
        try:
            results = self.execution_manager.emergency_close_all()
            logger.warning(f"Emergency close results: {results}")
            
            # Force close in strategy manager
            market_data = {}
            for symbol in self.config.symbols:
                ticker = self.data_manager.get_ticker(symbol)
                if ticker:
                    market_data[symbol] = ticker['last_price']
            
            self.strategy_manager.force_close_all_positions(market_data, "Emergency Close")
            
        except Exception as e:
            logger.error(f"Error in emergency close: {e}")
    
    async def _update_performance(self):
        """Update performance metrics"""
        try:
            # Get current portfolio value (simplified)
            self.current_capital = self.config.initial_capital + self.total_pnl
            
            # Update risk manager
            self.risk_manager.update_portfolio(self.current_capital)
            
        except Exception as e:
            logger.error(f"Error updating performance: {e}")
    
    async def _monitoring_loop(self):
        """Monitoring and heartbeat loop"""
        while self.running:
            try:
                current_time = time.time()
                
                # Heartbeat
                if current_time - self.last_heartbeat >= self.heartbeat_interval:
                    await self._send_heartbeat()
                    self.last_heartbeat = current_time
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self):
        """Send system status heartbeat"""
        try:
            uptime = time.time() - self.start_time if self.start_time else 0
            
            # Get system status
            risk_summary = self.risk_manager.get_risk_summary()
            portfolio_summary = self.strategy_manager.get_portfolio_summary()
            execution_summary = self.execution_manager.get_execution_summary()
            
            heartbeat_data = {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': uptime,
                'current_capital': self.current_capital,
                'total_pnl': self.total_pnl,
                'trade_count': self.trade_count,
                'risk_level': risk_summary.get('risk_level', 'unknown'),
                'open_positions': portfolio_summary.get('total_open_positions', 0),
                'kill_switch_active': risk_summary.get('kill_switch_active', False)
            }
            
            logger.info(f"Heartbeat: {json.dumps(heartbeat_data, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def shutdown(self):
        """Shutdown all components gracefully"""
        logger.info("Shutting down trading engine...")
        
        try:
            # Stop trading
            self.running = False
            
            # Close all positions
            await self._emergency_close_all()
            
            # Stop data feed
            if self.data_manager:
                await self.data_manager.stop()
            
            # Stop execution manager
            if self.execution_manager:
                self.execution_manager.shutdown()
            
            # Final status report
            await self._send_heartbeat()
            
            logger.info("Trading engine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

class TradeLogger:
    """
    Trade logging functionality
    Logs all trades to CSV for analysis
    """
    
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_header()
    
    def _ensure_header(self):
        """Ensure CSV header exists"""
        try:
            with open(self.filename, 'r') as f:
                pass  # File exists
        except FileNotFoundError:
            # Create file with header
            header = "timestamp,symbol,side,size,entry_price,exit_price,pnl,strategy,signal_strength,exit_reason,duration_seconds\n"
            with open(self.filename, 'w') as f:
                f.write(header)
    
    def log_trade_entry(self, symbol: str, side: str, size: float, entry_price: float,
                       strategy: str, signal_strength: float):
        """Log trade entry"""
        # Store entry data for later completion
        self.pending_entry = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'strategy': strategy,
            'signal_strength': signal_strength
        }
    
    def log_trade_exit(self, symbol: str, exit_price: float, pnl: float,
                      exit_reason: str, duration: float):
        """Log completed trade"""
        try:
            if hasattr(self, 'pending_entry') and self.pending_entry['symbol'] == symbol:
                entry = self.pending_entry
                
                trade_data = [
                    entry['timestamp'],
                    entry['symbol'],
                    entry['side'],
                    entry['size'],
                    entry['entry_price'],
                    exit_price,
                    pnl,
                    entry['strategy'],
                    entry['signal_strength'],
                    exit_reason,
                    duration
                ]
                
                with open(self.filename, 'a') as f:
                    f.write(','.join(map(str, trade_data)) + '\n')
                
                # Clear pending entry
                del self.pending_entry
                
        except Exception as e:
            logger.error(f"Error logging trade: {e}")

# Example configuration and main function
def create_default_config() -> BotConfig:
    """Create default bot configuration"""
    return BotConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        initial_capital=10000.0,
        is_testnet=True,  # Use testnet for safety
        data_update_interval=1.0,
        log_trades=True,
        trade_log_file="ai_scalping_trades.csv"
    )

async def main():
    """Main function to run the AI scalping bot"""
    try:
        # Create configuration
        config = create_default_config()
        
        # Create and start trading engine
        engine = TradingEngine(config)
        await engine.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    print("AI Scalping Bot for Bybit USDT Perpetual Futures")
    print("=" * 50)
    print("Starting bot...")
    
    # Run the bot
    asyncio.run(main())
