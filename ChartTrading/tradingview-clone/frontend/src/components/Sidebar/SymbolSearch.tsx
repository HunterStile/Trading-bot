import React, { useState, useEffect } from 'react';

const SymbolSearch = ({ onSelectSymbol }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [symbols, setSymbols] = useState([]);

    useEffect(() => {
        const fetchSymbols = async () => {
            try {
                const response = await fetch('/api/symbols'); // Adjust the API endpoint as needed
                const data = await response.json();
                setSymbols(data);
            } catch (error) {
                console.error('Error fetching symbols:', error);
            }
        };

        fetchSymbols();
    }, []);

    const handleSearchChange = (event) => {
        setSearchTerm(event.target.value);
    };

    const filteredSymbols = symbols.filter(symbol =>
        symbol.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="symbol-search">
            <input
                type="text"
                placeholder="Search for a symbol..."
                value={searchTerm}
                onChange={handleSearchChange}
            />
            <ul>
                {filteredSymbols.map((symbol, index) => (
                    <li key={index} onClick={() => onSelectSymbol(symbol)}>
                        {symbol}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default SymbolSearch;