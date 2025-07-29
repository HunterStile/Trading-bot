import { useEffect, useState } from 'react';
import { fetchChartData } from '../services/chartData';
import { ChartData } from '../types';

const useChart = (symbol: string, timeframe: string) => {
    const [chartData, setChartData] = useState<ChartData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadChartData = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await fetchChartData(symbol, timeframe);
                setChartData(data);
            } catch (err) {
                setError('Failed to fetch chart data');
            } finally {
                setLoading(false);
            }
        };

        loadChartData();
    }, [symbol, timeframe]);

    return { chartData, loading, error };
};

export default useChart;