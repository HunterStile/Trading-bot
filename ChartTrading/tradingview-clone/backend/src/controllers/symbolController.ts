import { Request, Response } from 'express';
import { Symbol } from '../models/Symbol';

export const getSymbols = async (req: Request, res: Response) => {
    try {
        const symbols = await Symbol.find();
        res.status(200).json(symbols);
    } catch (error) {
        res.status(500).json({ message: 'Error retrieving symbols', error });
    }
};

export const getSymbolById = async (req: Request, res: Response) => {
    const { id } = req.params;
    try {
        const symbol = await Symbol.findById(id);
        if (!symbol) {
            return res.status(404).json({ message: 'Symbol not found' });
        }
        res.status(200).json(symbol);
    } catch (error) {
        res.status(500).json({ message: 'Error retrieving symbol', error });
    }
};

export const createSymbol = async (req: Request, res: Response) => {
    const newSymbol = new Symbol(req.body);
    try {
        const savedSymbol = await newSymbol.save();
        res.status(201).json(savedSymbol);
    } catch (error) {
        res.status(400).json({ message: 'Error creating symbol', error });
    }
};

export const updateSymbol = async (req: Request, res: Response) => {
    const { id } = req.params;
    try {
        const updatedSymbol = await Symbol.findByIdAndUpdate(id, req.body, { new: true });
        if (!updatedSymbol) {
            return res.status(404).json({ message: 'Symbol not found' });
        }
        res.status(200).json(updatedSymbol);
    } catch (error) {
        res.status(400).json({ message: 'Error updating symbol', error });
    }
};

export const deleteSymbol = async (req: Request, res: Response) => {
    const { id } = req.params;
    try {
        const deletedSymbol = await Symbol.findByIdAndDelete(id);
        if (!deletedSymbol) {
            return res.status(404).json({ message: 'Symbol not found' });
        }
        res.status(204).send();
    } catch (error) {
        res.status(500).json({ message: 'Error deleting symbol', error });
    }
};