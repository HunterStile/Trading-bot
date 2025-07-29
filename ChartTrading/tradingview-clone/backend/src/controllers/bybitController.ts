import { Request, Response } from 'express';
import { bybitService } from '../services/bybitService';

export const getBybitKlineData = async (req: Request, res: Response) => {
  try {
    const {
      symbol = 'BTCUSDT',
      interval = 'D',
      limit = 100,
      category = 'linear'
    } = req.query;

    const klineData = await bybitService.getKlineData(
      category as string,
      symbol as string,
      interval as string,
      parseInt(limit as string)
    );

    res.json({
      success: true,
      data: klineData,
      symbol,
      interval,
      count: klineData.length
    });
  } catch (error) {
    console.error('Error fetching Bybit kline data:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      data: []
    });
  }
};

export const getBybitSymbols = async (req: Request, res: Response) => {
  try {
    const symbols = await bybitService.getSymbols();
    
    res.json({
      success: true,
      data: symbols
    });
  } catch (error) {
    console.error('Error fetching Bybit symbols:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      data: []
    });
  }
};
