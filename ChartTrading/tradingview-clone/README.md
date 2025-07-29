# 📈 TradingView Clone - Professional Charting Platform

Un clone professionale di TradingView costruito con React, TypeScript, Node.js e WebSocket per real-time data.

## 🚀 Features

### 📊 Grafici Avanzati
- **Candlestick Charts** con dati real-time
- **Indicatori Tecnici**: RSI, MACD, EMA, Bollinger Bands, Volume
- **Drawing Tools**: trend lines, supporti/resistenze, fibonacci
- **Multi-timeframe**: 1m, 5m, 15m, 1h, 4h, 1D, 1W
- **Zoom e Pan** interattivi

### 📡 Real-time Data
- **WebSocket** connection con Binance API
- **Live Price Updates** senza refresh
- **Volume Analysis** in tempo reale
- **Market Depth** visualization

### 🛠️ Trading Tools
- **Symbol Search** con autocomplete
- **Watchlist** personalizzabili  
- **Price Alerts** e notifiche
- **Market Scanner** per opportunità

### 🎨 UI/UX Professionale
- **Dark/Light Theme** come TradingView
- **Responsive Design** per mobile e desktop
- **Customizable Layout** con drag & drop
- **Performance Optimized** per real-time data

## 🏗️ Architettura

```
├── frontend/          # React + TypeScript + Vite
├── backend/           # Node.js + Express + WebSocket  
├── shared/            # Types e utilities condivise
└── docker/            # Configurazione Docker
```

### 🎯 Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite per build veloce
- Chart.js / D3.js per grafici
- WebSocket per real-time
- Tailwind CSS per styling

**Backend:**
- Node.js + Express + TypeScript
- WebSocket Server per real-time
- MongoDB per persistenza
- Redis per caching
- PM2 per process management

**Infrastructure:**
- Docker + Docker Compose
- Nginx per load balancing
- SSL/TLS encryption
- Health checks e monitoring

## 🚀 Quick Start

### Prerequisiti
- Docker e Docker Compose
- Node.js 18+ (per sviluppo locale)
- Git

### 🔥 Avvio Rapido con Docker

```bash
# Clona il repository
git clone <repository-url>
cd tradingview-clone

# Copia e modifica le variabili d'ambiente  
cp .env.example .env
# Modifica .env con i tuoi valori

# Avvia l'ambiente di sviluppo
docker-compose up -d

# Oppure usa gli script di utilità
./docker-tools.sh dev        # Linux/Mac
.\docker-tools.ps1 dev       # Windows PowerShell
```

### 🌐 Accesso all'Applicazione

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **MongoDB**: localhost:27017
   npm install
   ```

### Running the Application

You can run the application using Docker Compose:

```
docker-compose up
```

Alternatively, you can run the frontend and backend separately:

1. Start the backend:
   ```
   cd backend
   npm run start
   ```

2. Start the frontend:
   ```
   cd frontend
   npm run start
   ```

### Usage

- Access the application in your web browser at `http://localhost:3000`.
- Use the toolbar to select different chart types and indicators.
- Search for market symbols using the sidebar.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.