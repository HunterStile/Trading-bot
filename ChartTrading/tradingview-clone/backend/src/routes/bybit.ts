import { Router } from 'express';
import { getBybitKlineData, getBybitSymbols } from '../controllers/bybitController';

const router = Router();

// Get kline data from Bybit
router.get('/kline', getBybitKlineData);

// Get available symbols
router.get('/symbols', getBybitSymbols);

export default router;
