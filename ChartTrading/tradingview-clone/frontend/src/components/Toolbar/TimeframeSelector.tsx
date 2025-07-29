import React from 'react';

const TimeframeSelector: React.FC = () => {
    const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];
    const [selectedTimeframe, setSelectedTimeframe] = React.useState<string>(timeframes[0]);

    const handleTimeframeChange = (timeframe: string) => {
        setSelectedTimeframe(timeframe);
        // Add logic to update the chart based on the selected timeframe
    };

    return (
        <div className="timeframe-selector">
            <label htmlFor="timeframe">Select Timeframe:</label>
            <select
                id="timeframe"
                value={selectedTimeframe}
                onChange={(e) => handleTimeframeChange(e.target.value)}
            >
                {timeframes.map((timeframe) => (
                    <option key={timeframe} value={timeframe}>
                        {timeframe}
                    </option>
                ))}
            </select>
        </div>
    );
};

export default TimeframeSelector;