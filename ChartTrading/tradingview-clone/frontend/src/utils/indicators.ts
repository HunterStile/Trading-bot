export const calculateRSI = (prices: number[], period: number = 14): number[] => {
    const rsi: number[] = [];
    if (prices.length < period) {
        return rsi; // Not enough data
    }

    for (let i = period; i < prices.length; i++) {
        const gains: number[] = [];
        const losses: number[] = [];

        for (let j = i - period + 1; j <= i; j++) {
            const change = prices[j] - prices[j - 1];
            if (change > 0) {
                gains.push(change);
            } else {
                losses.push(-change);
            }
        }

        const avgGain = gains.reduce((a, b) => a + b, 0) / period;
        const avgLoss = losses.reduce((a, b) => a + b, 0) / period;

        const rs = avgLoss === 0 ? 0 : avgGain / avgLoss;
        rsi.push(100 - (100 / (1 + rs)));
    }

    return rsi;
};

export const calculateMACD = (prices: number[], shortPeriod: number = 12, longPeriod: number = 26, signalPeriod: number = 9): number[] => {
    const macd: number[] = [];
    const shortEMA = calculateEMA(prices, shortPeriod);
    const longEMA = calculateEMA(prices, longPeriod);

    for (let i = 0; i < longEMA.length; i++) {
        macd.push(shortEMA[i] - longEMA[i]);
    }

    return calculateEMA(macd, signalPeriod);
};

export const calculateEMA = (prices: number[], period: number): number[] => {
    const ema: number[] = [];
    const k = 2 / (period + 1);

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            ema.push(null); // Not enough data
        } else if (i === period - 1) {
            const avg = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
            ema.push(avg);
        } else {
            const currentEma = (prices[i] - ema[i - 1]) * k + ema[i - 1];
            ema.push(currentEma);
        }
    }

    return ema;
};

export const calculateMovingAverage = (prices: number[], period: number): number[] => {
    const movingAverage: number[] = [];

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            movingAverage.push(null); // Not enough data
        } else {
            const avg = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
            movingAverage.push(avg);
        }
    }

    return movingAverage;
};

export const calculateBollingerBands = (prices: number[], period: number = 20, stdDevMultiplier: number = 2): { upperBand: number[], lowerBand: number[] } => {
    const upperBand: number[] = [];
    const lowerBand: number[] = [];
    const movingAvg = calculateMovingAverage(prices, period);

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            upperBand.push(null); // Not enough data
            lowerBand.push(null); // Not enough data
        } else {
            const slice = prices.slice(i - period + 1, i + 1);
            const avg = movingAvg[i];
            const stdDev = Math.sqrt(slice.reduce((sum, value) => sum + Math.pow(value - avg, 2), 0) / period);
            upperBand.push(avg + stdDevMultiplier * stdDev);
            lowerBand.push(avg - stdDevMultiplier * stdDev);
        }
    }

    return { upperBand, lowerBand };
};