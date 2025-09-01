"""
Execution Module - Order execution and management for Bybit
Handles order placement, cancellation, and position management using existing API functions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_functions import *
from config import *
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from pybit.unified_trading import HTTP
import threading
from queue import Queue
import numpy as np

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP_MARKET = "StopMarket"
    TAKE_PROFIT_MARKET = "TakeProfitMarket"

class OrderSide(Enum):
    BUY = "Buy"
    SELL = "Sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class Order:
    """Order data structure"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False
    
    # Order tracking
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0
    avg_fill_price: Optional[float] = None
    created_time: Optional[float] = None
    updated_time: Optional[float] = None
    
    # Execution metadata
    slippage: Optional[float] = None
    execution_time: Optional[float] = None

class BybitExecutor:
    """
    Order execution engine for Bybit USDT Perpetual Futures
    Uses existing trading_functions.py for API calls
    """
    
    def __init__(self, is_testnet: bool = False):
        self.is_testnet = is_testnet
        self.session = HTTP(
            testnet=is_testnet,
            api_key=api,
            api_secret=api_sec,
        )
        
        # Order tracking
        self.open_orders = {}  # order_id -> Order
        self.order_history = []
        
        # Execution monitoring
        self.execution_queue = Queue()
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Slippage tracking
        self.slippage_history = []
        self.max_acceptable_slippage = 0.002  # 0.2%
        
        # Rate limiting
        self.last_order_time = 0
        self.min_order_interval = 0.1  # 100ms between orders
        
    def start_monitoring(self):
        """Start order monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitor_orders, daemon=True)
            self.monitoring_thread.start()
            logger.info("Order monitoring started")
    
    def stop_monitoring(self):
        """Stop order monitoring thread"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Order monitoring stopped")
    
    def place_market_order(self, symbol: str, side: OrderSide, qty: float, 
                          reduce_only: bool = False) -> Optional[Order]:
        """
        Place market order using existing API functions
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: Buy or Sell
            qty: Quantity in base currency
            reduce_only: Whether this is a reduce-only order
            
        Returns:
            Order object with execution details
        """
        try:
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_order_time < self.min_order_interval:
                time.sleep(self.min_order_interval)
            
            # Get current price for slippage calculation
            current_price = vedi_prezzo_moneta("linear", symbol)
            if not current_price:
                logger.error(f"Failed to get current price for {symbol}")
                return None
            
            # Create order object
            order = Order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                qty=qty,
                reduce_only=reduce_only,
                created_time=current_time
            )
            
            # Execute order based on side
            start_execution_time = time.time()
            
            try:
                if side == OrderSide.BUY:
                    if reduce_only:
                        # Close short position
                        result = chiudi_operazione_short("linear", symbol, qty)
                    else:
                        # Open long position or close short
                        result = compra_moneta_bybit_by_token("linear", symbol, qty)
                else:  # SELL
                    if reduce_only:
                        # Close long position
                        result = chiudi_operazione_long("linear", symbol, qty)
                    else:
                        # Open short position or close long
                        result = vendi_moneta_bybit_by_token("linear", symbol, qty)
                
                execution_time = time.time() - start_execution_time
                order.execution_time = execution_time
                
            except Exception as e:
                logger.error(f"Order execution failed: {e}")
                order.status = OrderStatus.REJECTED
                return order
            
            # Process result
            if result and 'retCode' in result:
                if result['retCode'] == 0:  # Success
                    order.status = OrderStatus.FILLED
                    order.order_id = result.get('result', {}).get('orderId', 'unknown')
                    
                    # Get fill price (approximate with current price for market orders)
                    fill_price = vedi_prezzo_moneta("linear", symbol)
                    order.avg_fill_price = fill_price
                    order.filled_qty = qty
                    
                    # Calculate slippage
                    if fill_price:
                        expected_price = current_price
                        if side == OrderSide.BUY:
                            slippage = (fill_price - expected_price) / expected_price
                        else:
                            slippage = (expected_price - fill_price) / expected_price
                        
                        order.slippage = slippage
                        self.slippage_history.append(slippage)
                        
                        if abs(slippage) > self.max_acceptable_slippage:
                            logger.warning(f"High slippage detected: {slippage:.4f} for {symbol}")
                    
                    logger.info(f"Market order filled: {symbol} {side.value} {qty} @ ${fill_price:.4f}")
                    
                else:
                    order.status = OrderStatus.REJECTED
                    logger.error(f"Order rejected: {result.get('retMsg', 'Unknown error')}")
            else:
                order.status = OrderStatus.REJECTED
                logger.error("Invalid order response")
            
            # Update tracking
            order.updated_time = time.time()
            self.last_order_time = time.time()
            
            if order.order_id:
                self.open_orders[order.order_id] = order
            
            self.order_history.append(order)
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: OrderSide, qty: float, 
                         price: float, reduce_only: bool = False,
                         time_in_force: str = "GTC") -> Optional[Order]:
        """
        Place limit order
        
        Args:
            symbol: Trading pair
            side: Buy or Sell
            qty: Quantity
            price: Limit price
            reduce_only: Whether this is a reduce-only order
            time_in_force: Time in force (GTC, IOC, FOK)
            
        Returns:
            Order object
        """
        try:
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_order_time < self.min_order_interval:
                time.sleep(self.min_order_interval)
            
            # Create order object
            order = Order(
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                qty=qty,
                price=price,
                reduce_only=reduce_only,
                time_in_force=time_in_force,
                created_time=current_time
            )
            
            # Place limit order using Bybit API
            start_execution_time = time.time()
            
            try:
                result = self.session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side.value,
                    orderType=OrderType.LIMIT.value,
                    qty=str(qty),
                    price=str(price),
                    timeInForce=time_in_force,
                    reduceOnly=reduce_only
                )
                
                execution_time = time.time() - start_execution_time
                order.execution_time = execution_time
                
            except Exception as e:
                logger.error(f"Limit order placement failed: {e}")
                order.status = OrderStatus.REJECTED
                return order
            
            # Process result
            if result and 'retCode' in result:
                if result['retCode'] == 0:
                    order.status = OrderStatus.PENDING
                    order.order_id = result.get('result', {}).get('orderId')
                    order.client_order_id = result.get('result', {}).get('orderLinkId')
                    
                    logger.info(f"Limit order placed: {symbol} {side.value} {qty} @ ${price:.4f}")
                    
                else:
                    order.status = OrderStatus.REJECTED
                    logger.error(f"Limit order rejected: {result.get('retMsg', 'Unknown error')}")
            else:
                order.status = OrderStatus.REJECTED
                logger.error("Invalid limit order response")
            
            # Update tracking
            order.updated_time = time.time()
            self.last_order_time = time.time()
            
            if order.order_id:
                self.open_orders[order.order_id] = order
            
            self.order_history.append(order)
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel pending order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            
        Returns:
            True if cancellation successful
        """
        try:
            result = self.session.cancel_order(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            
            if result and result.get('retCode') == 0:
                # Update order status
                if order_id in self.open_orders:
                    self.open_orders[order_id].status = OrderStatus.CANCELLED
                    self.open_orders[order_id].updated_time = time.time()
                    del self.open_orders[order_id]
                
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order: {result.get('retMsg', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self, symbol: str = None) -> int:
        """
        Cancel all pending orders for symbol or all symbols
        
        Args:
            symbol: Specific symbol to cancel orders for (None for all)
            
        Returns:
            Number of orders cancelled
        """
        try:
            if symbol:
                result = self.session.cancel_all_orders(
                    category="linear",
                    symbol=symbol
                )
            else:
                result = self.session.cancel_all_orders(category="linear")
            
            if result and result.get('retCode') == 0:
                cancelled_count = 0
                
                # Update local order tracking
                orders_to_remove = []
                for order_id, order in self.open_orders.items():
                    if symbol is None or order.symbol == symbol:
                        order.status = OrderStatus.CANCELLED
                        order.updated_time = time.time()
                        orders_to_remove.append(order_id)
                        cancelled_count += 1
                
                for order_id in orders_to_remove:
                    del self.open_orders[order_id]
                
                logger.info(f"Cancelled {cancelled_count} orders for {symbol or 'all symbols'}")
                return cancelled_count
            else:
                logger.error(f"Failed to cancel orders: {result.get('retMsg', 'Unknown error')}")
                return 0
                
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return 0
    
    def get_order_status(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get current status of an order"""
        try:
            result = self.session.get_open_orders(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            
            if result and result.get('retCode') == 0:
                orders_data = result.get('result', {}).get('list', [])
                if orders_data:
                    order_data = orders_data[0]
                    
                    # Update local order if exists
                    if order_id in self.open_orders:
                        order = self.open_orders[order_id]
                        order.status = self._parse_order_status(order_data.get('orderStatus'))
                        order.filled_qty = float(order_data.get('cumExecQty', 0))
                        order.avg_fill_price = float(order_data.get('avgPrice', 0)) if order_data.get('avgPrice') else None
                        order.updated_time = time.time()
                        
                        return order
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    def _parse_order_status(self, bybit_status: str) -> OrderStatus:
        """Convert Bybit order status to internal status"""
        status_map = {
            'New': OrderStatus.PENDING,
            'PartiallyFilled': OrderStatus.PARTIALLY_FILLED,
            'Filled': OrderStatus.FILLED,
            'Cancelled': OrderStatus.CANCELLED,
            'Rejected': OrderStatus.REJECTED
        }
        return status_map.get(bybit_status, OrderStatus.PENDING)
    
    def _monitor_orders(self):
        """Monitor open orders for status changes"""
        while self.monitoring_active:
            try:
                # Check each open order
                orders_to_check = list(self.open_orders.keys())
                
                for order_id in orders_to_check:
                    if order_id in self.open_orders:
                        order = self.open_orders[order_id]
                        updated_order = self.get_order_status(order_id, order.symbol)
                        
                        if updated_order and updated_order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                            # Move from open to history
                            del self.open_orders[order_id]
                            logger.info(f"Order {order_id} status changed to {updated_order.status.value}")
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in order monitoring: {e}")
                time.sleep(5)  # Wait longer on error
    
    def get_execution_stats(self) -> Dict:
        """Get execution performance statistics"""
        if not self.order_history:
            return {'total_orders': 0}
        
        total_orders = len(self.order_history)
        filled_orders = [o for o in self.order_history if o.status == OrderStatus.FILLED]
        rejected_orders = [o for o in self.order_history if o.status == OrderStatus.REJECTED]
        
        fill_rate = len(filled_orders) / total_orders if total_orders > 0 else 0
        
        # Execution time stats
        execution_times = [o.execution_time for o in filled_orders if o.execution_time]
        avg_execution_time = np.mean(execution_times) if execution_times else 0
        
        # Slippage stats
        avg_slippage = np.mean(self.slippage_history) if self.slippage_history else 0
        
        return {
            'total_orders': total_orders,
            'filled_orders': len(filled_orders),
            'rejected_orders': len(rejected_orders),
            'fill_rate': fill_rate,
            'avg_execution_time': avg_execution_time,
            'avg_slippage': avg_slippage,
            'open_orders': len(self.open_orders)
        }

class ExecutionManager:
    """
    High-level execution manager
    Coordinates order execution with strategy requirements
    """
    
    def __init__(self, symbols: List[str], is_testnet: bool = False):
        self.symbols = symbols
        self.executor = BybitExecutor(is_testnet)
        
        # Position tracking
        self.positions = {}  # symbol -> position info
        
        # Execution policies
        self.use_limit_orders = False  # Use market orders for scalping speed
        self.max_order_attempts = 3
        self.retry_delay = 0.5
        
        # Start monitoring
        self.executor.start_monitoring()
    
    def enter_position(self, symbol: str, side: str, size: float, 
                      entry_price: float = None, max_slippage: float = 0.002) -> Tuple[bool, Optional[Order]]:
        """
        Enter new position
        
        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            size: Position size
            entry_price: Desired entry price (None for market order)
            max_slippage: Maximum acceptable slippage
            
        Returns:
            (success, order)
        """
        try:
            order_side = OrderSide.BUY if side.lower() == 'long' else OrderSide.SELL
            
            # Use market order for immediate execution (scalping requirement)
            if entry_price is None or self.use_limit_orders is False:
                order = self.executor.place_market_order(symbol, order_side, size)
            else:
                order = self.executor.place_limit_order(symbol, order_side, size, entry_price)
            
            if order and order.status in [OrderStatus.FILLED, OrderStatus.PENDING]:
                # Update position tracking
                self.positions[symbol] = {
                    'side': side,
                    'size': size,
                    'entry_price': order.avg_fill_price or entry_price,
                    'entry_time': order.created_time,
                    'order_id': order.order_id
                }
                
                logger.info(f"Position entered: {symbol} {side} {size}")
                return True, order
            else:
                logger.error(f"Failed to enter position: {symbol} {side} {size}")
                return False, order
                
        except Exception as e:
            logger.error(f"Error entering position: {e}")
            return False, None
    
    def exit_position(self, symbol: str, size: float = None, 
                     exit_price: float = None) -> Tuple[bool, Optional[Order]]:
        """
        Exit existing position
        
        Args:
            symbol: Trading pair
            size: Size to close (None for full position)
            exit_price: Desired exit price (None for market order)
            
        Returns:
            (success, order)
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"No position to close for {symbol}")
                return False, None
            
            position = self.positions[symbol]
            close_size = size or position['size']
            
            # Determine close side (opposite of position side)
            if position['side'].lower() == 'long':
                close_side = OrderSide.SELL
            else:
                close_side = OrderSide.BUY
            
            # Use market order for immediate execution
            if exit_price is None or self.use_limit_orders is False:
                order = self.executor.place_market_order(symbol, close_side, close_size, reduce_only=True)
            else:
                order = self.executor.place_limit_order(symbol, close_side, close_size, 
                                                      exit_price, reduce_only=True)
            
            if order and order.status in [OrderStatus.FILLED, OrderStatus.PENDING]:
                # Update position tracking
                if close_size >= position['size']:
                    # Full close
                    del self.positions[symbol]
                else:
                    # Partial close
                    self.positions[symbol]['size'] -= close_size
                
                logger.info(f"Position closed: {symbol} size {close_size}")
                return True, order
            else:
                logger.error(f"Failed to close position: {symbol}")
                return False, order
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False, None
    
    def cancel_all_pending_orders(self, symbol: str = None) -> int:
        """Cancel all pending orders"""
        return self.executor.cancel_all_orders(symbol)
    
    def emergency_close_all(self) -> Dict[str, bool]:
        """Emergency close all open positions"""
        results = {}
        
        for symbol in list(self.positions.keys()):
            success, _ = self.exit_position(symbol)
            results[symbol] = success
        
        logger.warning("Emergency close all positions executed")
        return results
    
    def get_execution_summary(self) -> Dict:
        """Get execution performance summary"""
        executor_stats = self.executor.get_execution_stats()
        
        return {
            'executor_stats': executor_stats,
            'open_positions': len(self.positions),
            'position_symbols': list(self.positions.keys())
        }
    
    def shutdown(self):
        """Shutdown execution manager"""
        self.executor.stop_monitoring()
        logger.info("Execution manager shutdown")

# Example usage
if __name__ == "__main__":
    # Test execution manager
    symbols = ["BTCUSDT", "ETHUSDT"]
    exec_manager = ExecutionManager(symbols, is_testnet=True)
    
    try:
        # Test position entry
        success, order = exec_manager.enter_position("BTCUSDT", "long", 0.001)
        if success:
            print(f"Position entered successfully: {order.order_id}")
            
            # Wait a bit then close
            time.sleep(5)
            success, close_order = exec_manager.exit_position("BTCUSDT")
            if success:
                print(f"Position closed successfully: {close_order.order_id}")
        
        # Get execution stats
        stats = exec_manager.get_execution_summary()
        print(f"Execution stats: {stats}")
        
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        exec_manager.shutdown()
