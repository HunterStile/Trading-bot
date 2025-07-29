import { Request, Response } from 'express';
import { BinanceService } from '../services/binanceService';

// Tipo Timeframe locale per evitare problemi di import
type Timeframe = '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '6h' | '8h' | '12h' | '1d' | '3d' | '1w' | '1M';

const binanceService = new BinanceService();

export class BinanceController {
  async getKlineData(req: Request, res: Response) {
    try {
      const { symbol = 'BTCUSDT', interval = '1d', limit = 1000 } = req.query;
      console.log(`🟡 Binance API request: ${symbol}, ${interval}, limit: ${limit}`);

      // Converte l'intervallo al formato Binance/Timeframe
      let binanceInterval: Timeframe = '1d';
      
      switch (interval) {
        case 'D': binanceInterval = '1d'; break;
        case '240': binanceInterval = '4h'; break;
        case '60': binanceInterval = '1h'; break;
        case '15': binanceInterval = '15m'; break;
        case '5': binanceInterval = '5m'; break;
        case '1': binanceInterval = '1m'; break;
        default: binanceInterval = '1d';
      }

      const result = await binanceService.getKlines(
        symbol as string,
        binanceInterval,
        parseInt(limit as string) || 1000
      );

      res.json({
        success: true,
        data: result.data,
        message: `Retrieved ${result.data.length} candlesticks from Binance`,
        metadata: {
          symbol: symbol,
          interval: binanceInterval,
          count: result.data.length,
          source: 'Binance Public API (100% Free)'
        }
      });

    } catch (error) {
      console.error('❌ Binance Controller Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: [],
        source: 'Binance Public API (100% Free)'
      });
    }
  }

  async getSupportedSymbols(req: Request, res: Response) {
    try {
      // Lista hardcoded dei simboli più popolari
      const symbols = [
        'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT',
        'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT', 'MATICUSDT', 'UNIUSDT'
      ];
      
      res.json({
        success: true,
        data: symbols,
        message: `Retrieved ${symbols.length} supported symbols from Binance`,
        source: 'Binance Public API (100% Free)'
      });

    } catch (error) {
      console.error('❌ Binance Symbols Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: [],
        source: 'Binance Public API (100% Free)'
      });
    }
  }

  async getCoinInfo(req: Request, res: Response) {
    try {
      const { symbol } = req.params;
      if (!symbol) {
        return res.status(400).json({
          success: false,
          error: 'Symbol parameter is required',
          data: null
        });
      }

      const stats = await binanceService.get24hrStats(symbol.toUpperCase());
      
      res.json({
        success: true,
        data: {
          symbol: stats.symbol,
          current_price: parseFloat(stats.lastPrice),
          price_change_24h: parseFloat(stats.priceChange),
          price_change_percentage_24h: parseFloat(stats.priceChangePercent),
          high_24h: parseFloat(stats.highPrice),
          low_24h: parseFloat(stats.lowPrice),
          volume_24h: parseFloat(stats.volume)
        },
        message: `Retrieved info for ${symbol.toUpperCase()} from Binance`,
        source: 'Binance Public API (100% Free)'
      });

    } catch (error) {
      console.error('❌ Binance Coin Info Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: null,
        source: 'Binance Public API (100% Free)'
      });
    }
  }
}

export const binanceController = new BinanceController();
