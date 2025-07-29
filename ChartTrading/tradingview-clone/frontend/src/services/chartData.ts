import { useEffect, useState } from 'react';
import { fetchChartData } from '../services/api';

export const useChartData = (symbol, timeframe) => {
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const getData = async () => {
            try {
                setLoading(true);
                const data = await fetchChartData(symbol, timeframe);
                setChartData(data);
            } catch (err) {
                setError(err);
            } finally {
                setLoading(false);
            }
        };

        getData();
    }, [symbol, timeframe]);

    return { chartData, loading, error };
};