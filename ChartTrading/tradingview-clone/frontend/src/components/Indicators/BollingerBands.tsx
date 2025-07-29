import React from 'react';
import { Line } from 'react-chartjs-2';

interface BollingerBandsProps {
    prices: number[];
    period?: number;
    stdDevMultiplier?: number;
}

const BollingerBands: React.FC<BollingerBandsProps> = ({
    prices,
    period = 20,
    stdDevMultiplier = 2,
}) => {
    const calculateBollingerBands = (prices: number[]) => {
        const movingAverages: number[] = [];
        const upperBands: number[] = [];
        const lowerBands: number[] = [];

        for (let i = 0; i <= prices.length - period; i++) {
            const slice = prices.slice(i, i + period);
            const average = slice.reduce((sum, price) => sum + price, 0) / period;
            const variance = slice.reduce((sum, price) => sum + Math.pow(price - average, 2), 0) / period;
            const stdDev = Math.sqrt(variance);

            movingAverages.push(average);
            upperBands.push(average + stdDevMultiplier * stdDev);
            lowerBands.push(average - stdDevMultiplier * stdDev);
        }

        return { movingAverages, upperBands, lowerBands };
    };

    const { movingAverages, upperBands, lowerBands } = calculateBollingerBands(prices);

    const chartData = {
        labels: prices.slice(period - 1).map((_, index) => index + 1),
        datasets: [
            {
                label: 'Price',
                data: prices,
                borderColor: 'blue',
                fill: false,
            },
            {
                label: 'Upper Band',
                data: upperBands,
                borderColor: 'red',
                fill: false,
            },
            {
                label: 'Lower Band',
                data: lowerBands,
                borderColor: 'green',
                fill: false,
            },
            {
                label: 'Moving Average',
                data: movingAverages,
                borderColor: 'orange',
                fill: false,
            },
        ],
    };

    return (
        <div>
            <h2>Bollinger Bands</h2>
            <Line data={chartData} />
        </div>
    );
};

export default BollingerBands;