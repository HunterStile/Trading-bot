"""
Chart Renderer - Real-Time Orderflow Visualization
Crea grafici interattivi con Volume Profile, Large Orders e Pattern Detection
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
from .volume_profile import VolumeProfileMetrics, VolumeProfileLevel
from .order_flow import LargeOrder, OrderFlowSignal, MarketMicrostructure
from .real_time_feed import Trade, OrderBookUpdate

logger = logging.getLogger(__name__)

class ChartRenderer:
    """
    Renderizza grafici real-time per analisi orderflow
    """
    
    def __init__(self, 
                 update_interval_seconds: int = 5,
                 max_candles: int = 500,
                 chart_height: int = 800):
        
        self.update_interval = update_interval_seconds
        self.max_candles = max_candles
        self.chart_height = chart_height
        
        # Color scheme
        self.colors = {
            'buy': '#26a69a',      # Verde per buy
            'sell': '#ef5350',     # Rosso per sell
            'poc': '#ff9800',      # Arancione per POC
            'vah': '#2196f3',      # Blu per VAH
            'val': '#2196f3',      # Blu per VAL
            'large_buy': '#00e676', # Verde brillante per large buy
            'large_sell': '#ff5722', # Rosso brillante per large sell
            'volume_high': '#1a237e', # Volume alto
            'volume_low': '#e8eaf6'   # Volume basso
        }
    
    def create_orderflow_chart(self, 
                              symbol: str,
                              candles_data: pd.DataFrame,
                              volume_profile: VolumeProfileMetrics,
                              large_orders: List[LargeOrder],
                              signals: List[OrderFlowSignal],
                              microstructure: Optional[MarketMicrostructure] = None) -> go.Figure:
        """
        Crea grafico completo orderflow
        
        Args:
            symbol: Simbolo trading
            candles_data: DataFrame con OHLCV data
            volume_profile: Metriche volume profile
            large_orders: Lista ordini grossi
            signals: Segnali orderflow
            microstructure: Analisi microstruttura
            
        Returns:
            Figure Plotly interattiva
        """
        
        # Crea subplot con volume profile laterale
        fig = make_subplots(
            rows=2, cols=2,
            row_heights=[0.8, 0.2],
            column_widths=[0.8, 0.2],
            specs=[[{"secondary_y": True}, {"type": "scatter"}],
                   [{"colspan": 2}, None]],
            subplot_titles=(f'{symbol} - Orderflow Analysis', 'Volume Profile', 'Volume & Signals'),
            horizontal_spacing=0.02,
            vertical_spacing=0.05
        )
        
        # 1. MAIN CHART - Candlesticks + Large Orders + Levels
        if not candles_data.empty:
            self._add_candlesticks(fig, candles_data, row=1, col=1)
        
        # 2. Volume Profile laterale
        self._add_volume_profile_chart(fig, volume_profile, row=1, col=2)
        
        # 3. Large Orders (bolle)
        self._add_large_orders_bubbles(fig, large_orders, row=1, col=1)
        
        # 4. POC/VAH/VAL Lines
        self._add_profile_levels(fig, volume_profile, row=1, col=1)
        
        # 5. Signals annotations
        self._add_signals_annotations(fig, signals, row=1, col=1)
        
        # 6. Volume chart in basso
        if not candles_data.empty:
            self._add_volume_bars(fig, candles_data, row=2, col=1)
        
        # 7. Microstructure info
        if microstructure:
            self._add_microstructure_info(fig, microstructure)
        
        # Layout styling
        self._style_chart_layout(fig, symbol)
        
        return fig
    
    def _add_candlesticks(self, fig: go.Figure, candles_data: pd.DataFrame, row: int, col: int):
        """Aggiunge candlesticks al grafico"""
        fig.add_trace(
            go.Candlestick(
                x=candles_data['timestamp'],
                open=candles_data['open'],
                high=candles_data['high'],
                low=candles_data['low'],
                close=candles_data['close'],
                name='Price',
                increasing_line_color=self.colors['buy'],
                decreasing_line_color=self.colors['sell'],
                showlegend=False
            ),
            row=row, col=col
        )
    
    def _add_volume_profile_chart(self, fig: go.Figure, volume_profile: VolumeProfileMetrics, row: int, col: int):
        """Aggiunge volume profile laterale"""
        if not volume_profile.levels:
            return
        
        prices = [level.price for level in volume_profile.levels]
        volumes = [level.volume for level in volume_profile.levels]
        deltas = [level.delta for level in volume_profile.levels]
        
        # Volume profile bars (orizzontali)
        fig.add_trace(
            go.Bar(
                y=prices,
                x=volumes,
                orientation='h',
                name='Volume Profile',
                marker=dict(
                    color=deltas,
                    colorscale='RdYlGn',
                    colorbar=dict(title="Delta", x=1.1),
                    line=dict(width=0.5)
                ),
                hovertemplate='<b>Price: $%{y:.2f}</b><br>' +
                             'Volume: %{x:.2f}<br>' +
                             'Delta: %{marker.color:.2f}<br>' +
                             '<extra></extra>',
                showlegend=False
            ),
            row=row, col=col
        )
    
    def _add_large_orders_bubbles(self, fig: go.Figure, large_orders: List[LargeOrder], row: int, col: int):
        """Aggiunge bolle per ordini grossi"""
        if not large_orders:
            return
        
        # Separa buy e sell orders
        buy_orders = [o for o in large_orders if o.side == 'buy']
        sell_orders = [o for o in large_orders if o.side == 'sell']
        
        # Buy orders (bolle verdi)
        if buy_orders:
            fig.add_trace(
                go.Scatter(
                    x=[o.timestamp for o in buy_orders],
                    y=[o.price for o in buy_orders],
                    mode='markers',
                    name='Large Buy Orders',
                    marker=dict(
                        size=[min(50, max(10, o.volume * 5)) for o in buy_orders],
                        color=self.colors['large_buy'],
                        opacity=0.7,
                        line=dict(width=2, color='white'),
                        sizemode='diameter'
                    ),
                    hovertemplate='<b>🐋 Large BUY Order</b><br>' +
                                 'Price: $%{y:.2f}<br>' +
                                 'Volume: %{text:.4f}<br>' +
                                 'Impact: %{customdata:.1f}%<br>' +
                                 '<extra></extra>',
                    text=[o.volume for o in buy_orders],
                    customdata=[o.impact_score for o in buy_orders]
                ),
                row=row, col=col
            )
        
        # Sell orders (bolle rosse)
        if sell_orders:
            fig.add_trace(
                go.Scatter(
                    x=[o.timestamp for o in sell_orders],
                    y=[o.price for o in sell_orders],
                    mode='markers',
                    name='Large Sell Orders',
                    marker=dict(
                        size=[min(50, max(10, o.volume * 5)) for o in sell_orders],
                        color=self.colors['large_sell'],
                        opacity=0.7,
                        line=dict(width=2, color='white'),
                        sizemode='diameter'
                    ),
                    hovertemplate='<b>🐋 Large SELL Order</b><br>' +
                                 'Price: $%{y:.2f}<br>' +
                                 'Volume: %{text:.4f}<br>' +
                                 'Impact: %{customdata:.1f}%<br>' +
                                 '<extra></extra>',
                    text=[o.volume for o in sell_orders],
                    customdata=[o.impact_score for o in sell_orders]
                ),
                row=row, col=col
            )
    
    def _add_profile_levels(self, fig: go.Figure, volume_profile: VolumeProfileMetrics, row: int, col: int):
        """Aggiunge linee POC, VAH, VAL"""
        if not volume_profile.levels:
            return
        
        # POC Line (Point of Control)
        fig.add_hline(
            y=volume_profile.poc_price,
            line=dict(color=self.colors['poc'], width=3, dash='solid'),
            annotation_text=f"POC ${volume_profile.poc_price:.2f}",
            annotation_position="top right",
            row=row, col=col
        )
        
        # VAH Line (Value Area High)
        fig.add_hline(
            y=volume_profile.vah_price,
            line=dict(color=self.colors['vah'], width=2, dash='dash'),
            annotation_text=f"VAH ${volume_profile.vah_price:.2f}",
            annotation_position="top right",
            row=row, col=col
        )
        
        # VAL Line (Value Area Low)
        fig.add_hline(
            y=volume_profile.val_price,
            line=dict(color=self.colors['val'], width=2, dash='dash'),
            annotation_text=f"VAL ${volume_profile.val_price:.2f}",
            annotation_position="bottom right",
            row=row, col=col
        )
        
        # Value Area (zona tra VAH e VAL)
        fig.add_hrect(
            y0=volume_profile.val_price,
            y1=volume_profile.vah_price,
            fillcolor=self.colors['vah'],
            opacity=0.1,
            line_width=0,
            row=row, col=col
        )
    
    def _add_signals_annotations(self, fig: go.Figure, signals: List[OrderFlowSignal], row: int, col: int):
        """Aggiunge annotazioni per segnali"""
        for signal in signals:
            icon = {
                'accumulation': '📈',
                'distribution': '📉', 
                'breakout': '🚀',
                'absorption': '🌊'
            }.get(signal.signal_type, '📊')
            
            color = {
                'accumulation': 'green',
                'distribution': 'red',
                'breakout': 'blue',
                'absorption': 'orange'
            }.get(signal.signal_type, 'black')
            
            fig.add_annotation(
                x=signal.timestamp,
                y=signal.price_level,
                text=f"{icon} {signal.signal_type.title()}<br>{signal.strength:.0f}%",
                showarrow=True,
                arrowhead=2,
                arrowcolor=color,
                bgcolor=color,
                bordercolor=color,
                font=dict(color='white', size=10),
                row=row, col=col
            )
    
    def _add_volume_bars(self, fig: go.Figure, candles_data: pd.DataFrame, row: int, col: int):
        """Aggiunge barre volume in basso"""
        colors = [
            self.colors['buy'] if close >= open_price else self.colors['sell']
            for close, open_price in zip(candles_data['close'], candles_data['open'])
        ]
        
        fig.add_trace(
            go.Bar(
                x=candles_data['timestamp'],
                y=candles_data['volume'],
                name='Volume',
                marker=dict(color=colors, opacity=0.7),
                showlegend=False,
                hovertemplate='<b>Volume</b><br>' +
                             'Time: %{x}<br>' +
                             'Volume: %{y:.2f}<br>' +
                             '<extra></extra>'
            ),
            row=row, col=col
        )
    
    def _add_microstructure_info(self, fig: go.Figure, microstructure: MarketMicrostructure):
        """Aggiunge informazioni microstruttura"""
        info_text = f"""
        <b>Market Microstructure</b><br>
        Spread: ${microstructure.bid_ask_spread:.4f} ({microstructure.spread_percentage:.3f}%)<br>
        Depth Imbalance: {microstructure.depth_imbalance:.3f}<br>
        Buy Pressure: {microstructure.buy_pressure:.1%}<br>
        Sell Pressure: {microstructure.sell_pressure:.1%}<br>
        Absorption: {'🟢 YES' if microstructure.absorption_detected else '🔴 NO'}<br>
        Hidden Liquidity: {microstructure.hidden_liquidity_estimate:.2f}
        """
        
        fig.add_annotation(
            text=info_text,
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="black",
            font=dict(size=10)
        )
    
    def _style_chart_layout(self, fig: go.Figure, symbol: str):
        """Styling del layout"""
        fig.update_layout(
            title={
                'text': f'<b>{symbol} - Real-Time Orderflow Analysis</b>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            height=self.chart_height,
            template='plotly_dark',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=150, t=80, b=50)
        )
        
        # Remove x-axis labels from top charts
        fig.update_xaxes(showticklabels=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, row=1, col=2)
        
        # Style axes
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=2)
        fig.update_xaxes(title_text="Volume", row=1, col=2)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_xaxes(title_text="Time", row=2, col=1)
    
    def create_heatmap_chart(self, volume_profile: VolumeProfileMetrics, symbol: str) -> go.Figure:
        """Crea heatmap volume per price level"""
        if not volume_profile.levels:
            return go.Figure()
        
        # Prepara dati per heatmap
        prices = [level.price for level in volume_profile.levels]
        buy_volumes = [level.buy_volume for level in volume_profile.levels]
        sell_volumes = [level.sell_volume for level in volume_profile.levels]
        
        # Crea matrice per heatmap
        heatmap_data = []
        labels = []
        
        for i, level in enumerate(volume_profile.levels):
            heatmap_data.append([level.buy_volume, level.sell_volume])
            labels.append(f"${level.price:.2f}")
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=['Buy Volume', 'Sell Volume'],
            y=labels,
            colorscale='RdYlGn',
            hoverongaps=False,
            hovertemplate='<b>%{y}</b><br>' +
                         '%{x}: %{z:.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=f'<b>{symbol} - Volume Heatmap</b>',
            height=600,
            template='plotly_dark'
        )
        
        return fig
    
    def create_live_dashboard_layout(self) -> str:
        """
        Crea layout HTML per dashboard live
        
        Returns:
            HTML string per dashboard
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Bot - Live Orderflow Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body { margin: 0; padding: 10px; background-color: #1e1e1e; color: white; font-family: Arial; }
                .header { text-align: center; margin-bottom: 20px; }
                .charts-container { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
                .chart { border: 1px solid #333; border-radius: 8px; padding: 10px; }
                .stats { background-color: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Live Orderflow Analysis Dashboard</h1>
                <div id="last-update">Last Update: --</div>
            </div>
            
            <div class="stats">
                <div id="market-stats">Loading market stats...</div>
            </div>
            
            <div class="charts-container">
                <div class="chart">
                    <div id="main-chart"></div>
                </div>
                <div class="chart">
                    <div id="heatmap-chart"></div>
                </div>
            </div>
            
            <script>
                // Auto-refresh ogni 5 secondi
                setInterval(function() {
                    updateCharts();
                }, 5000);
                
                function updateCharts() {
                    // Qui andrà la logica per aggiornare i grafici
                    document.getElementById('last-update').innerHTML = 
                        'Last Update: ' + new Date().toLocaleTimeString();
                }
                
                // Inizializza
                updateCharts();
            </script>
        </body>
        </html>
        """
        return html_template


def test_chart_renderer():
    """Test del Chart Renderer"""
    print("🎨 Chart Renderer Test")
    
    renderer = ChartRenderer()
    
    # Dati di test per candlesticks
    dates = pd.date_range(start='2025-01-01', periods=100, freq='5min')
    base_price = 50000
    
    # Genera candlesticks realistici
    candles_data = []
    current_price = base_price
    
    for date in dates:
        # Random walk per prezzo
        change = np.random.normal(0, 20)
        open_price = current_price
        close_price = current_price + change
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 10))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 10))
        volume = np.random.exponential(100)
        
        candles_data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price, 
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        current_price = close_price
    
    candles_df = pd.DataFrame(candles_data)
    
    # Test dati (riusi delle classi precedenti)
    from .volume_profile import VolumeProfileCalculator, VolumeProfileLevel, VolumeProfileMetrics
    from .order_flow import LargeOrder, OrderFlowSignal
    
    # Volume profile di test
    levels = []
    for i in range(50):
        price = base_price + (i - 25) * 10
        volume = np.random.exponential(50)
        buy_vol = volume * np.random.uniform(0.3, 0.7)
        sell_vol = volume - buy_vol
        
        levels.append(VolumeProfileLevel(
            price=price,
            volume=volume,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            delta=buy_vol - sell_vol
        ))
    
    volume_profile = VolumeProfileMetrics(
        poc_price=base_price,
        poc_volume=max(levels, key=lambda x: x.volume).volume,
        vah_price=base_price + 100,
        val_price=base_price - 100,
        value_area_volume=sum(l.volume for l in levels) * 0.7,
        total_volume=sum(l.volume for l in levels),
        levels=levels
    )
    
    # Large orders di test
    large_orders = []
    for i in range(10):
        large_orders.append(LargeOrder(
            symbol='BTCUSDT',
            side=np.random.choice(['buy', 'sell']),
            price=base_price + np.random.uniform(-50, 50),
            volume=np.random.uniform(2, 10),
            value=0,  # Sarà calcolato
            timestamp=dates[np.random.randint(0, len(dates))],
            source='test',
            impact_score=np.random.uniform(20, 80)
        ))
    
    # Signals di test
    signals = [
        OrderFlowSignal(
            symbol='BTCUSDT',
            signal_type='accumulation',
            strength=75.0,
            price_level=base_price + 20,
            description="Strong accumulation detected",
            timestamp=dates[30],
            supporting_data={}
        )
    ]
    
    # Crea grafico principale
    print("📊 Creando grafico orderflow...")
    fig = renderer.create_orderflow_chart(
        'BTCUSDT',
        candles_df,
        volume_profile,
        large_orders,
        signals
    )
    
    # Salva grafico (per test)
    chart_file = "test_orderflow_chart.html"
    fig.write_html(chart_file)
    print(f"✅ Grafico salvato: {chart_file}")
    
    # Crea heatmap
    print("🔥 Creando heatmap...")
    heatmap_fig = renderer.create_heatmap_chart(volume_profile, 'BTCUSDT')
    heatmap_file = "test_heatmap.html"
    heatmap_fig.write_html(heatmap_file)
    print(f"✅ Heatmap salvato: {heatmap_file}")
    
    # Crea dashboard layout
    print("🖥️ Creando dashboard layout...")
    dashboard_html = renderer.create_live_dashboard_layout()
    dashboard_file = "live_dashboard.html"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    print(f"✅ Dashboard salvato: {dashboard_file}")
    
    print("🎨 Chart Renderer test completato!")
    print(f"📁 Files generati:")
    print(f"   - {chart_file}")
    print(f"   - {heatmap_file}")  
    print(f"   - {dashboard_file}")

if __name__ == "__main__":
    test_chart_renderer()