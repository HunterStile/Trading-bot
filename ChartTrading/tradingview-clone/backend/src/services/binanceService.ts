import axios from 'axios';
import { Kline, OHLCV, Timeframe, HistoricalDataResponse } from '../../shared/types/marketData';

export class BinanceService {
    private baseUrl = 'https://api.binance.com/api/v3';
    private webSocketUrl = 'wss://stream.binance.com:9443/ws/';

    /**
     * Recupera i dati storici kline da Binance
     */
    async getKlines(
        symbol: string,
        interval: Timeframe,
        limit: number = 500,
        startTime?: number,
        endTime?: number
    ): Promise<HistoricalDataResponse> {
        try {
            const params: any = {
                symbol: symbol.toUpperCase(),
                interval,
                limit
            };

            if (startTime) params.startTime = startTime;
            if (endTime) params.endTime = endTime;

            const response = await axios.get(`${this.baseUrl}/klines`, { params });

            // Converte i dati Binance in formato Kline
            const data: Kline[] = response.data.map((kline: any[]) => ({
                openTime: kline[0],
                open: kline[1],
                high: kline[2],
                low: kline[3],
                close: kline[4],
                volume: kline[5],
                closeTime: kline[6],
                quoteAssetVolume: kline[7],
                numberOfTrades: kline[8],
                takerBuyBaseAssetVolume: kline[9],
                takerBuyQuoteAssetVolume: kline[10]
            }));

            return {
                symbol,
                interval,
                data,
                count: data.length,
                status: 'success'
            };
        } catch (error) {
            console.error('Errore recupero klines da Binance:', error);
            return {
                symbol,
                interval,
                data: [],
                count: 0,
                status: 'error',
                message: `Impossibile recuperare dati per ${symbol}: ${error}`
            };
        }
    }

    /**
     * Recupera tutti i simboli disponibili su Binance
     */
    async getExchangeInfo() {
        try {
            const response = await axios.get(`${this.baseUrl}/exchangeInfo`);
            return response.data.symbols.filter((symbol: any) => 
                symbol.status === 'TRADING' && 
                symbol.quoteAsset === 'USDT'
            );
        } catch (error) {
            console.error('Errore recupero exchange info:', error);
            throw new Error('Impossibile recuperare informazioni exchange');
        }
    }

    /**
     * Recupera il prezzo attuale di un simbolo
     */
    async getCurrentPrice(symbol: string) {
        try {
            const response = await axios.get(`${this.baseUrl}/ticker/price`, {
                params: { symbol: symbol.toUpperCase() }
            });
            return parseFloat(response.data.price);
        } catch (error) {
            console.error('Errore recupero prezzo:', error);
            throw new Error(`Impossibile recuperare prezzo per ${symbol}`);
        }
    }

    /**
     * Recupera statistiche 24h per un simbolo
     */
    async get24hrStats(symbol: string) {
        try {
            const response = await axios.get(`${this.baseUrl}/ticker/24hr`, {
                params: { symbol: symbol.toUpperCase() }
            });
            return response.data;
        } catch (error) {
            console.error('Errore recupero stats 24h:', error);
            throw new Error(`Impossibile recuperare statistiche per ${symbol}`);
        }
    }

    /**
     * Crea WebSocket stream per dati real-time
     */
    createKlineStream(symbol: string, interval: Timeframe) {
        const streamName = `${symbol.toLowerCase()}@kline_${interval}`;
        return `${this.webSocketUrl}${streamName}`;
    }

    /**
     * Valida se un simbolo esiste
     */
    async validateSymbol(symbol: string): Promise<boolean> {
        try {
            await this.getCurrentPrice(symbol);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Converte timeframe per Binance API
     */
    private convertTimeframe(timeframe: string): string {
        const mapping: Record<string, string> = {
            '1m': '1m',
            '3m': '3m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d',
            '3d': '3d',
            '1w': '1w',
            '1M': '1M'
        };
        return mapping[timeframe] || '1d';
    }
}
