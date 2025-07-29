import React from 'react';

const indicators = [
    { name: 'RSI', value: 'rsi' },
    { name: 'MACD', value: 'macd' },
    { name: 'Moving Average', value: 'moving_average' },
    { name: 'Bollinger Bands', value: 'bollinger_bands' },
];

const IndicatorSelector = ({ onSelect }) => {
    const handleSelect = (event) => {
        onSelect(event.target.value);
    };

    return (
        <div className="indicator-selector">
            <label htmlFor="indicator-select">Select Indicator:</label>
            <select id="indicator-select" onChange={handleSelect}>
                <option value="">--Choose an Indicator--</option>
                {indicators.map((indicator) => (
                    <option key={indicator.value} value={indicator.value}>
                        {indicator.name}
                    </option>
                ))}
            </select>
        </div>
    );
};

export default IndicatorSelector;