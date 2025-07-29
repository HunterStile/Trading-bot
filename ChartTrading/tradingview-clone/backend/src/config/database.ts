export const config = {
    databaseUrl: process.env.DATABASE_URL || 'mongodb://localhost:27017/tradingview_clone',
    mongoOptions: {
        // useNewUrlParser e useUnifiedTopology sono deprecati in mongoose 6+
        // Mongoose 6+ usa queste impostazioni di default
    }
};

export const connectToDatabase = async () => {
    try {
        console.log('Connection to the database has been established successfully.');
    } catch (error) {
        console.error('Unable to connect to the database:', error);
    }
};