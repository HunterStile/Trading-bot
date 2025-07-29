import React from 'react';
import { Line } from 'react-chartjs-2';
import { ChartData, ChartOptions } from 'chart.js';

interface VolumeChartProps {
    volumeData: number[];
    labels: string[];
}

const VolumeChart: React.FC<VolumeChartProps> = ({ volumeData, labels }) => {
    const data: ChartData<'line'> = {
        labels: labels,
        datasets: [
            {
                label: 'Volume',
                data: volumeData,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
                tension: 0.1,
            },
        ],
    };

    const options: ChartOptions<'line'> = {
        responsive: true,
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Time',
                },
            },
            y: {
                title: {
                    display: true,
                    text: 'Volume',
                },
                beginAtZero: true,
            },
        },
    };

    return (
        <div>
            <h2>Volume Chart</h2>
            <Line data={data} options={options} />
        </div>
    );
};

export default VolumeChart;