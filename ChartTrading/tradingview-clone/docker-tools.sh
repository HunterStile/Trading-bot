#!/bin/bash

# Script di utilità per gestire l'applicazione TradingView Clone

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utilità
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Funzione di help
show_help() {
    cat << EOF
🔧 TradingView Clone - Docker Management Script

USAGE:
    ./docker-tools.sh [COMMAND] [OPTIONS]

COMMANDS:
    dev                 Avvia l'ambiente di sviluppo
    prod                Avvia l'ambiente di produzione
    build               Build delle immagini Docker
    clean               Pulisce containers e immagini
    logs                Mostra i logs dei servizi
    restart             Riavvia i servizi
    stop                Ferma tutti i servizi
    status              Mostra lo stato dei servizi
    shell-backend       Apre una shell nel container backend
    shell-frontend      Apre una shell nel container frontend
    backup-db           Crea un backup del database
    restore-db          Ripristina il database da backup

EXAMPLES:
    ./docker-tools.sh dev           # Avvia ambiente di sviluppo
    ./docker-tools.sh prod          # Avvia ambiente di produzione
    ./docker-tools.sh logs backend  # Mostra logs del backend
    ./docker-tools.sh clean         # Pulisce tutto

EOF
}

# Funzione per sviluppo
start_dev() {
    print_info "Avvio ambiente di sviluppo..."
    docker-compose -f docker-compose.yml up -d
    print_success "Ambiente di sviluppo avviato!"
    print_info "Frontend: http://localhost:3000"
    print_info "Backend: http://localhost:5000"
    print_info "MongoDB: localhost:27017"
}

# Funzione per produzione
start_prod() {
    print_info "Avvio ambiente di produzione..."
    
    # Controlla se esiste .env
    if [ ! -f .env ]; then
        print_warning "File .env non trovato. Copio .env.example..."
        cp .env.example .env
        print_warning "⚠️ IMPORTANTE: Modifica il file .env con i tuoi valori reali!"
        read -p "Premi Enter per continuare quando hai modificato .env..."
    fi
    
    docker-compose -f docker-compose.prod.yml up -d
    print_success "Ambiente di produzione avviato!"
    print_info "Applicazione: http://localhost"
    print_info "API: http://localhost:5000"
}

# Build delle immagini
build_images() {
    print_info "Build delle immagini Docker..."
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.prod.yml build
    print_success "Build completato!"
}

# Pulizia
clean_all() {
    print_warning "Pulizia containers e immagini..."
    docker-compose -f docker-compose.yml down -v --rmi all
    docker-compose -f docker-compose.prod.yml down -v --rmi all
    docker system prune -f
    print_success "Pulizia completata!"
}

# Logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Restart
restart_services() {
    print_info "Riavvio servizi..."
    docker-compose restart
    print_success "Servizi riavviati!"
}

# Stop
stop_services() {
    print_info "Arresto servizi..."
    docker-compose down
    docker-compose -f docker-compose.prod.yml down
    print_success "Servizi arrestati!"
}

# Status
show_status() {
    print_info "Stato dei servizi:"
    docker-compose ps
    echo ""
    docker-compose -f docker-compose.prod.yml ps
}

# Shell backend
shell_backend() {
    print_info "Apertura shell nel container backend..."
    docker-compose exec backend sh
}

# Shell frontend
shell_frontend() {
    print_info "Apertura shell nel container frontend..."
    docker-compose exec frontend sh
}

# Backup database
backup_db() {
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    print_info "Creazione backup database: $backup_name"
    docker-compose exec mongo mongodump --db tradingview_clone --out /tmp/$backup_name
    docker cp $(docker-compose ps -q mongo):/tmp/$backup_name ./backups/
    print_success "Backup creato: ./backups/$backup_name"
}

# Restore database
restore_db() {
    local backup_dir=$1
    if [ -z "$backup_dir" ]; then
        print_error "Specifica la directory del backup"
        echo "Uso: ./docker-tools.sh restore-db <backup_directory>"
        exit 1
    fi
    
    print_warning "Ripristino database da: $backup_dir"
    read -p "Sei sicuro? Questo sovrascriverà il database esistente [y/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker cp ./backups/$backup_dir $(docker-compose ps -q mongo):/tmp/
        docker-compose exec mongo mongorestore --db tradingview_clone --drop /tmp/$backup_dir/tradingview_clone
        print_success "Database ripristinato!"
    else
        print_info "Operazione annullata"
    fi
}

# Main switch
case $1 in
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    build)
        build_images
        ;;
    clean)
        clean_all
        ;;
    logs)
        show_logs $2
        ;;
    restart)
        restart_services
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    shell-backend)
        shell_backend
        ;;
    shell-frontend)
        shell_frontend
        ;;
    backup-db)
        backup_db
        ;;
    restore-db)
        restore_db $2
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Comando non riconosciuto: $1"
        show_help
        exit 1
        ;;
esac
