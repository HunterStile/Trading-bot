#!/bin/bash
# Script di deploy con Docker

set -e

echo "🐳 Deploy Trading Bot con Docker"
echo "================================="

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check Docker e Docker Compose
if ! command -v docker &> /dev/null; then
    print_error "Docker non installato!"
    print_warning "Installa Docker: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose non installato!"
    print_warning "Installa Docker Compose: sudo apt install docker-compose-plugin"
    exit 1
fi

# Controllo file .env
if [ ! -f ".env" ]; then
    print_warning "File .env mancante, copio da .env.example"
    cp .env.example .env
    print_error "CONFIGURA IL FILE .env PRIMA DI CONTINUARE!"
    exit 1
fi

# Crea directory necessarie
print_status "Creazione directory..."
mkdir -p data logs backups ssl

# Setup SSL self-signed per sviluppo (sostituisci con certificati reali)
if [ ! -f "ssl/cert.pem" ]; then
    print_status "Generazione certificati SSL self-signed..."
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=IT/ST=IT/L=City/O=TradingBot/CN=localhost"
fi

# Build e avvio
print_status "Build immagini Docker..."
docker-compose build

print_status "Avvio servizi..."
docker-compose up -d

# Attendi che i servizi siano pronti
print_status "Attendendo avvio servizi..."
sleep 10

# Controllo stato
print_status "Controllo stato servizi..."
docker-compose ps

print_status "✅ Deploy completato!"
echo ""
echo "🎉 Trading Bot avviato con Docker!"
echo ""
echo "📊 Dashboard: https://localhost (o http://localhost)"
echo "🔧 Controllo: docker-compose logs -f trading-bot"
echo "📋 Status: docker-compose ps"
echo ""
echo "💡 Comandi utili:"
echo "   - Restart: docker-compose restart"
echo "   - Stop: docker-compose down"
echo "   - Logs: docker-compose logs -f"
echo "   - Rebuild: docker-compose build --no-cache"
