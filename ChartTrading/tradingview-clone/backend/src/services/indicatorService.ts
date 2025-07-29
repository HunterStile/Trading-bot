import { Request, Response } from 'express';
import { calculateRSI } from '../utils/indicators/rsi';
import { calculateMACD } from '../utils/indicators/macd';
import { calculateMovingAverage } from '../utils/indicators/movingAverage';

export const getRSI = (req: Request, res: Response) => {
    const { prices, period } = req.body;

    if (!prices || !Array.isArray(prices) || prices.length === 0) {
        return res.status(400).json({ error: 'Invalid prices array' });
    }

    const rsi = calculateRSI(prices, period);
    return res.json({ rsi });
};

export const getMACD = (req: Request, res: Response) => {
    const { prices, shortPeriod, longPeriod, signalPeriod } = req.body;

    if (!prices || !Array.isArray(prices) || prices.length === 0) {
        return res.status(400).json({ error: 'Invalid prices array' });
    }

    const macd = calculateMACD(prices, shortPeriod, longPeriod, signalPeriod);
    return res.json({ macd });
};

export const getMovingAverage = (req: Request, res: Response) => {
    const { prices, period } = req.body;

    if (!prices || !Array.isArray(prices) || prices.length === 0) {
        return res.status(400).json({ error: 'Invalid prices array' });
    }

    const movingAverage = calculateMovingAverage(prices, period);
    return res.json({ movingAverage });
};