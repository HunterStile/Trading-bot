import React from 'react';
import { useChart } from '../../hooks/useChart';
import { calculateMovingAverage } from '../../utils/indicators';

interface MovingAverageProps {
    prices: number[];
    period: number;
}

const MovingAverage: React.FC<MovingAverageProps> = ({ prices, period }) => {
    const movingAverage = calculateMovingAverage(prices, period);

    return (
        <div>
            <h3>Moving Average</h3>
            <ul>
                {movingAverage.map((value, index) => (
                    <li key={index}>{value.toFixed(2)}</li>
                ))}
            </ul>
        </div>
    );
};

export default MovingAverage;