import { Request, Response, NextFunction } from 'express';

export const validateRequest = (req: Request, res: Response, next: NextFunction) => {
    const { body } = req;

    // Example validation logic
    if (!body.symbol || typeof body.symbol !== 'string') {
        return res.status(400).json({ error: 'Invalid symbol' });
    }

    if (!body.timeframe || typeof body.timeframe !== 'string') {
        return res.status(400).json({ error: 'Invalid timeframe' });
    }

    // Add more validation rules as needed

    next();
};