import axios from 'axios';

// CoinCap API interfaces
interface CoinCapAsset {
  id: string;
  rank: string;
  symbol: string;
  name: string;
  supply: string;
  maxSupply: string;
  marketCapUsd: string;
  volumeUsd24Hr: string;
  priceUsd: string;
  changePercent24Hr: string;
}

interface CoinCapHistoryData {
  priceUsd: string;
  time: number;
  circulatingSupply: string;
  date: string;
}

interface Kline {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export class CoinCapService {
  private baseUrl = 'https://api.coincap.io/v2';
  private rateLimitDelay = 200; // CoinCap è molto generoso, 200ms tra chiamate

  // Mapping simboli trading a CoinCap asset IDs
  private symbolToAssetId: { [key: string]: string } = {
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    'ADAUSDT': 'cardano',
    'BNBUSDT': 'binance-coin',
    'XRPUSDT': 'xrp',
    'SOLUSDT': 'solana',
    'DOTUSDT': 'polkadot',
    'AVAXUSDT': 'avalanche',
    'LINKUSDT': 'chainlink',
    'LTCUSDT': 'litecoin',
    'MATICUSDT': 'polygon',
    'UNIUSDT': 'uniswap',
    'ATOMUSDT': 'cosmos',
    'XLMUSDT': 'stellar',
    'VETUSDT': 'vechain'
  };

  // Mapping interval to milliseconds for CoinCap
  private intervalToMs: { [key: string]: number } = {
    '1': 60000,      // 1 minuto
    '5': 300000,     // 5 minuti
    '15': 900000,    // 15 minuti
    '60': 3600000,   // 1 ora
    '240': 14400000, // 4 ore
    'D': 86400000    // 1 giorno
  };

  async getKlineData(
    symbol: string = 'BTCUSDT',
    interval: string = 'D',
    limit: number = 1000
  ): Promise<Kline[]> {
    try {
      const assetId = this.symbolToAssetId[symbol];
      if (!assetId) {
        throw new Error(`Symbol ${symbol} not supported by CoinCap`);
      }

      console.log(`🚀 Fetching CoinCap data for ${symbol} (${assetId}), interval: ${interval}`);

      // CoinCap fornisce dati storici granulari - scegliamo la strategia migliore
      if (interval === 'D') {
        return await this.getDailyData(assetId, limit);
      } else {
        return await this.getIntraDayData(assetId, interval, limit);
      }

    } catch (error) {
      console.error('❌ CoinCap API error:', error);
      throw new Error(`Failed to fetch data from CoinCap: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private async getDailyData(assetId: string, limit: number): Promise<Kline[]> {
    // CoinCap API: usiamo periodi più limitati per evitare errori 404
    const endTime = Date.now();
    const startTime = endTime - (90 * 24 * 60 * 60 * 1000); // Solo 90 giorni (3 mesi)
    
    console.log(`📅 Fetching 90 days of daily data for ${assetId} from CoinCap`);

    const response = await axios.get(`${this.baseUrl}/assets/${assetId}/history`, {
      params: {
        interval: 'd1', // Daily interval
        start: startTime,
        end: endTime
      },
      timeout: 10000
    });

    if (!response.data.data || !Array.isArray(response.data.data)) {
      throw new Error('Invalid response format from CoinCap');
    }

    const historyData: CoinCapHistoryData[] = response.data.data;
    console.log(`📊 Processing ${historyData.length} daily data points from CoinCap`);

    // Convertiamo i dati in formato OHLC
    const klines: Kline[] = [];
    
    for (let i = 0; i < historyData.length - 1; i++) {
      const current = historyData[i];
      const next = historyData[i + 1];
      
      const price = parseFloat(current.priceUsd);
      const nextPrice = parseFloat(next.priceUsd);
      const volume = parseFloat(current.circulatingSupply) * price; // Estimate volume
      
      klines.push({
        openTime: current.time,
        open: price,
        high: Math.max(price, nextPrice),
        low: Math.min(price, nextPrice),
        close: nextPrice,
        volume: volume || 0
      });
    }

    return klines;
  }

  private async getIntraDayData(assetId: string, interval: string, limit: number): Promise<Kline[]> {
    // Per intraday, usiamo intervalli CoinCap più conservativi
    let coinCapInterval = 'h1'; // Default 1 ora
    let daysPeriod = 7; // Default 1 settimana
    
    switch (interval) {
      case '1':
        coinCapInterval = 'm1';
        daysPeriod = 1; // Solo 1 giorno per minutely
        break;
      case '5':
        coinCapInterval = 'm5';
        daysPeriod = 1; // Solo 1 giorno per 5min
        break;
      case '15':
        coinCapInterval = 'm15';
        daysPeriod = 3; // 3 giorni per 15min
        break;
      case '60':
        coinCapInterval = 'h1';
        daysPeriod = 7; // 1 settimana per hourly
        break;
    }

    const endTime = Date.now();
    const startTime = endTime - (daysPeriod * 24 * 60 * 60 * 1000);

    console.log(`⏰ Fetching ${daysPeriod} days of ${coinCapInterval} data for ${assetId}`);

    const response = await axios.get(`${this.baseUrl}/assets/${assetId}/history`, {
      params: {
        interval: coinCapInterval,
        start: startTime,
        end: endTime
      },
      timeout: 10000
    });

    if (!response.data.data || !Array.isArray(response.data.data)) {
      throw new Error('Invalid intraday response format from CoinCap');
    }

    const historyData: CoinCapHistoryData[] = response.data.data;
    console.log(`📊 Processing ${historyData.length} intraday data points`);

    // Convertiamo in formato OHLC
    const klines: Kline[] = [];
    
    for (let i = 0; i < historyData.length - 1; i++) {
      const current = historyData[i];
      const next = historyData[i + 1];
      
      const price = parseFloat(current.priceUsd);
      const nextPrice = parseFloat(next.priceUsd);
      const volume = parseFloat(current.circulatingSupply) * price; // Estimate volume
      
      klines.push({
        openTime: current.time,
        open: price,
        high: Math.max(price, nextPrice),
        low: Math.min(price, nextPrice),
        close: nextPrice,
        volume: volume || 0
      });
    }

    return klines;
  }

  async getSupportedSymbols(): Promise<string[]> {
    return Object.keys(this.symbolToAssetId);
  }

  async getCoinInfo(symbol: string) {
    const assetId = this.symbolToAssetId[symbol];
    if (!assetId) {
      throw new Error(`Symbol ${symbol} not supported`);
    }

    const response = await axios.get(`${this.baseUrl}/assets/${assetId}`, {
      timeout: 10000
    });

    const asset: CoinCapAsset = response.data.data;

    return {
      id: asset.id,
      name: asset.name,
      symbol: asset.symbol.toUpperCase(),
      current_price: parseFloat(asset.priceUsd),
      market_cap: parseFloat(asset.marketCapUsd),
      price_change_24h: parseFloat(asset.changePercent24Hr),
      price_change_percentage_24h: parseFloat(asset.changePercent24Hr),
      volume_24h: parseFloat(asset.volumeUsd24Hr)
    };
  }
}

export const coinCapService = new CoinCapService();
