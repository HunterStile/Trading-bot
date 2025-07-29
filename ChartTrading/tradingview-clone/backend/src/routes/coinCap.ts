import { Router } from 'express';
import { binanceController } from '../controllers/binanceController';

const router = Router();

// Usiamo Binance invece di CoinCap per maggiore affidabilità
// GET /api/coincap/kline - Ottieni dati candlestick (tramite Binance)
router.get('/kline', binanceController.getKlineData.bind(binanceController));

// GET /api/coincap/symbols - Lista simboli supportati (tramite Binance)  
router.get('/symbols', binanceController.getSupportedSymbols.bind(binanceController));

// GET /api/coincap/info/:symbol - Info dettagliate su una crypto (tramite Binance)
router.get('/info/:symbol', binanceController.getCoinInfo.bind(binanceController));

export default router;
