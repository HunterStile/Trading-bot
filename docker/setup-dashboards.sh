#!/bin/bash

# Setup Docker per Trading Bot Dashboards
# Questo script configura e avvia tutti i servizi dashboard in Docker

set -e

echo "🚀 Setting up Trading Bot Dashboards with Docker..."

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function per print colorati
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

# Controllo se Docker è installato
if ! command -v docker &> /dev/null; then
    print_error "Docker non è installato. Installa Docker prima di continuare."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose non è installato. Installa Docker Compose prima di continuare."
    exit 1
fi

# Vai nella directory del progetto
cd "$(dirname "$0")/.."

print_status "Working directory: $(pwd)"

# Crea directory necessarie
print_status "Creando directory necessarie..."
mkdir -p data logs backups docker/ssl

# Copia i file dashboard se non esistono già
print_status "Verificando file dashboard..."

if [ ! -f "simple_dashboard.py" ]; then
    print_warning "simple_dashboard.py non trovato nella root directory"
fi

if [ ! -f "professional_dashboard.py" ]; then
    print_warning "professional_dashboard.py non trovato nella root directory"
fi

if [ ! -f "multi_symbol_dashboard.py" ]; then
    print_warning "multi_symbol_dashboard.py non trovato nella root directory"
fi

# Crea file .env se non esiste
if [ ! -f ".env" ]; then
    print_status "Creando file .env..."
    cat > .env << EOF
# Trading Bot Dashboards Environment Variables
FLASK_ENV=production
PYTHONPATH=/app
PYTHONUNBUFFERED=1
REDIS_PASSWORD=dashboards2024

# Optional: API Keys (se necessario per future integrazioni)
# BYBIT_API_KEY=your_api_key
# BYBIT_SECRET=your_secret
# TELEGRAM_BOT_TOKEN=your_bot_token
EOF
    print_success "File .env creato"
else
    print_status "File .env già esistente"
fi

# Ferma eventuali container esistenti
print_status "Fermando container esistenti..."
cd docker
docker-compose -f docker-compose.dashboards.yml down 2>/dev/null || true

# Pulisci immagini vecchie (opzionale)
read -p "Vuoi rimuovere le immagini Docker esistenti? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Rimuovendo immagini vecchie..."
    docker system prune -f
fi

# Build delle immagini
print_status "Building immagini Docker..."
docker-compose -f docker-compose.dashboards.yml build --no-cache

# Avvia i servizi
print_status "Avviando servizi dashboard..."
docker-compose -f docker-compose.dashboards.yml up -d

# Attendi che i servizi si avviino
print_status "Attendendo avvio servizi..."
sleep 15

# Controllo health dei servizi
print_status "Controllando health dei servizi..."

services=("dashboard-multi-simple:5007" "dashboard-professional:5006" "dashboard-simple:5004" "dashboard-fixed:5003")

for service in "${services[@]}"; do
    container_name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if docker ps | grep -q $container_name; then
        if curl -f http://localhost:$port/debug &>/dev/null || curl -f http://localhost:$port/ &>/dev/null; then
            print_success "$container_name è online (porta $port)"
        else
            print_warning "$container_name è running ma non risponde su porta $port"
        fi
    else
        print_error "$container_name non è in running"
    fi
done

# Status finale
print_success "Setup Docker completato!"
echo ""
echo "🌐 Servizi disponibili:"
echo "  • Multi-Symbol Dashboard:  http://localhost/ (porta 80, proxy)"
echo "  • Dashboard Professionale: http://localhost/professional"  
echo "  • Dashboard Semplice:      http://localhost/simple"
echo "  • Dashboard Fixed:         http://localhost/fixed"
echo ""
echo "🔗 Accesso diretto:"
echo "  • Multi-Symbol: http://localhost:5007"
echo "  • Professionale: http://localhost:5006"  
echo "  • Semplice: http://localhost:5004"
echo "  • Fixed: http://localhost:5003"
echo ""
echo "🛠️ Monitoring:"
echo "  • Portainer: http://localhost:9000 (admin/admin123)"
echo "  • Redis: localhost:6379 (password: dashboards2024)"
echo ""
echo "📊 Comandi utili:"
echo "  • docker-compose -f docker-compose.dashboards.yml logs -f"
echo "  • docker-compose -f docker-compose.dashboards.yml restart"
echo "  • docker-compose -f docker-compose.dashboards.yml down"
echo ""
print_success "Enjoy your trading dashboards! 🚀📈"