import React from 'react';
import Candlestick from './Candlestick';
import LineChart from './LineChart';
import VolumeChart from './VolumeChart';
import { useChart } from '../../hooks/useChart';

const ChartContainer: React.FC = () => {
    const { chartData, chartType } = useChart();

    return (
        <div className="chart-container">
            {chartType === 'candlestick' && <Candlestick data={chartData} />}
            {chartType === 'line' && <LineChart data={chartData} />}
            {chartType === 'volume' && <VolumeChart data={chartData} />}
        </div>
    );
};

export default ChartContainer;