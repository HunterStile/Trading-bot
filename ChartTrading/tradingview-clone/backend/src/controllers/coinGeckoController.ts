import { Request, Response } from 'express';
import { coinGeckoService } from '../services/coinGeckoService';

export class CoinGeckoController {
  async getKlineData(req: Request, res: Response) {
    try {
      const { symbol = 'BTCUSDT', interval = 'D', limit = 100 } = req.query;
      
      console.log(`📊 CoinGecko API request: ${symbol}, ${interval}, limit: ${limit}`);
      
      const klineData = await coinGeckoService.getKlineData(
        symbol as string,
        interval as string,
        parseInt(limit as string) || 100
      );

      res.json({
        success: true,
        data: klineData,
        symbol: symbol,
        interval: interval,
        count: klineData.length,
        source: 'CoinGecko API (Free)'
      });

    } catch (error) {
      console.error('❌ CoinGecko Controller Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        symbol: req.query.symbol || 'unknown',
        interval: req.query.interval || 'unknown',
        source: 'CoinGecko API (Free)'
      });
    }
  }

  async getSupportedSymbols(req: Request, res: Response) {
    try {
      const symbols = await coinGeckoService.getSupportedSymbols();
      
      res.json({
        success: true,
        symbols: symbols,
        count: symbols.length,
        source: 'CoinGecko API (Free)'
      });

    } catch (error) {
      console.error('❌ CoinGecko Symbols Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch symbols'
      });
    }
  }

  async getCoinInfo(req: Request, res: Response) {
    try {
      const { symbol } = req.params;
      
      if (!symbol) {
        return res.status(400).json({
          success: false,
          error: 'Symbol parameter is required'
        });
      }

      const coinInfo = await coinGeckoService.getCoinInfo(symbol.toUpperCase());
      
      res.json({
        success: true,
        data: coinInfo,
        source: 'CoinGecko API (Free)'
      });

    } catch (error) {
      console.error('❌ CoinGecko Coin Info Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch coin info'
      });
    }
  }
}

export const coinGeckoController = new CoinGeckoController();
