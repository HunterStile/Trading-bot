"""
Real-Time Market Data Feed
WebSocket connection to Bybit for live orderflow data
"""
import asyncio
import websockets
import json
import logging
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from threading import Thread
import queue

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Singolo trade ricevuto dal feed"""
    symbol: str
    price: float
    volume: float
    side: str  # 'Buy' or 'Sell'
    timestamp: datetime
    trade_id: str

@dataclass
class OrderBookUpdate:
    """Aggiornamento order book"""
    symbol: str
    bids: List[List[float]]  # [[price, size], ...]
    asks: List[List[float]]  # [[price, size], ...]
    timestamp: datetime

class RealTimeFeed:
    """
    Feed real-time da Bybit WebSocket per analisi orderflow
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        
        # Callback functions
        self.trade_callbacks: List[Callable[[Trade], None]] = []
        self.orderbook_callbacks: List[Callable[[OrderBookUpdate], None]] = []
        
        # Data storage
        self.trades_queue = queue.Queue(maxsize=10000)
        self.orderbook_queue = queue.Queue(maxsize=1000)
        
        # Connection state
        self.is_connected = False
        self.websocket = None
        self.running = False
        
        # Data buffers for chart system
        self.recent_trades = {}  # symbol -> list of trades
        self.current_orderbook = {}  # symbol -> latest orderbook
        
    async def connect(self):
        """Connette al WebSocket Bybit"""
        try:
            logger.info("🔌 Connessione a Bybit WebSocket...")
            
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            
            # Sottoscrivi ai canali
            await self._subscribe_to_channels()
            
            logger.info("✅ Connesso a Bybit WebSocket")
            
            # Avvia loop di ricezione messaggi
            await self._message_loop()
            
        except Exception as e:
            logger.error(f"❌ Errore connessione WebSocket: {e}")
            self.is_connected = False
            
    async def _subscribe_to_channels(self):
        """Sottoscrivi ai canali trades e orderbook"""
        for symbol in self.symbols:
            # Sottoscrivi trades
            trade_sub = {
                "op": "subscribe",
                "args": [f"publicTrade.{symbol}"]
            }
            await self.websocket.send(json.dumps(trade_sub))
            
            # Sottoscrivi orderbook (depth 25 levels)
            orderbook_sub = {
                "op": "subscribe", 
                "args": [f"orderbook.25.{symbol}"]
            }
            await self.websocket.send(json.dumps(orderbook_sub))
            
        logger.info(f"📡 Sottoscritto a {len(self.symbols)} simboli")
    
    async def _message_loop(self):
        """Loop principale ricezione messaggi"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 Connessione WebSocket chiusa")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Errore nel message loop: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: str):
        """Gestisce messaggi ricevuti dal WebSocket"""
        try:
            data = json.loads(message)
            
            # Gestisce conferme sottoscrizione
            if data.get("success"):
                logger.info(f"✅ Sottoscrizione confermata: {data.get('ret_msg', '')}")
                return
                
            # Gestisce dati topic
            topic = data.get("topic", "")
            
            if topic.startswith("publicTrade"):
                await self._handle_trade_data(data)
            elif topic.startswith("orderbook"):
                await self._handle_orderbook_data(data)
                
        except json.JSONDecodeError:
            logger.warning("⚠️ Messaggio JSON non valido ricevuto")
        except Exception as e:
            logger.error(f"❌ Errore gestione messaggio: {e}")
    
    async def _handle_trade_data(self, data: Dict):
        """Gestisce dati trades"""
        try:
            topic = data["topic"]
            symbol = topic.split(".")[1]
            trades_data = data["data"]
            
            for trade_data in trades_data:
                trade = Trade(
                    symbol=symbol,
                    price=float(trade_data["p"]),
                    volume=float(trade_data["v"]),
                    side='buy' if trade_data["S"] == "Buy" else 'sell',
                    timestamp=datetime.fromtimestamp(int(trade_data["T"]) / 1000),
                    trade_id=trade_data["i"]
                )
                
                # Aggiungi a buffer
                if symbol not in self.recent_trades:
                    self.recent_trades[symbol] = []
                    
                self.recent_trades[symbol].append(trade)
                
                # Mantieni solo ultimi 1000 trades
                if len(self.recent_trades[symbol]) > 1000:
                    self.recent_trades[symbol] = self.recent_trades[symbol][-1000:]
                
                # Aggiungi a queue per processori esterni
                if not self.trades_queue.full():
                    self.trades_queue.put(trade)
                
                # Chiama callbacks
                for callback in self.trade_callbacks:
                    try:
                        callback(trade)
                    except Exception as e:
                        logger.error(f"❌ Errore callback trade: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Errore gestione trade data: {e}")
    
    async def _handle_orderbook_data(self, data: Dict):
        """Gestisce dati orderbook"""
        try:
            topic = data["topic"]
            symbol = topic.split(".")[2]
            orderbook_data = data["data"]
            
            orderbook_update = OrderBookUpdate(
                symbol=symbol,
                bids=[[float(bid[0]), float(bid[1])] for bid in orderbook_data["b"]],
                asks=[[float(ask[0]), float(ask[1])] for ask in orderbook_data["a"]],
                timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000)
            )
            
            # Aggiorna orderbook corrente
            self.current_orderbook[symbol] = orderbook_update
            
            # Aggiungi a queue
            if not self.orderbook_queue.full():
                self.orderbook_queue.put(orderbook_update)
            
            # Chiama callbacks
            for callback in self.orderbook_callbacks:
                try:
                    callback(orderbook_update)
                except Exception as e:
                    logger.error(f"❌ Errore callback orderbook: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Errore gestione orderbook data: {e}")
    
    def add_trade_callback(self, callback: Callable[[Trade], None]):
        """Aggiunge callback per trades"""
        self.trade_callbacks.append(callback)
    
    def add_orderbook_callback(self, callback: Callable[[OrderBookUpdate], None]):
        """Aggiunge callback per orderbook"""
        self.orderbook_callbacks.append(callback)
    
    def get_recent_trades_df(self, symbol: str, minutes: int = 5) -> pd.DataFrame:
        """
        Restituisce DataFrame trades recenti per analisi volume profile
        
        Args:
            symbol: Simbolo da analizzare
            minutes: Minuti indietro da considerare
            
        Returns:
            DataFrame con colonne ['price', 'volume', 'side', 'timestamp']
        """
        if symbol not in self.recent_trades:
            return pd.DataFrame(columns=['price', 'volume', 'side', 'timestamp'])
        
        trades = self.recent_trades[symbol]
        cutoff_time = datetime.now() - pd.Timedelta(minutes=minutes)
        
        # Filtra trades recenti
        recent_trades = [t for t in trades if t.timestamp >= cutoff_time]
        
        if not recent_trades:
            return pd.DataFrame(columns=['price', 'volume', 'side', 'timestamp'])
        
        # Converti in DataFrame
        data = []
        for trade in recent_trades:
            data.append({
                'price': trade.price,
                'volume': trade.volume,
                'side': trade.side,
                'timestamp': trade.timestamp
            })
        
        return pd.DataFrame(data)
    
    def get_large_orders(self, symbol: str, min_size: float = 1.0) -> List[Dict]:
        """
        Identifica ordini grossi nell'orderbook
        
        Args:
            symbol: Simbolo da analizzare
            min_size: Dimensione minima ordine (in unità base)
            
        Returns:
            Lista ordini grossi con informazioni
        """
        if symbol not in self.current_orderbook:
            return []
        
        orderbook = self.current_orderbook[symbol]
        large_orders = []
        
        # Analizza bids (ordini di acquisto)
        for price, size in orderbook.bids:
            if size >= min_size:
                large_orders.append({
                    'side': 'buy',
                    'price': price,
                    'size': size,
                    'value': price * size,
                    'timestamp': orderbook.timestamp
                })
        
        # Analizza asks (ordini di vendita)
        for price, size in orderbook.asks:
            if size >= min_size:
                large_orders.append({
                    'side': 'sell',
                    'price': price,
                    'size': size,
                    'value': price * size,
                    'timestamp': orderbook.timestamp
                })
        
        # Ordina per valore
        large_orders.sort(key=lambda x: x['value'], reverse=True)
        return large_orders
    
    async def disconnect(self):
        """Disconnette dal WebSocket"""
        self.running = False
        self.is_connected = False
        
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 Disconnesso da Bybit WebSocket")
    
    def start_background_feed(self):
        """Avvia il feed in background thread"""
        def run_feed():
            asyncio.run(self.connect())
        
        self.running = True
        thread = Thread(target=run_feed, daemon=True)
        thread.start()
        logger.info("🚀 Feed real-time avviato in background")
        return thread


def test_real_time_feed():
    """Test simulato del real-time feed"""
    import time
    import random
    
    print("📡 Real-Time Feed Test (simulato)")
    
    feed = RealTimeFeed(['BTCUSDT'])
    
    # Callback per stampare trades
    def on_trade(trade: Trade):
        print(f"💰 {trade.symbol}: {trade.side} {trade.volume:.4f} @ ${trade.price:.2f}")
    
    def on_orderbook(orderbook: OrderBookUpdate):
        best_bid = max(orderbook.bids, key=lambda x: x[0]) if orderbook.bids else [0, 0]
        best_ask = min(orderbook.asks, key=lambda x: x[0]) if orderbook.asks else [0, 0]
        spread = best_ask[0] - best_bid[0] if best_bid[0] and best_ask[0] else 0
        print(f"📊 {orderbook.symbol} Spread: ${spread:.2f} (${best_bid[0]:.2f} / ${best_ask[0]:.2f})")
    
    feed.add_trade_callback(on_trade)
    feed.add_orderbook_callback(on_orderbook)
    
    # Simula alcuni trades per test
    print("🎭 Simulazione trades...")
    base_price = 50000
    for i in range(10):
        trade = Trade(
            symbol='BTCUSDT',
            price=base_price + random.uniform(-100, 100),
            volume=random.uniform(0.01, 2.0),
            side=random.choice(['buy', 'sell']),
            timestamp=datetime.now(),
            trade_id=f"test_{i}"
        )
        
        # Simula callback
        on_trade(trade)
        
        # Aggiungi a buffer per test DataFrame
        if 'BTCUSDT' not in feed.recent_trades:
            feed.recent_trades['BTCUSDT'] = []
        feed.recent_trades['BTCUSDT'].append(trade)
    
    # Test DataFrame
    df = feed.get_recent_trades_df('BTCUSDT')
    print(f"\n📊 DataFrame Test: {len(df)} trades")
    if not df.empty:
        print(f"   Prezzo medio: ${df['price'].mean():.2f}")
        print(f"   Volume totale: {df['volume'].sum():.4f}")
        print(f"   Buy/Sell: {df['side'].value_counts().to_dict()}")
    
    print("✅ Real-Time Feed test completato")

if __name__ == "__main__":
    test_real_time_feed()