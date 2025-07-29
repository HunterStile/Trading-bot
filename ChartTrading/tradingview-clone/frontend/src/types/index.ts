export type ChartData = {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
};

export type IndicatorData = {
    rsi?: number[];
    macd?: {
        macd: number[];
        signal: number[];
        histogram: number[];
    };
    movingAverage?: number[];
    bollingerBands?: {
        upper: number[];
        middle: number[];
        lower: number[];
    };
};

export type MarketData = {
    symbol: string;
    price: number;
    volume: number;
    timestamp: number;
};

export type WebSocketMessage = {
    type: string;
    payload: any;
};

export interface ChartProps {
    data: ChartData[];
    indicators?: IndicatorData;
    width: number;
    height: number;
}

export interface IndicatorProps {
    data: number[];
    label: string;
}