import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import dotenv from 'dotenv';
import marketDataRoutes from './routes/marketData';
import symbolRoutes from './routes/symbols';
import userRoutes from './routes/users';
import bybitRoutes from './routes/bybit';
import coinGeckoRoutes from './routes/coinGecko';
import coinCapRoutes from './routes/coinCap';
import { config } from './config/database';

// Carica le variabili d'ambiente
dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json()); // Sostituisce body-parser
app.use(express.urlencoded({ extended: true }));

// Route di test
app.get('/api/test', (req, res) => {
    res.json({ 
        message: 'Backend is working!', 
        timestamp: new Date().toISOString(),
        status: 'success' 
    });
});

// Routes
app.use('/api/market-data', marketDataRoutes);
app.use('/api/symbols', symbolRoutes);
app.use('/api/users', userRoutes);
app.use('/api/bybit', bybitRoutes);
app.use('/api/coingecko', coinGeckoRoutes);
app.use('/api/coincap', coinCapRoutes);

// Database connection
mongoose.connect(config.databaseUrl)
    .then(() => {
        console.log('Database connected successfully');
        app.listen(PORT, () => {
            console.log(`Server is running on port ${PORT}`);
        });
    })
    .catch(err => {
        console.error('Database connection error:', err);
    });