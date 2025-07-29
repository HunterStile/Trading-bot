import { Router } from 'express';
import { MarketDataController, fetchMarketData, fetchMarketDataBySymbol } from '../controllers/marketDataController';

const router = Router();
const marketDataController = new MarketDataController();

// Route per i dati storici kline
router.get('/klines/:symbol', (req, res) => marketDataController.getKlines(req, res));

// Route per ottenere tutti i simboli
router.get('/symbols', (req, res) => marketDataController.getSymbols(req, res));

// Route per ottenere il prezzo attuale
router.get('/price/:symbol', (req, res) => marketDataController.getCurrentPrice(req, res));

// Route per ottenere statistiche 24h
router.get('/stats/:symbol', (req, res) => marketDataController.get24hrStats(req, res));

// Route legacy per compatibilità
router.get('/market-data', fetchMarketData);
router.get('/market-data/:symbol', fetchMarketDataBySymbol);

export default router;