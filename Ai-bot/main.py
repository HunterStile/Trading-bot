"""
Main entry point for the AI Scalping Bot
Provides command-line interface and orchestrates bot startup
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import bot components
from engine import TradingEngine, BotConfig
from config import (
    create_config_from_preset, 
    load_config_from_file, 
    save_config_to_file,
    validate_config,
    get_production_config,
    get_development_config
)
from backtester import BacktestEngine, BacktestAnalyzer

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def create_bot_config_from_dict(config_dict: dict) -> BotConfig:
    """Convert configuration dictionary to BotConfig"""
    trading_config = config_dict.get('trading')
    signal_config = config_dict.get('signal')
    strategy_config = config_dict.get('strategy')
    risk_config = config_dict.get('risk')
    execution_config = config_dict.get('execution')
    
    # Convert strategy config to expected format
    strategy_dict = {}
    if strategy_config:
        strategy_dict['mean_reversion'] = {
            'min_signal_strength': strategy_config.mean_reversion_min_signal_strength,
            'risk_per_trade': strategy_config.mean_reversion_risk_per_trade,
            'max_holding_time': strategy_config.mean_reversion_max_holding_time,
            'profit_target_ratio': strategy_config.mean_reversion_profit_target_ratio
        }
        strategy_dict['breakout'] = {
            'min_signal_strength': strategy_config.breakout_min_signal_strength,
            'risk_per_trade': strategy_config.breakout_risk_per_trade,
            'trailing_stop_distance': strategy_config.breakout_trailing_stop_distance,
            'profit_target_multiple': strategy_config.breakout_profit_target_multiple,
            'max_holding_time': strategy_config.breakout_max_holding_time
        }
    
    # Convert risk config to expected format
    risk_dict = {}
    if risk_config:
        risk_dict['position_risk'] = {
            'risk_per_trade': risk_config.default_risk_per_trade,
            'max_risk_per_trade': risk_config.max_risk_per_trade,
            'max_position_size': risk_config.max_position_size,
            'min_stop_distance': risk_config.min_stop_distance,
            'max_stop_distance': risk_config.max_stop_distance,
            'max_leverage': risk_config.max_leverage
        }
        risk_dict['portfolio_risk'] = {
            'max_daily_loss': risk_config.max_daily_loss,
            'max_total_exposure': risk_config.max_total_exposure,
            'max_drawdown': risk_config.max_drawdown,
            'max_consecutive_losses': risk_config.max_consecutive_losses,
            'max_positions': strategy_config.max_concurrent_positions if strategy_config else 5
        }
    
    # Convert signal config to dict format
    signal_dict = {}
    if signal_config:
        signal_dict = {
            'window_size': signal_config.window_size,
            'mean_reversion_threshold': signal_config.mean_reversion_threshold,
            'breakout_threshold': signal_config.breakout_threshold,
            'volume_spike_threshold': signal_config.volume_spike_threshold,
            'ob_imbalance_threshold': signal_config.ob_imbalance_threshold,
            'min_signal_interval': signal_config.min_signal_interval
        }
    
    return BotConfig(
        symbols=trading_config.symbols if trading_config else ["BTCUSDT"],
        initial_capital=trading_config.initial_capital if trading_config else 10000.0,
        is_testnet=trading_config.use_testnet if trading_config else True,
        data_update_interval=trading_config.data_update_interval if trading_config else 1.0,
        signal_config=signal_dict,
        strategy_config=strategy_dict,
        risk_config=risk_dict,
        log_trades=trading_config.log_trades if trading_config else True,
        trade_log_file=trading_config.trade_log_file if trading_config else "ai_scalping_trades.csv"
    )

async def run_live_trading(config_dict: dict):
    """Run live trading bot"""
    print("🚀 Starting AI Scalping Bot - Live Trading Mode")
    print("=" * 50)
    
    # Create bot configuration
    bot_config = create_bot_config_from_dict(config_dict)
    
    # Setup logging
    trading_config = config_dict.get('trading')
    log_level = trading_config.log_level if trading_config else "INFO"
    setup_logging(log_level, f"ai_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Show configuration summary
    print(f"Trading Symbols: {bot_config.symbols}")
    print(f"Initial Capital: ${bot_config.initial_capital:,.2f}")
    print(f"Environment: {'TESTNET' if bot_config.is_testnet else 'LIVE'}")
    print(f"Log Level: {log_level}")
    print("-" * 50)
    
    # Confirm live trading
    if not bot_config.is_testnet:
        confirm = input("⚠️  LIVE TRADING MODE! Are you sure? (type 'yes' to continue): ")
        if confirm.lower() != 'yes':
            print("Trading cancelled.")
            return
    
    try:
        # Create and start trading engine
        engine = TradingEngine(bot_config)
        await engine.start()
        
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logging.error(f"Bot error: {e}", exc_info=True)

async def run_backtest(config_dict: dict, start_date: str, end_date: str, 
                      symbol: str, save_results: bool = True):
    """Run backtesting"""
    print("📊 Starting AI Scalping Bot - Backtest Mode")
    print("=" * 50)
    
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        print(f"Symbol: {symbol}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Duration: {(end_dt - start_dt).days} days")
        print("-" * 50)
        
        # Extract configurations
        trading_config = config_dict.get('trading')
        signal_config = config_dict.get('signal')
        strategy_config = config_dict.get('strategy')
        risk_config = config_dict.get('risk')
        
        # Convert to backtest format
        strategy_configs = {}
        if strategy_config:
            strategy_configs['mean_reversion'] = {
                'min_signal_strength': strategy_config.mean_reversion_min_signal_strength,
                'risk_per_trade': strategy_config.mean_reversion_risk_per_trade,
                'max_holding_time': strategy_config.mean_reversion_max_holding_time,
                'profit_target_ratio': strategy_config.mean_reversion_profit_target_ratio
            }
            strategy_configs['breakout'] = {
                'min_signal_strength': strategy_config.breakout_min_signal_strength,
                'risk_per_trade': strategy_config.breakout_risk_per_trade,
                'trailing_stop_distance': strategy_config.breakout_trailing_stop_distance,
                'profit_target_multiple': strategy_config.breakout_profit_target_multiple,
                'max_holding_time': strategy_config.breakout_max_holding_time
            }
        
        signal_dict = {}
        if signal_config:
            signal_dict = {
                'window_size': signal_config.window_size,
                'mean_reversion_threshold': signal_config.mean_reversion_threshold,
                'breakout_threshold': signal_config.breakout_threshold,
                'volume_spike_threshold': signal_config.volume_spike_threshold,
                'ob_imbalance_threshold': signal_config.ob_imbalance_threshold,
                'min_signal_interval': signal_config.min_signal_interval
            }
        
        risk_dict = {}
        if risk_config:
            risk_dict = {
                'position_risk': {
                    'risk_per_trade': risk_config.default_risk_per_trade,
                    'max_risk_per_trade': risk_config.max_risk_per_trade,
                    'max_position_size': risk_config.max_position_size,
                    'min_stop_distance': risk_config.min_stop_distance,
                    'max_stop_distance': risk_config.max_stop_distance,
                    'max_leverage': risk_config.max_leverage
                },
                'portfolio_risk': {
                    'max_daily_loss': risk_config.max_daily_loss,
                    'max_total_exposure': risk_config.max_total_exposure,
                    'max_drawdown': risk_config.max_drawdown,
                    'max_consecutive_losses': risk_config.max_consecutive_losses,
                    'max_positions': strategy_config.max_concurrent_positions if strategy_config else 5
                }
            }
        
        # Run backtest
        initial_capital = trading_config.initial_capital if trading_config else 10000.0
        backtester = BacktestEngine(initial_capital)
        
        result = backtester.run_backtest(
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            strategy_configs=strategy_configs,
            signal_config=signal_dict,
            risk_config=risk_dict,
            interval="1"
        )
        
        if result:
            # Print results
            BacktestAnalyzer.print_summary(result)
            
            # Save results if requested
            if save_results:
                # Create results directory
                results_dir = Path("backtest_results")
                results_dir.mkdir(exist_ok=True)
                
                # Generate plot
                plot_path = results_dir / f"backtest_{symbol}_{start_date}_{end_date}.png"
                BacktestAnalyzer.plot_results(result, str(plot_path))
                
                # Save trade details to CSV
                if result.trades:
                    import pandas as pd
                    trades_df = pd.DataFrame(result.trades)
                    csv_path = results_dir / f"trades_{symbol}_{start_date}_{end_date}.csv"
                    trades_df.to_csv(csv_path, index=False)
                    print(f"💾 Trade details saved to {csv_path}")
            
            return result
        else:
            print("❌ Backtest failed")
            return None
            
    except Exception as e:
        print(f"❌ Backtest error: {e}")
        logging.error(f"Backtest error: {e}", exc_info=True)
        return None

def print_banner():
    """Print bot banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    AI SCALPING BOT                           ║
    ║              Bybit USDT Perpetual Futures                    ║
    ║                                                              ║
    ║  🤖 Automated scalping with AI-powered signals              ║
    ║  ⚡ High-frequency mean reversion & breakout strategies      ║
    ║  🛡️  Advanced risk management & kill switches               ║
    ║  📊 Real-time monitoring & trade logging                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Scalping Bot for Bybit USDT Perpetual Futures')
    
    # Mode selection
    parser.add_argument('mode', choices=['trade', 'backtest', 'config'], 
                       help='Bot operation mode')
    
    # Configuration
    parser.add_argument('--config', '-c', type=str, default=None,
                       help='Configuration file path (JSON)')
    parser.add_argument('--preset', '-p', type=str, default='default',
                       choices=['default', 'conservative', 'aggressive'],
                       help='Configuration preset')
    
    # Live trading options
    parser.add_argument('--testnet', action='store_true',
                       help='Use testnet for live trading')
    parser.add_argument('--live', action='store_true',
                       help='Enable live trading (use with caution)')
    
    # Backtesting options
    parser.add_argument('--symbol', '-s', type=str, default='BTCUSDT',
                       help='Symbol for backtesting')
    parser.add_argument('--start-date', type=str, default='2024-01-01',
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2024-02-01',
                       help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--no-save', action='store_true',
                       help='Don\'t save backtest results')
    
    # Configuration generation
    parser.add_argument('--output', '-o', type=str, default='ai_bot_config.json',
                       help='Output file for config generation')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    try:
        # Load or create configuration
        if args.config:
            print(f"📄 Loading configuration from {args.config}")
            config_dict = load_config_from_file(args.config)
        else:
            print(f"⚙️  Using {args.preset} preset configuration")
            config_dict = create_config_from_preset(args.preset)
        
        # Validate configuration
        issues = validate_config(config_dict)
        if issues:
            print("⚠️  Configuration validation issues:")
            for issue in issues:
                print(f"   - {issue}")
            
            if args.mode in ['trade', 'backtest']:
                confirm = input("Continue anyway? (y/n): ")
                if confirm.lower() != 'y':
                    return
        
        # Override testnet setting if specified
        if args.testnet or (args.mode == 'trade' and not args.live):
            if 'trading' in config_dict:
                config_dict['trading'].use_testnet = True
        elif args.live and args.mode == 'trade':
            if 'trading' in config_dict:
                config_dict['trading'].use_testnet = False
        
        # Execute based on mode
        if args.mode == 'trade':
            asyncio.run(run_live_trading(config_dict))
            
        elif args.mode == 'backtest':
            asyncio.run(run_backtest(
                config_dict, 
                args.start_date, 
                args.end_date, 
                args.symbol,
                not args.no_save
            ))
            
        elif args.mode == 'config':
            print(f"💾 Saving configuration to {args.output}")
            save_config_to_file(config_dict, args.output)
            print("✅ Configuration saved successfully")
            
            # Show configuration summary
            trading_config = config_dict.get('trading')
            if trading_config:
                print(f"\nConfiguration Summary:")
                print(f"  Symbols: {trading_config.symbols}")
                print(f"  Initial Capital: ${trading_config.initial_capital:,.2f}")
                print(f"  Environment: {'Testnet' if trading_config.use_testnet else 'Live'}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
