import React from 'react';
import { useEffect, useState } from 'react';
import { calculateMACD } from '../../utils/indicators';

interface MACDProps {
    prices: number[];
    shortPeriod?: number;
    longPeriod?: number;
    signalPeriod?: number;
}

const MACD: React.FC<MACDProps> = ({ prices, shortPeriod = 12, longPeriod = 26, signalPeriod = 9 }) => {
    const [macdValues, setMacdValues] = useState<{ macd: number[]; signal: number[]; histogram: number[] }>({
        macd: [],
        signal: [],
        histogram: [],
    });

    useEffect(() => {
        const { macd, signal, histogram } = calculateMACD(prices, shortPeriod, longPeriod, signalPeriod);
        setMacdValues({ macd, signal, histogram });
    }, [prices, shortPeriod, longPeriod, signalPeriod]);

    return (
        <div>
            <h3>MACD Indicator</h3>
            <div>
                <h4>MACD Values</h4>
                <ul>
                    {macdValues.macd.map((value, index) => (
                        <li key={index}>MACD: {value.toFixed(2)}, Signal: {macdValues.signal[index]?.toFixed(2)}, Histogram: {macdValues.histogram[index]?.toFixed(2)}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default MACD;