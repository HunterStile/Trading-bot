# Backend Dockerfile
FROM node:18-alpine

# Install Python and pip for PyBit integration
RUN apk add --no-cache python3 py3-pip

# Set working directory
WORKDIR /app

# Copy package files
COPY ChartTrading/tradingview-clone/backend/package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy Python trading functions and requirements from main project
COPY trading_functions.py ./
COPY config.py ./
COPY requirements.txt ./

# Install Python dependencies (use --break-system-packages for Docker)
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy shared types
COPY ChartTrading/tradingview-clone/shared ./shared

# Copy backend source code
COPY ChartTrading/tradingview-clone/backend/ .

# Install ts-node globally for development
RUN npm install -g ts-node ts-node-dev

# Expose port
EXPOSE 5000

# Start command for development
CMD ["npm", "run", "dev"]
