# Frontend Dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy shared types
COPY shared ./shared

# Copy frontend source code
COPY frontend/ .

# Install Vite globally
RUN npm install -g vite

# Expose port
EXPOSE 3000

# Start command for development
CMD ["npm", "start"]
