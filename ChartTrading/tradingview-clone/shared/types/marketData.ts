export interface MarketData {
    symbol: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timestamp: number;
}

export type Timeframe = '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '6h' | '8h' | '12h' | '1d' | '3d' | '1w' | '1M';

export interface OHLCV {
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

// Kline data structure (come da API Binance)
export interface Kline {
    openTime: number;
    open: string;
    high: string;
    low: string;
    close: string;
    volume: string;
    closeTime: number;
    quoteAssetVolume: string;
    numberOfTrades: number;
    takerBuyBaseAssetVolume: string;
    takerBuyQuoteAssetVolume: string;
    ignore?: string;
}

// Response per i dati storici
export interface HistoricalDataResponse {
    symbol: string;
    interval: string;
    data: Kline[];
    count: number;
    status: 'success' | 'error';
    message?: string;
}

export interface MarketDataResponse {
    data: MarketData[];
    status: string;
    message?: string;
}

export interface MarketDataSubscription {
    symbol: string;
    interval: string;
}
