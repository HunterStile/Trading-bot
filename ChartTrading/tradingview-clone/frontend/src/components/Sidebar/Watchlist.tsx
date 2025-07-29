import React from 'react';

const Watchlist: React.FC = () => {
    const [watchlist, setWatchlist] = React.useState<string[]>([]);

    const addSymbol = (symbol: string) => {
        setWatchlist(prev => [...prev, symbol]);
    };

    const removeSymbol = (symbol: string) => {
        setWatchlist(prev => prev.filter(s => s !== symbol));
    };

    return (
        <div className="watchlist">
            <h2>Watchlist</h2>
            <ul>
                {watchlist.map((symbol, index) => (
                    <li key={index}>
                        {symbol}
                        <button onClick={() => removeSymbol(symbol)}>Remove</button>
                    </li>
                ))}
            </ul>
            <button onClick={() => addSymbol(prompt('Enter symbol:') || '')}>Add Symbol</button>
        </div>
    );
};

export default Watchlist;