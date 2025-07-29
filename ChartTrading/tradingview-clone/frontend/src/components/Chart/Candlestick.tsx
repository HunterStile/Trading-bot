import React from 'react';
import { Chart } from 'react-charts';

interface CandlestickProps {
    data: {
        date: Date;
        open: number;
        high: number;
        low: number;
        close: number;
    }[];
}

const Candlestick: React.FC<CandlestickProps> = ({ data }) => {
    const series = React.useMemo(
        () => ({
            type: 'candlestick',
            showPoints: false,
        }),
        []
    );

    const axes = React.useMemo(
        () => [
            { primary: true, type: 'time', position: 'bottom' },
            { type: 'linear', position: 'left' },
        ],
        []
    );

    const chartData = React.useMemo(
        () => [
            {
                label: 'Candlestick Chart',
                data: data.map(d => ({
                    primary: d.date,
                    secondary: [d.open, d.high, d.low, d.close],
                })),
            },
        ],
        [data]
    );

    return (
        <div style={{ height: '400px', width: '100%' }}>
            <Chart data={chartData} series={series} axes={axes} />
        </div>
    );
};

export default Candlestick;