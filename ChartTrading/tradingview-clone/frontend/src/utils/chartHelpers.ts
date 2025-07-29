import { ChartData } from '../types';

export const calculateChartData = (rawData: any[]): ChartData[] => {
    return rawData.map(data => ({
        time: data.timestamp,
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        volume: data.volume,
    }));
};

export const formatChartData = (data: ChartData[]): any[] => {
    return data.map(({ time, open, high, low, close, volume }) => ({
        x: new Date(time),
        y: [open, high, low, close],
        volume,
    }));
};

export const getChartOptions = (title: string, yAxisLabel: string) => {
    return {
        responsive: true,
        scales: {
            x: {
                type: 'time',
                title: {
                    display: true,
                    text: 'Time',
                },
            },
            y: {
                title: {
                    display: true,
                    text: yAxisLabel,
                },
            },
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
            },
            title: {
                display: true,
                text: title,
            },
        },
    };
};