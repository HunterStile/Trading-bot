// MongoDB initialization script
// Questo script viene eseguito quando il container MongoDB viene creato

// Crea il database principale
db = db.getSiblingDB('tradingview_clone');

// Crea le collezioni principali con gli indici
db.createCollection('users');
db.createCollection('symbols');
db.createCollection('market_data');
db.createCollection('user_settings');
db.createCollection('watchlists');

// Indici per performance
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });

db.symbols.createIndex({ "symbol": 1 }, { unique: true });
db.symbols.createIndex({ "exchange": 1 });

db.market_data.createIndex({ "symbol": 1, "timestamp": 1 });
db.market_data.createIndex({ "symbol": 1, "timeframe": 1, "timestamp": 1 });

db.user_settings.createIndex({ "userId": 1 });
db.watchlists.createIndex({ "userId": 1 });

// Inserisci alcuni dati di esempio
db.symbols.insertMany([
    {
        symbol: "BTCUSDT",
        exchange: "binance",
        baseAsset: "BTC",
        quoteAsset: "USDT",
        status: "active",
        createdAt: new Date()
    },
    {
        symbol: "ETHUSDT", 
        exchange: "binance",
        baseAsset: "ETH",
        quoteAsset: "USDT",
        status: "active",
        createdAt: new Date()
    },
    {
        symbol: "ADAUSDT",
        exchange: "binance", 
        baseAsset: "ADA",
        quoteAsset: "USDT",
        status: "active",
        createdAt: new Date()
    }
]);

print('Database inizializzato con successo!');
print('Collezioni create:', db.getCollectionNames());
print('Simboli inseriti:', db.symbols.count());
