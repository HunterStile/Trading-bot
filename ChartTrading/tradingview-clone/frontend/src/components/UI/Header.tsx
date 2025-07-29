import React from 'react';

const Header: React.FC = () => {
    return (
        <header className="header">
            <h1 className="header-title">TradingView Clone</h1>
            <nav className="header-nav">
                <ul>
                    <li><a href="#chart">Chart</a></li>
                    <li><a href="#indicators">Indicators</a></li>
                    <li><a href="#watchlist">Watchlist</a></li>
                    <li><a href="#market-data">Market Data</a></li>
                </ul>
            </nav>
        </header>
    );
};

export default Header;