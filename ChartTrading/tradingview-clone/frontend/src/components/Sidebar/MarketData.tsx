import React from 'react';

const MarketData: React.FC = () => {
    const [marketData, setMarketData] = React.useState<any[]>([]);
    const [loading, setLoading] = React.useState<boolean>(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
        const fetchMarketData = async () => {
            try {
                const response = await fetch('/api/market-data');
                if (!response.ok) {
                    throw new Error('Failed to fetch market data');
                }
                const data = await response.json();
                setMarketData(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchMarketData();
    }, []);

    if (loading) {
        return <div>Loading market data...</div>;
    }

    if (error) {
        return <div>Error: {error}</div>;
    }

    return (
        <div className="market-data">
            <h2>Market Data</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Volume</th>
                    </tr>
                </thead>
                <tbody>
                    {marketData.map((data) => (
                        <tr key={data.symbol}>
                            <td>{data.symbol}</td>
                            <td>{data.price}</td>
                            <td>{data.change}</td>
                            <td>{data.volume}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default MarketData;