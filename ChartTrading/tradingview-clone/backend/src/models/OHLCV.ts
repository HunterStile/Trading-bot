export interface OHLCV {
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timestamp: number; // Unix timestamp in milliseconds
}

export class OHLCVData {
    private data: OHLCV[];

    constructor() {
        this.data = [];
    }

    addData(ohlcv: OHLCV): void {
        this.data.push(ohlcv);
    }

    getData(): OHLCV[] {
        return this.data;
    }

    getLatest(): OHLCV | null {
        return this.data.length > 0 ? this.data[this.data.length - 1] : null;
    }

    clearData(): void {
        this.data = [];
    }
}