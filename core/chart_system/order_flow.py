"""
Order Flow Analyzer
Analizza il flusso degli ordini per identificare pattern e ordini grossi
Combina Volume Profile con dati real-time per trading insights
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from .volume_profile import VolumeProfileCalculator, VolumeProfileMetrics
from .real_time_feed import RealTimeFeed, Trade, OrderBookUpdate

logger = logging.getLogger(__name__)

@dataclass
class LargeOrder:
    """Ordine grosso rilevato"""
    symbol: str
    side: str  # 'buy' or 'sell'
    price: float
    volume: float
    value: float  # price * volume
    timestamp: datetime
    source: str  # 'trade' or 'orderbook'
    impact_score: float  # 0-100, impatto sul mercato

@dataclass
class OrderFlowSignal:
    """Segnale generato dall'analisi orderflow"""
    symbol: str
    signal_type: str  # 'accumulation', 'distribution', 'breakout', 'absorption'
    strength: float  # 0-100
    price_level: float
    description: str
    timestamp: datetime
    supporting_data: Dict

@dataclass
class MarketMicrostructure:
    """Analisi microstruttura del mercato"""
    symbol: str
    timestamp: datetime
    
    # Spread e liquidità
    bid_ask_spread: float
    spread_percentage: float
    depth_imbalance: float  # (bid_depth - ask_depth) / total_depth
    
    # Volumi e pressioni
    buy_pressure: float
    sell_pressure: float
    net_pressure: float
    
    # Pattern detection
    absorption_detected: bool
    iceberg_orders: List[Dict]
    hidden_liquidity_estimate: float

class OrderFlowAnalyzer:
    """
    Analizza il flusso ordini real-time per identificare:
    - Ordini grossi (whales)
    - Pattern di accumulation/distribution  
    - Breakout con volume
    - Absorption patterns
    - Iceberg orders
    """
    
    def __init__(self, 
                 large_order_threshold_btc: float = 5.0,
                 large_order_threshold_eth: float = 50.0,
                 volume_profile_period: int = 60):  # minuti
        
        self.large_order_thresholds = {
            'BTCUSDT': large_order_threshold_btc,
            'ETHUSDT': large_order_threshold_eth,
        }
        self.volume_profile_period = volume_profile_period
        self.volume_calculator = VolumeProfileCalculator(tick_size=1.0)
        
        # Data storage
        self.large_orders_history = []
        self.signals_history = []
        self.price_alerts = {}  # symbol -> alert levels
        
        # Real-time state
        self.last_volume_profiles = {}  # symbol -> VolumeProfileMetrics
        self.order_flow_state = {}  # symbol -> current state
        
    def analyze_trade(self, trade: Trade) -> List[LargeOrder]:
        """
        Analizza un singolo trade per rilevare ordini grossi
        
        Args:
            trade: Trade da analizzare
            
        Returns:
            Lista di ordini grossi rilevati
        """
        large_orders = []
        
        # Controlla se è un ordine grosso
        threshold = self.large_order_thresholds.get(trade.symbol, 1.0)
        
        if trade.volume >= threshold:
            # Calcola impact score basato su volume relativo
            impact_score = min(100, (trade.volume / threshold) * 20)
            
            large_order = LargeOrder(
                symbol=trade.symbol,
                side=trade.side,
                price=trade.price,
                volume=trade.volume,
                value=trade.price * trade.volume,
                timestamp=trade.timestamp,
                source='trade',
                impact_score=impact_score
            )
            
            large_orders.append(large_order)
            self.large_orders_history.append(large_order)
            
            logger.info(f"🐋 Large order detected: {trade.side} {trade.volume:.4f} {trade.symbol} @ ${trade.price:.2f}")
        
        return large_orders
    
    def analyze_orderbook(self, orderbook: OrderBookUpdate) -> Tuple[List[LargeOrder], MarketMicrostructure]:
        """
        Analizza orderbook per ordini grossi e microstruttura
        
        Args:
            orderbook: Aggiornamento orderbook
            
        Returns:
            Tuple (large_orders, microstructure_analysis)
        """
        large_orders = []
        threshold = self.large_order_thresholds.get(orderbook.symbol, 1.0)
        
        # Analizza ordini grossi nel book
        for price, size in orderbook.bids + orderbook.asks:
            if size >= threshold:
                side = 'buy' if [price, size] in orderbook.bids else 'sell'
                impact_score = min(100, (size / threshold) * 15)  # Minore per orderbook
                
                large_order = LargeOrder(
                    symbol=orderbook.symbol,
                    side=side,
                    price=price,
                    volume=size,
                    value=price * size,
                    timestamp=orderbook.timestamp,
                    source='orderbook',
                    impact_score=impact_score
                )
                large_orders.append(large_order)
        
        # Analizza microstruttura
        microstructure = self._analyze_microstructure(orderbook)
        
        return large_orders, microstructure
    
    def _analyze_microstructure(self, orderbook: OrderBookUpdate) -> MarketMicrostructure:
        """Analizza la microstruttura del mercato"""
        
        if not orderbook.bids or not orderbook.asks:
            return self._empty_microstructure(orderbook.symbol, orderbook.timestamp)
        
        # Best bid/ask
        best_bid = max(orderbook.bids, key=lambda x: x[0])
        best_ask = min(orderbook.asks, key=lambda x: x[0])
        
        # Spread
        spread = best_ask[0] - best_bid[0]
        spread_pct = (spread / best_ask[0]) * 100
        
        # Depth analysis
        total_bid_volume = sum(size for _, size in orderbook.bids)
        total_ask_volume = sum(size for _, size in orderbook.asks)
        total_volume = total_bid_volume + total_ask_volume
        
        depth_imbalance = 0
        if total_volume > 0:
            depth_imbalance = (total_bid_volume - total_ask_volume) / total_volume
        
        # Pressioni
        buy_pressure = total_bid_volume / total_volume if total_volume > 0 else 0.5
        sell_pressure = total_ask_volume / total_volume if total_volume > 0 else 0.5
        net_pressure = buy_pressure - sell_pressure
        
        # Pattern detection
        absorption_detected = self._detect_absorption(orderbook)
        iceberg_orders = self._detect_iceberg_orders(orderbook)
        hidden_liquidity = self._estimate_hidden_liquidity(orderbook)
        
        return MarketMicrostructure(
            symbol=orderbook.symbol,
            timestamp=orderbook.timestamp,
            bid_ask_spread=spread,
            spread_percentage=spread_pct,
            depth_imbalance=depth_imbalance,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            net_pressure=net_pressure,
            absorption_detected=absorption_detected,
            iceberg_orders=iceberg_orders,
            hidden_liquidity_estimate=hidden_liquidity
        )
    
    def _detect_absorption(self, orderbook: OrderBookUpdate) -> bool:
        """Rileva pattern di absorption (grandi ordini che assorbono liquidità)"""
        # Cerca ordini molto grandi rispetto alla media
        threshold = self.large_order_thresholds.get(orderbook.symbol, 1.0)
        
        all_orders = [(price, size) for price, size in orderbook.bids + orderbook.asks]
        if not all_orders:
            return False
        
        avg_size = np.mean([size for _, size in all_orders])
        max_size = max(size for _, size in all_orders)
        
        # Absorption se ordine più grosso è 5x la media e sopra threshold
        return max_size > (avg_size * 5) and max_size > threshold
    
    def _detect_iceberg_orders(self, orderbook: OrderBookUpdate) -> List[Dict]:
        """Rileva potenziali iceberg orders"""
        icebergs = []
        
        # Cerca ordini ripetuti allo stesso prezzo nel tempo
        # (Per ora implementazione semplificata)
        
        for price, size in orderbook.bids + orderbook.asks:
            # Iceberg candidato se ordine molto piatto rispetto agli altri
            side = 'buy' if [price, size] in orderbook.bids else 'sell'
            
            # Logica semplificata: ordini "sospetti" 
            if size > 0 and size == round(size, 2):  # Dimensioni "round"
                icebergs.append({
                    'side': side,
                    'price': price,
                    'visible_size': size,
                    'confidence': 0.3  # Bassa confidenza per ora
                })
        
        return icebergs[:5]  # Max 5 per performance
    
    def _estimate_hidden_liquidity(self, orderbook: OrderBookUpdate) -> float:
        """Stima la liquidità nascosta"""
        # Stima basata su gap nel book e pattern storici
        visible_liquidity = sum(size for _, size in orderbook.bids + orderbook.asks)
        
        # Stima empirica: 20-30% di liquidità nascosta nei mercati crypto
        hidden_estimate = visible_liquidity * 0.25
        
        return hidden_estimate
    
    def analyze_volume_profile_signals(self, symbol: str, trades_df: pd.DataFrame) -> List[OrderFlowSignal]:
        """
        Analizza volume profile per generare segnali
        
        Args:
            symbol: Simbolo da analizzare
            trades_df: DataFrame con trades recenti
            
        Returns:
            Lista di segnali generati
        """
        signals = []
        
        if trades_df.empty:
            return signals
        
        # Calcola volume profile
        metrics = self.volume_calculator.calculate_profile(trades_df)
        self.last_volume_profiles[symbol] = metrics
        
        # Analizza delta profile
        delta_analysis = self.volume_calculator.analyze_delta_profile(metrics)
        
        # Segnale accumulation/distribution
        if abs(delta_analysis['total_delta']) > metrics.total_volume * 0.1:  # 10% threshold
            signal_type = 'accumulation' if delta_analysis['total_delta'] > 0 else 'distribution'
            strength = min(100, abs(delta_analysis['total_delta']) / metrics.total_volume * 100)
            
            signals.append(OrderFlowSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                price_level=metrics.poc_price,
                description=f"{signal_type.title()} detected at POC with {delta_analysis['total_delta']:.2f} delta",
                timestamp=datetime.now(),
                supporting_data={
                    'delta': delta_analysis['total_delta'],
                    'poc_price': metrics.poc_price,
                    'total_volume': metrics.total_volume
                }
            ))
        
        # Segnale breakout
        if self._detect_breakout_pattern(symbol, metrics):
            signals.append(OrderFlowSignal(
                symbol=symbol,
                signal_type='breakout',
                strength=75,
                price_level=metrics.vah_price,
                description="Volume breakout above VAH detected",
                timestamp=datetime.now(),
                supporting_data={
                    'vah_price': metrics.vah_price,
                    'val_price': metrics.val_price,
                    'poc_price': metrics.poc_price
                }
            ))
        
        return signals
    
    def _detect_breakout_pattern(self, symbol: str, metrics: VolumeProfileMetrics) -> bool:
        """Rileva pattern di breakout basato su volume profile"""
        # Semplificato: breakout se volume significativo sopra VAH
        if not metrics.levels:
            return False
        
        # Volumi sopra VAH
        above_vah_volume = sum(
            level.volume for level in metrics.levels 
            if level.price > metrics.vah_price
        )
        
        # Breakout se >20% del volume è sopra VAH
        return above_vah_volume > (metrics.total_volume * 0.2)
    
    def _empty_microstructure(self, symbol: str, timestamp: datetime) -> MarketMicrostructure:
        """Restituisce microstruttura vuota"""
        return MarketMicrostructure(
            symbol=symbol,
            timestamp=timestamp,
            bid_ask_spread=0.0,
            spread_percentage=0.0,
            depth_imbalance=0.0,
            buy_pressure=0.5,
            sell_pressure=0.5,
            net_pressure=0.0,
            absorption_detected=False,
            iceberg_orders=[],
            hidden_liquidity_estimate=0.0
        )
    
    def get_recent_large_orders(self, symbol: str = None, minutes: int = 15) -> List[LargeOrder]:
        """Restituisce ordini grossi recenti"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        recent_orders = [
            order for order in self.large_orders_history
            if order.timestamp >= cutoff and (symbol is None or order.symbol == symbol)
        ]
        
        return sorted(recent_orders, key=lambda x: x.timestamp, reverse=True)
    
    def get_summary_stats(self, symbol: str) -> Dict:
        """Restituisce statistiche riassuntive per simbolo"""
        recent_orders = self.get_recent_large_orders(symbol, minutes=60)
        
        if not recent_orders:
            return {'symbol': symbol, 'large_orders_count': 0}
        
        total_volume = sum(order.volume for order in recent_orders)
        total_value = sum(order.value for order in recent_orders)
        avg_impact = np.mean([order.impact_score for order in recent_orders])
        
        buy_orders = [o for o in recent_orders if o.side == 'buy']
        sell_orders = [o for o in recent_orders if o.side == 'sell']
        
        return {
            'symbol': symbol,
            'large_orders_count': len(recent_orders),
            'total_volume': total_volume,
            'total_value': total_value,
            'avg_impact_score': avg_impact,
            'buy_orders': len(buy_orders),
            'sell_orders': len(sell_orders),
            'buy_sell_ratio': len(buy_orders) / len(sell_orders) if sell_orders else float('inf'),
            'latest_poc': self.last_volume_profiles.get(symbol, {}).poc_price if symbol in self.last_volume_profiles else None
        }


def test_order_flow_analyzer():
    """Test dell'Order Flow Analyzer"""
    print("🔍 Order Flow Analyzer Test")
    
    analyzer = OrderFlowAnalyzer(
        large_order_threshold_btc=2.0,  # Soglia più bassa per test
        large_order_threshold_eth=20.0
    )
    
    # Simula alcuni trades
    from .real_time_feed import Trade
    import random
    
    trades = []
    base_price = 50000
    
    for i in range(50):
        volume = random.choice([0.1, 0.5, 1.0, 3.0, 5.0])  # Include alcuni grossi
        trade = Trade(
            symbol='BTCUSDT',
            price=base_price + random.uniform(-50, 50),
            volume=volume,
            side=random.choice(['buy', 'sell']),
            timestamp=datetime.now(),
            trade_id=f"test_{i}"
        )
        trades.append(trade)
        
        # Analizza trade
        large_orders = analyzer.analyze_trade(trade)
        if large_orders:
            for order in large_orders:
                print(f"🐋 Large Order: {order.side} {order.volume:.2f} @ ${order.price:.2f} (Impact: {order.impact_score:.1f})")
    
    # Test volume profile signals
    trades_df = pd.DataFrame([{
        'price': t.price,
        'volume': t.volume,
        'side': t.side,
        'timestamp': t.timestamp
    } for t in trades])
    
    signals = analyzer.analyze_volume_profile_signals('BTCUSDT', trades_df)
    print(f"\n📊 Volume Profile Signals: {len(signals)}")
    for signal in signals:
        print(f"   {signal.signal_type}: {signal.strength:.1f}% @ ${signal.price_level:.2f}")
        print(f"   {signal.description}")
    
    # Test summary stats
    stats = analyzer.get_summary_stats('BTCUSDT')
    print(f"\n📈 Summary Stats:")
    print(f"   Large orders: {stats['large_orders_count']}")
    print(f"   Total volume: {stats.get('total_volume', 0):.2f}")
    print(f"   Buy/Sell ratio: {stats.get('buy_sell_ratio', 0):.2f}")
    
    print("✅ Order Flow Analyzer test completato")

if __name__ == "__main__":
    test_order_flow_analyzer()