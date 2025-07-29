import { Router } from 'express';
import { coinGeckoController } from '../controllers/coinGeckoController';

const router = Router();

// GET /api/coingecko/kline - Ottieni dati candlestick
router.get('/kline', coinGeckoController.getKlineData.bind(coinGeckoController));

// GET /api/coingecko/symbols - Lista simboli supportati
router.get('/symbols', coinGeckoController.getSupportedSymbols.bind(coinGeckoController));

// GET /api/coingecko/info/:symbol - Info dettagliate su una crypto
router.get('/info/:symbol', coinGeckoController.getCoinInfo.bind(coinGeckoController));

export default router;
