export function calculateRSI(prices: number[], period: number = 14): number[] {
    if (prices.length < period + 1) {
        return Array(prices.length).fill(50); // Neutral value if insufficient data
    }

    const deltas: number[] = [];
    for (let i = 1; i < prices.length; i++) {
        deltas.push(prices[i] - prices[i - 1]);
    }

    const gains: number[] = deltas.map(delta => Math.max(delta, 0));
    const losses: number[] = deltas.map(delta => Math.abs(Math.min(delta, 0)));

    const rsiValues: number[] = Array(period).fill(50); // Neutral values for the first 'period' values

    if (gains.length >= period) {
        let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
        let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;

        if (avgLoss === 0) {
            rsiValues.push(100);
        } else {
            const rs = avgGain / avgLoss;
            const rsi = 100 - (100 / (1 + rs));
            rsiValues.push(rsi);
        }

        for (let i = period; i < gains.length; i++) {
            avgGain = (avgGain * (period - 1) + gains[i]) / period;
            avgLoss = (avgLoss * (period - 1) + losses[i]) / period;

            if (avgLoss === 0) {
                rsiValues.push(100);
            } else {
                const rs = avgGain / avgLoss;
                const rsi = 100 - (100 / (1 + rs));
                rsiValues.push(rsi);
            }
        }
    }

    while (rsiValues.length < prices.length) {
        rsiValues.push(50);
    }

    return rsiValues.slice(0, prices.length);
}

export function rsiSignals(rsiValues: number[], oversoldLevel: number = 30, overboughtLevel: number = 70): string[] {
    return rsiValues.map(rsi => {
        if (rsi <= oversoldLevel) {
            return 'oversold';
        } else if (rsi >= overboughtLevel) {
            return 'overbought';
        } else {
            return 'neutral';
        }
    });
}

export function rsiDivergence(prices: number[], rsiValues: number[], lookback: number = 5): string[] {
    if (prices.length < lookback * 2 || rsiValues.length < lookback * 2) {
        return Array(prices.length).fill('none');
    }

    const signals: string[] = Array(lookback).fill('none');

    for (let i = lookback; i < prices.length - lookback; i++) {
        const priceHigh = Math.max(...prices.slice(i - lookback, i + lookback + 1));
        const priceLow = Math.min(...prices.slice(i - lookback, i + lookback + 1));
        const rsiHigh = Math.max(...rsiValues.slice(i - lookback, i + lookback + 1));
        const rsiLow = Math.min(...rsiValues.slice(i - lookback, i + lookback + 1));

        const currentPrice = prices[i];
        const currentRsi = rsiValues[i];

        if (currentPrice <= priceLow && currentRsi > rsiLow && currentRsi < 50) {
            signals.push('bullish_div');
        } else if (currentPrice >= priceHigh && currentRsi < rsiHigh && currentRsi > 50) {
            signals.push('bearish_div');
        } else {
            signals.push('none');
        }
    }

    while (signals.length < prices.length) {
        signals.push('none');
    }

    return signals;
}