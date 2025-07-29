import { Request, Response } from 'express';
import { BinanceService } from '../services/binanceService';
import { Timeframe } from '../../shared/types/marketData';

export class MarketDataController {
    private binanceService: BinanceService;

    constructor() {
        this.binanceService = new BinanceService();
    }

    /**
     * GET /api/klines/:symbol
     * Recupera dati storici kline
     */
    async getKlines(req: Request, res: Response) {
        try {
            const { symbol } = req.params;
            const { 
                interval = '1d',
                limit = 500,
                startTime,
                endTime 
            } = req.query;

            // Valida parametri
            if (!symbol) {
                return res.status(400).json({
                    error: 'Simbolo richiesto'
                });
            }

            const data = await this.binanceService.getKlines(
                symbol,
                interval as Timeframe,
                parseInt(limit as string),
                startTime ? parseInt(startTime as string) : undefined,
                endTime ? parseInt(endTime as string) : undefined
            );

            res.json({
                success: true,
                data
            });

        } catch (error) {
            console.error('Errore getKlines:', error);
            res.status(500).json({
                error: 'Errore interno del server',
                message: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }

    /**
     * GET /api/symbols
     * Recupera tutti i simboli disponibili
     */
    async getSymbols(req: Request, res: Response) {
        try {
            const symbols = await this.binanceService.getExchangeInfo();
            
            res.json({
                success: true,
                data: symbols
            });

        } catch (error) {
            console.error('Errore getSymbols:', error);
            res.status(500).json({
                error: 'Errore interno del server',
                message: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }

    /**
     * GET /api/price/:symbol
     * Recupera prezzo attuale
     */
    async getCurrentPrice(req: Request, res: Response) {
        try {
            const { symbol } = req.params;

            if (!symbol) {
                return res.status(400).json({
                    error: 'Simbolo richiesto'
                });
            }

            const price = await this.binanceService.getCurrentPrice(symbol);

            res.json({
                success: true,
                data: {
                    symbol,
                    price
                }
            });

        } catch (error) {
            console.error('Errore getCurrentPrice:', error);
            res.status(500).json({
                error: 'Errore interno del server',
                message: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }

    /**
     * GET /api/stats/:symbol
     * Recupera statistiche 24h
     */
    async get24hrStats(req: Request, res: Response) {
        try {
            const { symbol } = req.params;

            if (!symbol) {
                return res.status(400).json({
                    error: 'Simbolo richiesto'
                });
            }

            const stats = await this.binanceService.get24hrStats(symbol);

            res.json({
                success: true,
                data: stats
            });

        } catch (error) {
            console.error('Errore get24hrStats:', error);
            res.status(500).json({
                error: 'Errore interno del server',
                message: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }
}

// Export delle funzioni per compatibilità con il codice esistente
const controller = new MarketDataController();

export const fetchMarketData = async (req: Request, res: Response) => {
    // Redirect alla nuova funzione per i simboli
    await controller.getSymbols(req, res);
};

export const fetchMarketDataBySymbol = async (req: Request, res: Response) => {
    // Redirect alla nuova funzione per i klines
    await controller.getKlines(req, res);
};