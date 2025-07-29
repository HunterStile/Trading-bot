import { Request, Response } from 'express';
import { coinCapService } from '../services/coinCapService';

export class CoinCapController {
  async getKlineData(req: Request, res: Response) {
    try {
      const { symbol = 'BTCUSDT', interval = 'D', limit = 1000 } = req.query;
      console.log(`🚀 CoinCap API request: ${symbol}, ${interval}, limit: ${limit}`);

      const klineData = await coinCapService.getKlineData(
        symbol as string,
        interval as string,
        parseInt(limit as string) || 1000
      );

      res.json({
        success: true,
        data: klineData,
        message: `Retrieved ${klineData.length} candlesticks from CoinCap`,
        metadata: {
          symbol: symbol,
          interval: interval,
          count: klineData.length,
          source: 'CoinCap API (100% Free)'
        }
      });

    } catch (error) {
      console.error('❌ CoinCap Controller Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: [],
        source: 'CoinCap API (100% Free)'
      });
    }
  }

  async getSupportedSymbols(req: Request, res: Response) {
    try {
      const symbols = await coinCapService.getSupportedSymbols();
      
      res.json({
        success: true,
        data: symbols,
        message: `Retrieved ${symbols.length} supported symbols from CoinCap`,
        source: 'CoinCap API (100% Free)'
      });

    } catch (error) {
      console.error('❌ CoinCap Symbols Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: [],
        source: 'CoinCap API (100% Free)'
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

      const coinInfo = await coinCapService.getCoinInfo(symbol.toUpperCase());
      
      res.json({
        success: true,
        data: coinInfo,
        message: `Retrieved info for ${symbol.toUpperCase()} from CoinCap`,
        source: 'CoinCap API (100% Free)'
      });

    } catch (error) {
      console.error('❌ CoinCap Coin Info Error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        data: null,
        source: 'CoinCap API (100% Free)'
      });
    }
  }
}

export const coinCapController = new CoinCapController();
