import axios from 'axios';

// CoinGecko API interfaces
interface CoinGeckoOHLC {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CoinGeckoPriceData {
  prices: [number, number][];
  market_caps: [number, number][];
  total_volumes: [number, number][];
}

interface Kline {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export class CoinGeckoService {
  private baseUrl = 'https://api.coingecko.com/api/v3';
  private rateLimitDelay = 1200; // 1.2 secondi tra requests per rispettare rate limit

  // Mapping dei simboli trading ai coin IDs di CoinGecko
  private symbolToCoinId: { [key: string]: string } = {
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    'ADAUSDT': 'cardano',
    'BNBUSDT': 'binancecoin',
    'XRPUSDT': 'ripple',
    'SOLUSDT': 'solana',
    'DOTUSDT': 'polkadot',
    'AVAXUSDT': 'avalanche-2',
    'LINKUSDT': 'chainlink',
    'LTCUSDT': 'litecoin',
    'MATICUSDT': 'matic-network',
    'UNIUSDT': 'uniswap',
    'ATOMUSDT': 'cosmos',
    'XLMUSDT': 'stellar',
    'VETUSDT': 'vechain'
  };

  // Mapping timeframes - Aumentiamo i giorni per avere più dati storici
  private intervalToDays: { [key: string]: number } = {
    '1': 7,      // 1 minuto -> 1 settimana di dati
    '5': 14,     // 5 minuti -> 2 settimane di dati  
    '15': 30,    // 15 minuti -> 1 mese di dati
    '60': 90,    // 1 ora -> 3 mesi di dati
    '240': 365,  // 4 ore -> 1 anno di dati
    'D': 365     // Daily -> 1 anno di dati
  };

  async getKlineData(
    symbol: string = 'BTCUSDT',
    interval: string = 'D',
    limit: number = 100
  ): Promise<Kline[]> {
    try {
      const coinId = this.symbolToCoinId[symbol];
      if (!coinId) {
        throw new Error(`Symbol ${symbol} not supported by CoinGecko`);
      }

      console.log(`📡 Fetching CoinGecko data for ${symbol} (${coinId}), interval: ${interval}`);

      // Per timeframes sotto 1 giorno, usiamo market_chart endpoint
      if (interval === '1' || interval === '5' || interval === '15' || interval === '60') {
        return await this.getIntraDayData(coinId, interval, limit);
      } else {
        // Per daily e sopra, usiamo OHLC endpoint
        return await this.getDailyData(coinId, limit);
      }

    } catch (error) {
      console.error('❌ CoinGecko API error:', error);
      throw new Error(`Failed to fetch data from CoinGecko: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private async getIntraDayData(coinId: string, interval: string, limit: number): Promise<Kline[]> {
    const days = this.intervalToDays[interval] || 1;
    
    const response = await axios.get(`${this.baseUrl}/coins/${coinId}/market_chart`, {
      params: {
        vs_currency: 'usd',
        days: days,
        interval: interval === '1' ? 'minutely' : 'hourly'
      },
      timeout: 10000
    });

    const data: CoinGeckoPriceData = response.data;
    
    if (!data.prices || !data.total_volumes) {
      throw new Error('Invalid response format from CoinGecko');
    }

    // Convertiamo i dati di prezzo in formato OHLC semplificato
    const klines: Kline[] = [];
    const intervalMinutes = this.getIntervalMinutes(interval);
    
    // Processo tutti i dati disponibili, il frontend gestirà il panning
    console.log(`📊 Processing ${data.prices.length} price points for ${interval} interval`);
    
    for (let i = 0; i < data.prices.length - 1; i++) {
      const [timestamp, price] = data.prices[i];
      const [, volume] = data.total_volumes[i] || [0, 0];
      
      // Per intraday, simuliamo OHLC usando i prezzi consecutivi
      const nextPrice = data.prices[i + 1] ? data.prices[i + 1][1] : price;
      
      klines.push({
        openTime: timestamp,
        open: price,
        high: Math.max(price, nextPrice),
        low: Math.min(price, nextPrice),
        close: nextPrice,
        volume: volume || 0
      });
    }

    // Restituiamo tutti i dati, ordinati dal più vecchio al più nuovo
    return klines;
  }

  private async getDailyData(coinId: string, limit: number): Promise<Kline[]> {
    // CoinGecko free API: usiamo 365 giorni (massimo gratuito per OHLC)
    const days = 365; // 1 anno di dati storici gratuiti
    console.log(`📅 Fetching ${days} days of historical data for ${coinId} (CoinGecko Free)`);
    
    const response = await axios.get(`${this.baseUrl}/coins/${coinId}/ohlc`, {
      params: {
        vs_currency: 'usd',
        days: days
      },
      timeout: 15000
    });

    if (!Array.isArray(response.data)) {
      throw new Error('Invalid OHLC response format from CoinGecko');
    }

    // Otteniamo anche i dati di volume
    const volumeResponse = await axios.get(`${this.baseUrl}/coins/${coinId}/market_chart`, {
      params: {
        vs_currency: 'usd',
        days: days
      },
      timeout: 15000
    });

    const volumeData = volumeResponse.data.total_volumes || [];

    console.log(`📊 Processing ${response.data.length} OHLC daily candles`);

    const klines: Kline[] = response.data.map((ohlc: number[], index: number) => {
      const [timestamp, open, high, low, close] = ohlc;
      const volume = volumeData[index] ? volumeData[index][1] : 0;

      return {
        openTime: timestamp,
        open: open,
        high: high,
        low: low,
        close: close,
        volume: volume || 0
      };
    });

    // Restituiamo tutti i dati storici disponibili
    return klines;
  }

  private getIntervalMinutes(interval: string): number {
    switch (interval) {
      case '1': return 1;
      case '5': return 5;
      case '15': return 15;
      case '60': return 60;
      case '240': return 240;
      case 'D': return 1440;
      default: return 60;
    }
  }

  async getSupportedSymbols(): Promise<string[]> {
    return Object.keys(this.symbolToCoinId);
  }

  async getCoinInfo(symbol: string) {
    const coinId = this.symbolToCoinId[symbol];
    if (!coinId) {
      throw new Error(`Symbol ${symbol} not supported`);
    }

    const response = await axios.get(`${this.baseUrl}/coins/${coinId}`, {
      params: {
        localization: false,
        tickers: false,
        market_data: true,
        community_data: false,
        developer_data: false,
        sparkline: false
      },
      timeout: 10000
    });

    return {
      id: response.data.id,
      name: response.data.name,
      symbol: response.data.symbol.toUpperCase(),
      current_price: response.data.market_data.current_price.usd,
      market_cap: response.data.market_data.market_cap.usd,
      price_change_24h: response.data.market_data.price_change_24h,
      price_change_percentage_24h: response.data.market_data.price_change_percentage_24h
    };
  }
}

export const coinGeckoService = new CoinGeckoService();
