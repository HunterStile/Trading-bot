// Tipi per gli indicatori tecnici
export type IndicatorType = 'RSI' | 'MACD' | 'MovingAverage' | 'BollingerBands' | 'Volume' | 'Stochastic' | 'CCI' | 'Williams';

// RSI
export interface RSIConfig {
    period: number;
    overbought: number;
    oversold: number;
}

export interface RSIData {
    value: number;
    signal: 'overbought' | 'oversold' | 'neutral';
    timestamp: number;
}

// MACD
export interface MACDConfig {
    fastPeriod: number;
    slowPeriod: number;
    signalPeriod: number;
}

export interface MACDData {
    macd: number;
    signal: number;
    histogram: number;
    timestamp: number;
}

// Moving Average
export interface MovingAverageConfig {
    period: number;
    type: 'sma' | 'ema' | 'wma';
}

export interface MovingAverageData {
    value: number;
    timestamp: number;
}

// Bollinger Bands
export interface BollingerBandsConfig {
    period: number;
    stdDev: number;
}

export interface BollingerBandsData {
    upper: number;
    middle: number;
    lower: number;
    timestamp: number;
}

// Volume
export interface VolumeData {
    volume: number;
    volumeAvg: number;
    timestamp: number;
}

// Configurazione generica indicatori
export interface IndicatorConfig {
    type: IndicatorType;
    period: number;
    oversoldLevel?: number;
    overboughtLevel?: number;
    visible?: boolean;
    color?: string;
    parameters?: Record<string, any>;
}

export interface IndicatorData {
    timestamp: number;
    value: number;
}

export interface IndicatorsState {
    [key: string]: IndicatorData[];
}

// Indicatori avanzati
export interface AdvancedIndicatorData {
    name: string;
    data: any[];
    config: IndicatorConfig;
}

// Chart annotations
export interface ChartAnnotation {
    id: string;
    type: 'line' | 'rectangle' | 'text' | 'arrow' | 'trendline';
    points: Array<{x: number, y: number}>;
    style: {
        color: string;
        lineWidth?: number;
        fillColor?: string;
        text?: string;
        fontSize?: number;
    };
}

// Drawing tools
export type DrawingTool = 'none' | 'line' | 'rectangle' | 'circle' | 'arrow' | 'text' | 'trendline' | 'fibonacci';

export interface DrawingState {
    activeTool: DrawingTool;
    isDrawing: boolean;
    annotations: ChartAnnotation[];
}