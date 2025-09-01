"""
Data Feed Module - WebSocket connection for real-time market data
Handles Bybit WebSocket streams for orderbook, trades, and ticker data
"""

import asyncio
import websockets
import json
import time
import logging
from typing import Dict, List, Callable, Optional
from collections import deque, defaultdict
import threading
from queue import Queue
import hmac
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BybitWebSocketClient:
    """
    WebSocket client for Bybit real-time data feeds
    Supports orderbook, trades, and ticker subscriptions
    """
    
    def __init__(self, is_testnet: bool = False):
        self.is_testnet = is_testnet
        self.base_url = "wss://stream-testnet.bybit.com/v5/public/linear" if is_testnet else "wss://stream.bybit.com/v5/public/linear"
        self.websocket = None
        self.subscriptions = set()
        self.callbacks = defaultdict(list)
        self.running = False
        self.ping_interval = 20  # seconds
        self.last_ping = 0
        
        # Data storage
        self.orderbook_data = {}
        self.trade_data = deque(maxlen=1000)
        self.ticker_data = {}
        
        # Threading
        self.message_queue = Queue()
        self.processor_thread = None
        
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(self.base_url)
            self.running = True
            logger.info(f"Connected to Bybit WebSocket: {self.base_url}")
            
            # Start message processor thread
            self.processor_thread = threading.Thread(target=self._process_messages, daemon=True)
            self.processor_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from Bybit WebSocket")
    
    async def subscribe(self, channel: str, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to a WebSocket channel
        
        Args:
            channel: orderbook.1, publicTrade, tickers
            symbol: Trading pair (e.g., BTCUSDT)
            callback: Optional callback function for data processing
        """
        subscription = f"{channel}.{symbol}"
        
        if subscription in self.subscriptions:
            logger.warning(f"Already subscribed to {subscription}")
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [subscription]
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_msg))
            self.subscriptions.add(subscription)
            
            if callback:
                self.callbacks[subscription].append(callback)
            
            logger.info(f"Subscribed to {subscription}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {subscription}: {e}")
    
    async def unsubscribe(self, channel: str, symbol: str):
        """Unsubscribe from a WebSocket channel"""
        subscription = f"{channel}.{symbol}"
        
        if subscription not in self.subscriptions:
            logger.warning(f"Not subscribed to {subscription}")
            return
        
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": [subscription]
        }
        
        try:
            await self.websocket.send(json.dumps(unsubscribe_msg))
            self.subscriptions.remove(subscription)
            logger.info(f"Unsubscribed from {subscription}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {subscription}: {e}")
    
    async def listen(self):
        """Main listening loop for WebSocket messages"""
        while self.running:
            try:
                # Send ping periodically
                if time.time() - self.last_ping > self.ping_interval:
                    await self._send_ping()
                
                # Receive and queue messages
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                self.message_queue.put(message)
                
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                break
        
        # Attempt reconnection
        if self.running:
            logger.info("Attempting to reconnect...")
            await self._reconnect()
    
    async def _send_ping(self):
        """Send ping to keep connection alive"""
        try:
            ping_msg = {"op": "ping"}
            await self.websocket.send(json.dumps(ping_msg))
            self.last_ping = time.time()
        except Exception as e:
            logger.error(f"Failed to send ping: {e}")
    
    async def _reconnect(self):
        """Reconnect and re-subscribe to channels"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                
                if await self.connect():
                    # Re-subscribe to all channels
                    old_subscriptions = self.subscriptions.copy()
                    self.subscriptions.clear()
                    
                    for subscription in old_subscriptions:
                        channel, symbol = subscription.split('.', 1)
                        await self.subscribe(channel, symbol)
                    
                    logger.info("Successfully reconnected and re-subscribed")
                    return
                    
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                retry_delay *= 2
        
        logger.error("Failed to reconnect after maximum retries")
        self.running = False
    
    def _process_messages(self):
        """Process incoming WebSocket messages in separate thread"""
        while self.running:
            try:
                if not self.message_queue.empty():
                    message = self.message_queue.get(timeout=1.0)
                    data = json.loads(message)
                    self._handle_message(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue
    
    def _handle_message(self, data: Dict):
        """Handle different types of WebSocket messages"""
        if data.get('op') == 'pong':
            return
        
        if 'topic' in data:
            topic = data['topic']
            
            # Handle orderbook updates
            if 'orderbook' in topic:
                self._handle_orderbook(data)
            
            # Handle trade updates
            elif 'publicTrade' in topic:
                self._handle_trade(data)
            
            # Handle ticker updates
            elif 'tickers' in topic:
                self._handle_ticker(data)
            
            # Execute callbacks
            if topic in self.callbacks:
                for callback in self.callbacks[topic]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error in callback for {topic}: {e}")
    
    def _handle_orderbook(self, data: Dict):
        """Process orderbook data"""
        try:
            symbol = data['topic'].split('.')[1]
            orderbook_data = data['data']
            
            if symbol not in self.orderbook_data:
                self.orderbook_data[symbol] = {
                    'bids': [],
                    'asks': [],
                    'timestamp': 0
                }
            
            # Update orderbook
            if orderbook_data.get('b'):  # bids
                self.orderbook_data[symbol]['bids'] = [[float(price), float(size)] for price, size in orderbook_data['b']]
            
            if orderbook_data.get('a'):  # asks
                self.orderbook_data[symbol]['asks'] = [[float(price), float(size)] for price, size in orderbook_data['a']]
            
            self.orderbook_data[symbol]['timestamp'] = orderbook_data.get('ts', time.time() * 1000)
            
        except Exception as e:
            logger.error(f"Error handling orderbook data: {e}")
    
    def _handle_trade(self, data: Dict):
        """Process trade data"""
        try:
            for trade in data['data']:
                trade_info = {
                    'symbol': trade['s'],
                    'price': float(trade['p']),
                    'size': float(trade['v']),
                    'side': trade['S'],
                    'timestamp': int(trade['T'])
                }
                self.trade_data.append(trade_info)
                
        except Exception as e:
            logger.error(f"Error handling trade data: {e}")
    
    def _handle_ticker(self, data: Dict):
        """Process ticker data"""
        try:
            for ticker in data['data']:
                symbol = ticker['symbol']
                self.ticker_data[symbol] = {
                    'last_price': float(ticker.get('lastPrice', 0)),
                    'bid': float(ticker.get('bid1Price', 0)),
                    'ask': float(ticker.get('ask1Price', 0)),
                    'volume': float(ticker.get('volume24h', 0)),
                    'change': float(ticker.get('price24hPcnt', 0)),
                    'timestamp': int(ticker.get('ts', time.time() * 1000))
                }
                
        except Exception as e:
            logger.error(f"Error handling ticker data: {e}")
    
    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """Get latest orderbook for symbol"""
        return self.orderbook_data.get(symbol)
    
    def get_recent_trades(self, symbol: str, count: int = 100) -> List[Dict]:
        """Get recent trades for symbol"""
        return [trade for trade in list(self.trade_data)[-count:] if trade['symbol'] == symbol]
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get latest ticker for symbol"""
        return self.ticker_data.get(symbol)

class MarketDataManager:
    """
    High-level market data manager
    Provides clean interface for accessing real-time market data
    """
    
    def __init__(self, symbols: List[str], is_testnet: bool = False):
        self.symbols = symbols
        self.ws_client = BybitWebSocketClient(is_testnet)
        self.running = False
        
    async def start(self):
        """Start market data feeds"""
        try:
            if await self.ws_client.connect():
                # Subscribe to required channels for all symbols
                for symbol in self.symbols:
                    await self.ws_client.subscribe("orderbook.1", symbol)
                    await self.ws_client.subscribe("publicTrade", symbol)
                    await self.ws_client.subscribe("tickers", symbol)
                
                self.running = True
                logger.info(f"Market data manager started for symbols: {self.symbols}")
                
                # Start listening
                await self.ws_client.listen()
                
        except Exception as e:
            logger.error(f"Failed to start market data manager: {e}")
    
    async def stop(self):
        """Stop market data feeds"""
        self.running = False
        await self.ws_client.disconnect()
        logger.info("Market data manager stopped")
    
    def get_bid_ask(self, symbol: str) -> Optional[tuple]:
        """Get best bid and ask prices"""
        orderbook = self.ws_client.get_orderbook(symbol)
        if orderbook and orderbook['bids'] and orderbook['asks']:
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            return best_bid, best_ask
        return None
    
    def get_mid_price(self, symbol: str) -> Optional[float]:
        """Get mid price (bid + ask) / 2"""
        bid_ask = self.get_bid_ask(symbol)
        if bid_ask:
            return (bid_ask[0] + bid_ask[1]) / 2
        return None
    
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get bid-ask spread"""
        bid_ask = self.get_bid_ask(symbol)
        if bid_ask:
            return bid_ask[1] - bid_ask[0]
        return None
    
    def get_orderbook_imbalance(self, symbol: str, depth: int = 5) -> Optional[float]:
        """
        Calculate orderbook imbalance
        Returns value between -1 (sell pressure) and 1 (buy pressure)
        """
        orderbook = self.ws_client.get_orderbook(symbol)
        if not orderbook or not orderbook['bids'] or not orderbook['asks']:
            return None
        
        bid_volume = sum(bid[1] for bid in orderbook['bids'][:depth])
        ask_volume = sum(ask[1] for ask in orderbook['asks'][:depth])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0
        
        return (bid_volume - ask_volume) / total_volume
    
    def get_volume_profile(self, symbol: str, time_window: int = 60) -> Dict:
        """Get volume profile for specified time window (seconds)"""
        current_time = time.time() * 1000
        cutoff_time = current_time - (time_window * 1000)
        
        recent_trades = [
            trade for trade in self.ws_client.get_recent_trades(symbol)
            if trade['timestamp'] >= cutoff_time
        ]
        
        if not recent_trades:
            return {'total_volume': 0, 'buy_volume': 0, 'sell_volume': 0, 'trade_count': 0}
        
        total_volume = sum(trade['size'] for trade in recent_trades)
        buy_volume = sum(trade['size'] for trade in recent_trades if trade['side'] == 'Buy')
        sell_volume = total_volume - buy_volume
        
        return {
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'trade_count': len(recent_trades),
            'avg_trade_size': total_volume / len(recent_trades) if recent_trades else 0
        }

# Example usage
if __name__ == "__main__":
    async def main():
        symbols = ["BTCUSDT", "ETHUSDT"]
        data_manager = MarketDataManager(symbols, is_testnet=False)
        
        try:
            await data_manager.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await data_manager.stop()
    
    asyncio.run(main())
