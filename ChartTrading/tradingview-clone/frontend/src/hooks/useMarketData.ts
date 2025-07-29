import { useEffect, useState } from 'react';
import { fetchMarketData } from '../services/api';

const useMarketData = (symbol) => {
    const [marketData, setMarketData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const getMarketData = async () => {
            try {
                setLoading(true);
                const data = await fetchMarketData(symbol);
                setMarketData(data);
            } catch (err) {
                setError(err);
            } finally {
                setLoading(false);
            }
        };

        if (symbol) {
            getMarketData();
        }
    }, [symbol]);

    return { marketData, loading, error };
};

export default useMarketData;