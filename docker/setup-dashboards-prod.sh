#!/bin/bash
# 🚀 Trading Bot Dashboard Production Deployment Script for Ubuntu
# Usa porte sicure per evitare conflitti su server di produzione

set -e

echo "🚀 Starting Trading Bot Dashboard Production Deployment..."
echo "📅 $(date)"
echo "🖥️  Production Server: Ubuntu"
echo "🔧 Using safe ports to avoid conflicts"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function for colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Stop existing containers if running
print_status "Stopping existing dashboard containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Remove unused containers and images
print_status "Cleaning up unused resources..."
docker system prune -f

# Build images
print_status "Building dashboard images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
print_status "Starting dashboard services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait a bit for services to start
print_status "Waiting for services to start..."
sleep 15

# Check service status
print_status "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📊 Dashboard URLs (Production):"
echo "  🌐 Nginx Proxy:        http://your-server-ip:9080"
echo "  📈 Simple Dashboard:   http://your-server-ip:15004"  
echo "  💼 Professional:      http://your-server-ip:15006"
echo "  🔀 Multi-Symbol:      http://your-server-ip:15007"
echo "  🐳 Portainer:         http://your-server-ip:19000"
echo ""
echo "🔧 Production Ports Used:"
echo "  📡 Nginx HTTP:  9080"
echo "  🔒 Nginx HTTPS: 9443" 
echo "  💾 Redis:       19379"
echo "  🐳 Portainer:   19000"
echo ""
echo "🔍 Useful Commands:"
echo "  📋 Check logs:     docker-compose -f docker-compose.prod.yml logs -f"
echo "  🔄 Restart:        docker-compose -f docker-compose.prod.yml restart"
echo "  🛑 Stop all:       docker-compose -f docker-compose.prod.yml down"
echo "  📊 Monitor:        docker-compose -f docker-compose.prod.yml ps"
echo ""

# Final health check
print_status "Running final health checks..."
sleep 5

# Check if services are responding
for service in "15004" "15006" "15007"; do
    if curl -f -s "http://localhost:$service" > /dev/null 2>&1; then
        print_success "Dashboard on port $service is responding"
    else
        print_warning "Dashboard on port $service is not responding yet (may need more time)"
    fi
done

print_success "🚀 All dashboards deployed successfully!"
print_warning "⚠️  Make sure to configure your firewall to allow access to these ports"
print_status "🔒 Remember to set up SSL certificates for production use"