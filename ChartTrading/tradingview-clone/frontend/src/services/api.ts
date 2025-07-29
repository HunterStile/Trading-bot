import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api'; // Adjust the base URL as needed

export const fetchMarketData = async (symbol) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/marketData/${symbol}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching market data:', error);
        throw error;
    }
};

export const fetchSymbols = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/symbols`);
        return response.data;
    } catch (error) {
        console.error('Error fetching symbols:', error);
        throw error;
    }
};

export const fetchUserData = async (userId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/users/${userId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching user data:', error);
        throw error;
    }
};