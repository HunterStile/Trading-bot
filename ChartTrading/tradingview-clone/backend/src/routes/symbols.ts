import { Router } from 'express';
import { getSymbols, getSymbolById, createSymbol, updateSymbol, deleteSymbol } from '../controllers/symbolController';

const router = Router();

// Route to get all symbols
router.get('/', getSymbols);

// Route to get a specific symbol by ID
router.get('/:id', getSymbolById);

// Route to create a new symbol
router.post('/', createSymbol);

// Route to update an existing symbol
router.put('/:id', updateSymbol);

// Route to delete a symbol
router.delete('/:id', deleteSymbol);

export default router;