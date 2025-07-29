import { OHLCV } from '../../models/OHLCV';

export function calculateSimpleMovingAverage(data: OHLCV[], period: number): number[] {
    const sma: number[] = [];
    
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            sma.push(null); // Not enough data for SMA
        } else {
            const sum = data.slice(i - period + 1, i + 1).reduce((acc, curr) => acc + curr.close, 0);
            sma.push(sum / period);
        }
    }
    
    return sma;
}

export function calculateExponentialMovingAverage(data: OHLCV[], period: number): number[] {
    const ema: number[] = [];
    const k = 2 / (period + 1);
    
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            ema.push(null); // Not enough data for EMA
        } else if (i === period - 1) {
            const sum = data.slice(0, period).reduce((acc, curr) => acc + curr.close, 0);
            ema.push(sum / period); // First EMA is SMA
        } else {
            const currentEma = (data[i].close - ema[i - 1]) * k + ema[i - 1];
            ema.push(currentEma);
        }
    }
    
    return ema;
}