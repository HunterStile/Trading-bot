export function calculateMACD(prices: number[], shortPeriod: number = 12, longPeriod: number = 26, signalPeriod: number = 9): { macd: number[], signal: number[], histogram: number[] } {
    const shortEma = calculateEMA(prices, shortPeriod);
    const longEma = calculateEMA(prices, longPeriod);
    const macd: number[] = [];
    const signal: number[] = [];
    const histogram: number[] = [];

    for (let i = 0; i < prices.length; i++) {
        if (shortEma[i] !== undefined && longEma[i] !== undefined) {
            macd[i] = shortEma[i] - longEma[i];
        } else {
            macd[i] = 0;
        }
    }

    const signalEma = calculateEMA(macd, signalPeriod);

    for (let i = 0; i < macd.length; i++) {
        if (signalEma[i] !== undefined) {
            signal[i] = signalEma[i];
            histogram[i] = macd[i] - signal[i];
        } else {
            signal[i] = 0;
            histogram[i] = 0;
        }
    }

    return { macd, signal, histogram };
}

function calculateEMA(prices: number[], period: number): number[] {
    const k = 2 / (period + 1);
    const ema: number[] = [];
    let initialEma = prices.slice(0, period).reduce((sum, price) => sum + price, 0) / period;

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            ema[i] = undefined; // Not enough data to calculate EMA
        } else if (i === period - 1) {
            ema[i] = initialEma; // First EMA is the average of the first 'period' prices
        } else {
            ema[i] = (prices[i] - ema[i - 1]) * k + ema[i - 1];
        }
    }

    return ema;
}