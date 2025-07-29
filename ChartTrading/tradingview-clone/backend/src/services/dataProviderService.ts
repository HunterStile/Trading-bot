import axios from 'axios';
import { MarketData } from '../../shared/types/marketData';

const API_BASE_URL = 'http://localhost:5000/api'; // Adjust the base URL as needed

export const fetchMarketData = async (symbol: string): Promise<MarketData> => {
    try {
        const response = await axios.get(`${API_BASE_URL}/marketData/${symbol}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching market data:', error);
        throw error;
    }
};

export const fetchHistoricalData = async (symbol: string, timeframe: string): Promise<MarketData[]> => {
    try {
        const response = await axios.get(`${API_BASE_URL}/marketData/historical`, {
            params: { symbol, timeframe },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching historical data:', error);
        throw error;
    }
};

export const fetchSymbols = async (): Promise<string[]> => {
    try {
        const response = await axios.get(`${API_BASE_URL}/symbols`);
        return response.data;
    } catch (error) {
        console.error('Error fetching symbols:', error);
        throw error;
    }
};