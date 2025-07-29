import React from 'react';
import { useEffect, useState } from 'react';
import { fetchRSIData } from '../../services/api';
import { Chart } from '../Chart/ChartContainer';

const RSI = ({ symbol, period = 14 }) => {
    const [rsiData, setRsiData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const getRSIData = async () => {
            try {
                const data = await fetchRSIData(symbol, period);
                setRsiData(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        getRSIData();
    }, [symbol, period]);

    if (loading) return <div>Loading RSI data...</div>;
    if (error) return <div>Error fetching RSI data: {error}</div>;

    return (
        <div>
            <h2>RSI for {symbol}</h2>
            <Chart data={rsiData} />
        </div>
    );
};

export default RSI;