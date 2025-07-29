import { Request, Response, NextFunction } from 'express';

const rateLimit = (limit: number, windowMs: number) => {
    const requests: { [key: string]: number } = {};

    return (req: Request, res: Response, next: NextFunction) => {
        const key = req.ip;

        if (!requests[key]) {
            requests[key] = 1;
        } else {
            requests[key]++;
        }

        if (requests[key] > limit) {
            return res.status(429).json({ message: 'Too many requests, please try again later.' });
        }

        setTimeout(() => {
            requests[key]--;
            if (requests[key] <= 0) {
                delete requests[key];
            }
        }, windowMs);

        next();
    };
};

export default rateLimit;