import WebSocket from 'ws';
import { Server } from 'http';
import { MarketData } from '../models/OHLCV';
import { User } from '../models/User';

class WebSocketService {
    private wss: WebSocket.Server;

    constructor(server: Server) {
        this.wss = new WebSocket.Server({ server });
        this.initializeWebSocket();
    }

    private initializeWebSocket() {
        this.wss.on('connection', (ws: WebSocket) => {
            console.log('New client connected');

            ws.on('message', (message: string) => {
                this.handleMessage(ws, message);
            });

            ws.on('close', () => {
                console.log('Client disconnected');
            });
        });
    }

    private handleMessage(ws: WebSocket, message: string) {
        const data = JSON.parse(message);

        switch (data.type) {
            case 'subscribe':
                this.subscribeToMarketData(ws, data.symbol);
                break;
            case 'unsubscribe':
                this.unsubscribeFromMarketData(ws, data.symbol);
                break;
            default:
                console.error('Unknown message type:', data.type);
        }
    }

    private subscribeToMarketData(ws: WebSocket, symbol: string) {
        // Logic to subscribe to market data for the given symbol
        console.log(`Subscribed to market data for symbol: ${symbol}`);
        // Example: Send market data to the client
        const marketData = this.getMarketData(symbol);
        ws.send(JSON.stringify({ type: 'marketData', data: marketData }));
    }

    private unsubscribeFromMarketData(ws: WebSocket, symbol: string) {
        // Logic to unsubscribe from market data for the given symbol
        console.log(`Unsubscribed from market data for symbol: ${symbol}`);
    }

    private getMarketData(symbol: string): MarketData {
        // Fetch market data for the symbol (mocked for this example)
        return {
            symbol,
            open: 100,
            high: 105,
            low: 95,
            close: 102,
            volume: 1000,
        };
    }
}

export default WebSocketService;