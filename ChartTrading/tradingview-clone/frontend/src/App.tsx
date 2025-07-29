import React, { useState, useEffect } from 'react';
import './App.css';

interface KlineData {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartData {
  time: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  formattedTime: string;
}

interface BybitApiResponse {
  success: boolean;
  data: KlineData[];
  symbol: string;
  interval: string;
  count: number;
  error?: string;
}

// Helper function per formattare il tempo in base al timeframe
const formatTimeByInterval = (date: Date, interval: string): string => {
  switch (interval) {
    case 'D':
      return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
    case '240':
      return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) + ' ' + 
             date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    case '60':
      return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) + ' ' + 
             date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    case '15':
      return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    case '5':
      return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    case '1':
      return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    default:
      return date.toLocaleDateString('it-IT');
  }
};

// Helper function per ottenere il numero di candele in base al timeframe
const getLimitByInterval = (interval: string): number => {
  switch (interval) {
    case 'D': return 100; // 100 giorni
    case '240': return 168; // 1 mese di 4h (24*7)
    case '60': return 168; // 1 settimana di 1h (24*7)  
    case '15': return 96; // 1 giorno di 15m (24*4)
    case '5': return 288; // 1 giorno di 5m (24*12)
    case '1': return 240; // 4 ore di 1m (4*60)
    default: return 100;
  }
};

const App: React.FC = () => {
  const [btcPrice, setBtcPrice] = useState<number | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [selectedInterval, setSelectedInterval] = useState('D');
  const [selectedProvider, setSelectedProvider] = useState<'bybit' | 'coingecko' | 'coincap'>('coincap');
  const [chartRange, setChartRange] = useState({ start: 0, end: 50 }); // Per zoom/pan
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    fetchData();
  }, [selectedSymbol, selectedInterval, selectedProvider]);

  const fetchData = async () => {
    if (selectedProvider === 'coingecko') {
      await fetchCoinGeckoData();
    } else if (selectedProvider === 'coincap') {
      await fetchCoinCapData();
    } else {
      await fetchBybitData();
    }
  };

  const fetchCoinGeckoData = async () => {
    try {
      setIsLoading(true);
      
      // Test connessione backend
      const testResponse = await fetch('http://localhost:5000/api/test');
      if (!testResponse.ok) {
        throw new Error('Backend non disponibile');
      }

      // Recupera dati da CoinGecko tramite il nostro backend
      const limit = getLimitByInterval(selectedInterval);
      const response = await fetch(
        `http://localhost:5000/api/coingecko/kline?symbol=${selectedSymbol}&interval=${selectedInterval}&limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error('Errore nel recupero dati CoinGecko');
      }

      const result: BybitApiResponse = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Errore API CoinGecko');
      }
      
      // Converte i dati in formato chart
      const chartData: ChartData[] = result.data.map((kline: KlineData) => {
        const date = new Date(kline.openTime);
        return {
          time: date.toLocaleDateString(),
          timestamp: kline.openTime,
          open: kline.open,
          high: kline.high,
          low: kline.low,
          close: kline.close,
          volume: kline.volume,
          formattedTime: formatTimeByInterval(date, selectedInterval)
        };
      });

      setChartData(chartData);
      setBtcPrice(chartData[chartData.length - 1]?.close || 0);
      setLastUpdate(new Date());
      setError(null);
      
    } catch (err) {
      console.error('Errore CoinGecko:', err);
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchBybitData = async () => {
    try {
      setIsLoading(true);
      
      // Test connessione backend
      const testResponse = await fetch('http://localhost:5000/api/test');
      if (!testResponse.ok) {
        throw new Error('Backend non disponibile');
      }

      // Recupera dati da Bybit tramite il nostro backend
      const limit = getLimitByInterval(selectedInterval);
      const response = await fetch(
        `http://localhost:5000/api/bybit/kline?symbol=${selectedSymbol}&interval=${selectedInterval}&limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error('Errore nel recupero dati Bybit');
      }

      const result: BybitApiResponse = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Errore API Bybit');
      }
      
      // Converte i dati di Bybit in formato chart
      const chartData: ChartData[] = result.data.map((kline: KlineData) => {
        const date = new Date(kline.openTime);
        return {
          time: date.toLocaleDateString(),
          timestamp: kline.openTime,
          open: kline.open,
          high: kline.high,
          low: kline.low,
          close: kline.close,
          volume: kline.volume,
          formattedTime: formatTimeByInterval(date, selectedInterval)
        };
      });

      setChartData(chartData);
      setBtcPrice(chartData[chartData.length - 1]?.close || 0);
      setLastUpdate(new Date());
      setError(null);
      
    } catch (err) {
      console.error('Errore:', err);
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCoinCapData = async () => {
    try {
      setIsLoading(true);
      
      // Test connessione backend
      const testResponse = await fetch('http://localhost:5000/api/test');
      if (!testResponse.ok) {
        throw new Error('Backend non disponibile');
      }

      const limit = 1000; // Binance può gestire grandi dataset

      // Recupera dati da Binance tramite il nostro backend
      const response = await fetch(
        `http://localhost:5000/api/coincap/kline?symbol=${selectedSymbol}&interval=${selectedInterval}&limit=${limit}`
      );

      if (!response.ok) {
        throw new Error('Errore nel recupero dati Binance');
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Errore API Binance');
      }

      console.log(`✅ Binance: Retrieved ${result.data.length} candlesticks`);

      // Convertiamo i dati per il grafico - assicuriamoci che i valori siano numeri
      const chartData: ChartData[] = result.data.map((kline: any) => {
        const date = new Date(kline.openTime);
        return {
          time: date.toLocaleDateString(),
          timestamp: kline.openTime,
          open: parseFloat(kline.open) || 0,
          high: parseFloat(kline.high) || 0,
          low: parseFloat(kline.low) || 0,
          close: parseFloat(kline.close) || 0,
          volume: parseFloat(kline.volume) || 0,
          formattedTime: formatTimeByInterval(date, selectedInterval)
        };
      });

      setChartData(chartData);
      setBtcPrice(chartData[chartData.length - 1]?.close || 0);
      setLastUpdate(new Date());
      setError(null);
      
    } catch (err) {
      console.error('Errore Binance:', err);
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
    } finally {
      setIsLoading(false);
    }
  };

  const calculateChange = () => {
    if (chartData.length < 2) return { value: 0, percentage: 0 };
    
    const current = chartData[chartData.length - 1].close;
    const previous = chartData[chartData.length - 2].close;
    const change = current - previous;
    const percentage = (change / previous) * 100;
    
    return { value: change, percentage };
  };

  const change = calculateChange();

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚀 TradingView Clone</h1>
        <div className="status">
          {isLoading ? '🔄 Loading...' : error ? '❌ Error' : '✅ Ready'}
        </div>
      </header>
      
      <main className="app-main">
        <div className="dashboard">
          <div className="price-card">
            <h2>{selectedSymbol} via {
              selectedProvider === 'coincap' ? 'Binance (100% Free)' : 
              selectedProvider === 'coingecko' ? 'CoinGecko (Free)' : 'Bybit'
            }</h2>
            <div className="symbol-selector">
              <select 
                value={selectedSymbol} 
                onChange={(e) => setSelectedSymbol(e.target.value)}
                disabled={isLoading}
              >
                <option value="BTCUSDT">Bitcoin (BTC/USDT)</option>
                <option value="ETHUSDT">Ethereum (ETH/USDT)</option>
                <option value="ADAUSDT">Cardano (ADA/USDT)</option>
                <option value="BNBUSDT">Binance Coin (BNB/USDT)</option>
                <option value="XRPUSDT">Ripple (XRP/USDT)</option>
                <option value="SOLUSDT">Solana (SOL/USDT)</option>
              </select>
              <select 
                value={selectedInterval} 
                onChange={(e) => setSelectedInterval(e.target.value)}
                disabled={isLoading}
              >
                <option value="D">📅 Daily (1D)</option>
                <option value="240">🕐 4 Hours (4H)</option>
                <option value="60">⏰ 1 Hour (1H)</option>
                <option value="15">⚡ 15 Minutes (15m)</option>
                <option value="5">🚀 5 Minutes (5m)</option>
                <option value="1">💨 1 Minute (1m)</option>
              </select>
              <select 
                value={selectedProvider} 
                onChange={(e) => setSelectedProvider(e.target.value as 'bybit' | 'coingecko' | 'coincap')}
                disabled={isLoading}
              >
                <option value="coincap">� Binance (100% Free)</option>
                <option value="coingecko">🆓 CoinGecko (Free)</option>
                <option value="bybit">⚡ Bybit (API Key)</option>
              </select>
            </div>
            <div className="price">
              ${btcPrice?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'Loading...'}
            </div>
            <div className={`change ${change.percentage >= 0 ? 'positive' : 'negative'}`}>
              {change.percentage >= 0 ? '+' : ''}{change.percentage.toFixed(2)}%
              <span className="change-value">
                ({change.percentage >= 0 ? '+' : ''}${change.value.toFixed(2)})
              </span>
            </div>
            <div className="last-update">
              📡 Ultimo aggiornamento: {lastUpdate.toLocaleTimeString('it-IT')}
              <br />
              📊 {chartData.length} candele - Timeframe: {selectedInterval === 'D' ? 'Giornaliero' : 
                selectedInterval === '240' ? '4 Ore' : 
                selectedInterval === '60' ? '1 Ora' : 
                selectedInterval === '15' ? '15 Minuti' :
                selectedInterval === '5' ? '5 Minuti' : '1 Minuto'}
            </div>
          </div>

          <div className="chart-container">
            <div className="chart-header">
              <h3>📊 {selectedSymbol} Chart - {selectedInterval === 'D' ? 'Daily' : 
                selectedInterval === '240' ? '4H' : 
                selectedInterval === '60' ? '1H' : 
                selectedInterval === '15' ? '15m' :
                selectedInterval === '5' ? '5m' : '1m'} - {
                  selectedProvider === 'coincap' ? 'Binance' :
                  selectedProvider === 'coingecko' ? 'CoinGecko' : 'Bybit'
                } Data</h3>
              <div className="chart-controls">
                <button onClick={fetchData} className="refresh-btn" disabled={isLoading}>
                  🔄 Aggiorna
                </button>
                <div className="zoom-controls">
                  <button onClick={() => setChartRange(prev => ({ ...prev, end: Math.min(prev.end + 20, chartData.length) }))}>
                    🔍 Zoom Out
                  </button>
                  <button onClick={() => setChartRange(prev => ({ ...prev, end: Math.max(prev.end - 20, 20) }))}>
                    🔎 Zoom In
                  </button>
                </div>
              </div>
            </div>
            
            {error ? (
              <div className="error-message">
                ❌ Errore: {error}
              </div>
            ) : isLoading ? (
              <div className="loading">🔄 Caricamento dati...</div>
            ) : (
              <div className="chart-wrapper">
                <div className="chart-area">
                  <CandlestickChart 
                    data={chartData} 
                    range={chartRange}
                    interval={selectedInterval}
                  />
                </div>
                <div className="volume-chart">
                  <VolumeChart 
                    data={chartData.slice(chartRange.start, chartRange.end)} 
                    interval={selectedInterval}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="stats-panel">
            <h3>📈 Statistiche</h3>
            <div className="stats-grid">
              <div className="stat">
                <label>Massimo 30gg:</label>
                <span>${Math.max(...chartData.map(d => d.high)).toLocaleString()}</span>
              </div>
              <div className="stat">
                <label>Minimo 30gg:</label>
                <span>${Math.min(...chartData.map(d => d.low)).toLocaleString()}</span>
              </div>
              <div className="stat">
                <label>Volume medio:</label>
                <span>{(chartData.reduce((sum, d) => sum + d.volume, 0) / chartData.length / 1000).toFixed(0)}K</span>
              </div>
              <div className="stat">
                <label>Candele:</label>
                <span>{chartData.length}</span>
              </div>
            </div>

            <div className="features">
              <h4>🎯 Funzionalità</h4>
              <ul>
                <li>✅ Dati real-time {
                  selectedProvider === 'coincap' ? 'Binance (100% Free)' :
                  selectedProvider === 'coingecko' ? 'CoinGecko (Free)' : 'Bybit (API)'
                }</li>
                <li>✅ Grafico a candele</li>
                <li>✅ Selezione simbolo</li>
                <li>✅ Timeframe multipli</li>
                <li>✅ Selezione Data Provider</li>
                <li>✅ Backend API Multi-source</li>
                <li>🔄 WebSocket live</li>
                <li>🔄 Indicatori tecnici</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// Componente grafico a candele professionale
const CandlestickChart: React.FC<{ 
  data: ChartData[], 
  range?: { start: number, end: number },
  interval?: string 
}> = ({ data, range, interval }) => {
  if (!data.length) return <div>Nessun dato disponibile</div>;

  // Use range if provided, otherwise show all data
  const displayData = range ? data.slice(range.start, range.end) : data;
  
  const maxPrice = Math.max(...displayData.map(d => d.high));
  const minPrice = Math.min(...displayData.map(d => d.low));
  const priceRange = maxPrice - minPrice;

  return (
    <div className="candlestick-chart">
      <div className="price-scale">
        <div className="price-label">${maxPrice.toFixed(2)}</div>
        <div className="price-label">${((maxPrice + minPrice) / 2).toFixed(2)}</div>
        <div className="price-label">${minPrice.toFixed(2)}</div>
      </div>
      
      <div className="candles-container">
        {displayData.map((candle, index) => {
          const isGreen = candle.close > candle.open;
          const bodyTop = Math.max(candle.open, candle.close);
          const bodyBottom = Math.min(candle.open, candle.close);
          
          const highY = ((maxPrice - candle.high) / priceRange) * 100;
          const lowY = ((maxPrice - candle.low) / priceRange) * 100;
          const bodyTopY = ((maxPrice - bodyTop) / priceRange) * 100;
          const bodyBottomY = ((maxPrice - bodyBottom) / priceRange) * 100;
          
          return (
            <div 
              key={index} 
              className="candle-wrapper" 
              title={`${candle.formattedTime}\n💰 O: $${candle.open.toFixed(2)}\n📈 H: $${candle.high.toFixed(2)}\n📉 L: $${candle.low.toFixed(2)}\n💵 C: $${candle.close.toFixed(2)}\n📊 V: ${(candle.volume/1000).toFixed(0)}K`}
            >
              {/* Wick superiore */}
              <div 
                className="wick"
                style={{
                  top: `${highY}%`,
                  height: `${Math.max(bodyTopY - highY, 0.5)}%`
                }}
              />
              
              {/* Body della candela */}
              <div 
                className={`candle-body ${isGreen ? 'green' : 'red'}`}
                style={{
                  top: `${bodyTopY}%`,
                  height: `${Math.max(bodyBottomY - bodyTopY, 1)}%`
                }}
              />
              
              {/* Wick inferiore */}
              <div 
                className="wick"
                style={{
                  top: `${bodyBottomY}%`,
                  height: `${Math.max(lowY - bodyBottomY, 0.5)}%`
                }}
              />
              
              {/* Time label ogni poche candele */}
              {index % Math.ceil(displayData.length / 8) === 0 && (
                <div className="time-label">
                  {candle.formattedTime}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Componente grafico volume
const VolumeChart: React.FC<{ 
  data: ChartData[], 
  interval?: string 
}> = ({ data, interval }) => {
  if (!data.length) return null;

  const maxVolume = Math.max(...data.map(d => d.volume));
  
  return (
    <div className="volume-chart">
      <div className="volume-header">
        <span>📊 Volume</span>
        <span>Max: {(maxVolume/1000).toFixed(0)}K</span>
      </div>
      <div className="volume-bars">
        {data.map((candle, index) => {
          const isGreen = candle.close > candle.open;
          const height = (candle.volume / maxVolume) * 100;
          
          return (
            <div 
              key={index} 
              className={`volume-bar ${isGreen ? 'green' : 'red'}`}
              style={{ height: `${height}%` }}
              title={`Volume: ${(candle.volume/1000).toFixed(0)}K`}
            />
          );
        })}
      </div>
    </div>
  );
};

export default App;