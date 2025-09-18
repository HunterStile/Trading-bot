#!/bin/bash
# Script di deploy con Docker per Trading Bot

set -e

echo "🐳 DEPLOY TRADING BOT CON DOCKER"
echo "================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per print colorato
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check se eseguito come root
if [[ $EUID -eq 0 ]]; then
   print_error "Non eseguire questo script come root!"
   print_info "Invece, aggiungi l'utente al gruppo docker:"
   print_info "sudo usermod -aG docker \$USER"
   print_info "newgrp docker"
   exit 1
fi

# 1. Verifica Docker
print_status "Verifica Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker non trovato! Installa Docker prima di continuare"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose non trovato! Installa Docker Compose"
    exit 1
fi

# 2. Verifica permessi Docker
print_status "Verifica permessi Docker..."
if ! docker ps &> /dev/null; then
    print_error "L'utente $(whoami) non ha permessi per Docker!"
    print_info "Esegui questi comandi:"
    print_info "sudo usermod -aG docker $(whoami)"
    print_info "newgrp docker"
    print_info "Poi riavvia il terminale e riprova"
    exit 1
fi

print_status "Docker verificato"

# 2. Verifica directory progetto
PROJECT_DIR=$(pwd)
print_status "Directory progetto: $PROJECT_DIR"

if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    print_error "File Docker mancanti! Assicurati di essere nella directory del Trading-bot"
    exit 1
fi

# 3. Configurazione .env
if [ ! -f ".env" ]; then
    print_status "Configurazione file .env..."
    cp .env.example .env
    
    print_info "Configurazione API keys:"
    read -p "Bybit API Key: " BYBIT_API_KEY
    read -p "Bybit API Secret: " BYBIT_API_SECRET
    read -p "Telegram Token: " TELEGRAM_TOKEN
    read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID
    
    sed -i "s/BYBIT_API_KEY=.*/BYBIT_API_KEY=$BYBIT_API_KEY/" .env
    sed -i "s/BYBIT_API_SECRET=.*/BYBIT_API_SECRET=$BYBIT_API_SECRET/" .env
    sed -i "s/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$TELEGRAM_TOKEN/" .env
    sed -i "s/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID/" .env
    
    print_status "File .env configurato"
else
    print_warning "File .env esistente"
fi

# 4. Crea directory
print_status "Creazione directory..."
mkdir -p data logs backups

# 5. Deploy
print_status "Deploy con Docker..."
docker-compose down 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

print_status "Attendendo avvio..."
sleep 10

print_status "✅ DEPLOY COMPLETATO!"
echo ""
echo "📊 Dashboard: http://$(hostname -I | cut -d' ' -f1):5000"
echo "🔧 Gestione: docker-compose logs -f"
echo ""
print_info "Il bot è pronto!"

if [ "$NGINX_CHOICE" = "2" ]; then
    print_status "Configurazione per Nginx Proxy Manager..."
    COMPOSE_FILE="docker-compose.simple.yml"
    print_info "Useremo docker-compose.simple.yml (solo bot + redis)"
else
    print_status "Configurazione con nginx incluso..."
    COMPOSE_FILE="docker-compose.yml"
    
    # Crea configurazione nginx semplificata
    cat > nginx-simple.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream trading-bot {
        server trading-bot:5000;
    }

    server {
        listen 80;
        server_name _;

        # Proxy settings
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Main application
        location / {
            proxy_pass http://trading-bot;
        }

        # WebSocket support
        location /socket.io/ {
            proxy_pass http://trading-bot;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Health check
        location /health {
            proxy_pass http://trading-bot;
        }
    }
}
EOF
    
    # Usa la configurazione semplificata
    cp nginx-simple.conf nginx.conf
fi==============================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per print colorato
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check se eseguito come root
if [[ $EUID -eq 0 ]]; then
   print_error "Non eseguire questo script come root!"
   exit 1
fi

# 1. Verifica Docker e Docker Compose
print_status "Verifica Docker..."
if ! command -v docker &> /dev/null; then
    print_warning "Docker non trovato, installazione in corso..."
    sudo apt update -y
    sudo apt install -y ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update -y
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    print_status "Docker installato! Rilogga per usare Docker senza sudo"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_warning "Docker Compose non trovato, installazione in corso..."
    sudo apt install -y docker-compose-plugin
fi

print_status "Docker verificato"

# 2. Verifica directory progetto
PROJECT_DIR=$(pwd)
print_status "Directory progetto: $PROJECT_DIR"

# Verifica che siamo nella directory giusta
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    print_error "ERRORE: File Docker mancanti!"
    print_error "Assicurati di essere nella directory del Trading-bot con docker-compose.yml"
    exit 1
fi

print_status "File Docker trovati"

# 3. Configurazione .env
if [ ! -f ".env" ]; then
    print_status "Configurazione file .env..."
    cp .env.example .env
    
    print_info "Configurazione interattiva delle API keys:"
    read -p "Inserisci la tua Bybit API Key: " BYBIT_API_KEY
    read -p "Inserisci la tua Bybit API Secret: " BYBIT_API_SECRET
    read -p "Inserisci il Token del Bot Telegram: " TELEGRAM_TOKEN
    read -p "Inserisci il tuo Chat ID Telegram: " TELEGRAM_CHAT_ID
    
    # Sostituisci nel file .env
    sed -i "s/BYBIT_API_KEY=.*/BYBIT_API_KEY=$BYBIT_API_KEY/" .env
    sed -i "s/BYBIT_API_SECRET=.*/BYBIT_API_SECRET=$BYBIT_API_SECRET/" .env
    sed -i "s/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$TELEGRAM_TOKEN/" .env
    sed -i "s/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID/" .env
    
    print_status "File .env configurato"
else
    print_warning "File .env già esistente - usando configurazione esistente"
fi

# 4. Configurazione dominio per Nginx
read -p "Inserisci il tuo dominio (es. trading.miodominio.com) o premi ENTER per localhost: " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="localhost"
    print_warning "Usando localhost come dominio"
fi

# 5. Crea directory necessarie
print_status "Creazione directory necessarie..."
mkdir -p data logs backups ssl

# 6. Genera certificati SSL self-signed se non esistono
if [ ! -f "ssl/cert.pem" ]; then
    print_status "Generazione certificati SSL self-signed..."
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes 
        -subj "/C=IT/ST=Italy/L=City/O=TradingBot/CN=$DOMAIN" 2>/dev/null || {
        print_warning "OpenSSL non disponibile, SSL disabilitato"
        touch ssl/cert.pem ssl/key.pem
    }
fi

# 5. Setup progetto
PROJECT_DIR=$(pwd)
print_status "Directory progetto corrente: $PROJECT_DIR"

# Verifica che siamo nella directory giusta
if [ ! -f "trading_functions.py" ] || [ ! -f "frontend/app.py" ]; then
    print_error "ERRORE: Questo script deve essere eseguito dalla directory del Trading-bot!"
    print_error "Assicurati di essere in ~/bot/Trading-bot/ e riprova"
    exit 1
fi

print_status "Repository Trading-bot trovata correttamente"

# Aggiorna repository se è un repository git
if [ -d ".git" ]; then
    print_status "Aggiornamento repository..."
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || print_warning "Git pull fallito - continuo comunque"
else
    print_warning "Non è un repository git - continuo senza aggiornamento"
fi

# 6. Setup Python Virtual Environment
print_status "Creazione ambiente virtuale Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# 7. Installazione dipendenze Python
print_status "Installazione dipendenze Python..."
pip install --upgrade pip

# Prova prima con requirements completo
if pip install -r requirements.txt; then
    print_status "Tutte le dipendenze installate con successo"
else
    print_warning "Installazione completa fallita, provo con requirements minimi..."
    if pip install -r requirements-minimal.txt; then
        print_status "Dipendenze minime installate - il bot funzionerà con funzionalità base"
    else
        print_error "Anche l'installazione minima è fallita!"
        print_error "Prova a installare manualmente: pip install Flask Flask-SocketIO pybit requests python-telegram-bot python-dotenv"
        exit 1
    fi
fi

# 8. Configurazione file .env
if [ ! -f ".env" ]; then
    print_status "Configurazione file .env..."
    cp .env.example .env
    print_warning "IMPORTANTE: Configura il file .env con le tue chiavi API!"
    print_warning "File da modificare: $PROJECT_DIR/.env"
    
    # Input interattivo per configurazione base
    read -p "Inserisci la tua Bybit API Key: " BYBIT_API_KEY
    read -p "Inserisci la tua Bybit API Secret: " BYBIT_API_SECRET
    read -p "Inserisci il Token del Bot Telegram: " TELEGRAM_TOKEN
    read -p "Inserisci il tuo Chat ID Telegram: " TELEGRAM_CHAT_ID
    
    # Sostituisci nel file .env
    sed -i "s/BYBIT_API_KEY=.*/BYBIT_API_KEY=$BYBIT_API_KEY/" .env
    sed -i "s/BYBIT_API_SECRET=.*/BYBIT_API_SECRET=$BYBIT_API_SECRET/" .env
    sed -i "s/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$TELEGRAM_TOKEN/" .env
    sed -i "s/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID/" .env
    
    # Configura Chrome solo se installato
    if command -v google-chrome &> /dev/null; then
        sed -i "s|CHROME_DRIVER_PATH=.*|CHROME_DRIVER_PATH=/usr/local/bin/chromedriver|" .env
        sed -i "s|CHROME_BINARY_PATH=.*|CHROME_BINARY_PATH=/usr/bin/google-chrome|" .env
    else
        sed -i "s|CHROME_DRIVER_PATH=.*|CHROME_DRIVER_PATH=|" .env
        sed -i "s|CHROME_BINARY_PATH=.*|CHROME_BINARY_PATH=|" .env
    fi
else
    print_warning "File .env già esistente"
fi

# 9. Test configurazione
print_status "Test configurazione..."
if python3 test_quick.py; then
    print_status "Test configurazione superato!"
else
    print_warning "Test configurazione parziale - il bot potrebbe funzionare con limitazioni"
    print_warning "Controlla le configurazioni nel file .env"
fi

# 10. Configurazione Nginx
print_status "Configurazione Nginx..."

# Controlla se il file default esiste, altrimenti crealo vuoto
if [ ! -f "/etc/nginx/sites-enabled/default" ]; then
    sudo touch /etc/nginx/sites-available/default
    sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
fi

read -p "Inserisci il tuo dominio (es. trading.miodominio.com) o IP del server: " DOMAIN

# Se l'utente non inserisce nulla, usa localhost
if [ -z "$DOMAIN" ]; then
    DOMAIN="localhost"
    print_warning "Usando localhost come dominio predefinito"
fi

sudo tee /etc/nginx/sites-available/trading-bot > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Abilita il sito
sudo ln -sf /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/

# Test configurazione nginx
if sudo nginx -t; then
    print_status "Configurazione Nginx corretta"
    sudo systemctl reload nginx
else
    print_warning "Errore configurazione Nginx - continuo senza nginx"
fi

# 11. Configurazione Supervisor
print_status "Configurazione Supervisor..."
sudo mkdir -p /var/log/trading-bot
sudo chown $USER:$USER /var/log/trading-bot

sudo tee /etc/supervisor/conf.d/trading-bot.conf > /dev/null <<EOF
sudo tee /etc/supervisor/conf.d/trading-bot.conf > /dev/null <<EOF
[program:trading-bot-frontend]
command=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/frontend/app.py
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
stderr_logfile=/var/log/trading-bot/frontend.err.log
stdout_logfile=/var/log/trading-bot/frontend.out.log
environment=PATH="$PROJECT_DIR/venv/bin"

[group:trading-bot]
programs=trading-bot-frontend
EOF
EOF

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start trading-bot-frontend

# 12. Setup SSL con Let's Encrypt (opzionale)
read -p "Vuoi configurare SSL con Let's Encrypt? (y/n): " SETUP_SSL
if [[ $SETUP_SSL == "y" || $SETUP_SSL == "Y" ]]; then
    print_status "Installazione Certbot..."
    sudo apt install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d $DOMAIN
fi

# 7. Test configurazione (opzionale)
read -p "Vuoi testare la configurazione prima del deploy? (y/n): " TEST_CONFIG
if [[ $TEST_CONFIG == "y" || $TEST_CONFIG == "Y" ]]; then
    print_status "Test configurazione..."
    if [ -f "test_robust.py" ]; then
        docker run --rm -v "$PROJECT_DIR:/app" -w /app --env-file .env python:3.9-slim bash -c "
            pip install -q requests pybit python-telegram-bot python-dotenv && 
            python test_robust.py
        " && print_status "Test configurazione superato!" || print_warning "Test configurazione fallito"
    else
        print_warning "File test_robust.py non trovato, salto il test"
    fi
fi

# 8. Ferma container esistenti
print_status "Pulizia container esistenti..."
docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# 9. Build e avvio con Docker Compose
print_status "Build immagini Docker..."
docker-compose -f $COMPOSE_FILE build --no-cache

print_status "Avvio servizi con Docker..."
docker-compose -f $COMPOSE_FILE up -d

# 10. Attendi che i servizi siano pronti
print_status "Attendendo avvio servizi..."
sleep 15

# 11. Controllo stato servizi
print_status "Controllo stato servizi..."
docker-compose -f $COMPOSE_FILE ps

# 12. Test connettività
print_status "Test connettività..."
if curl -f -s http://localhost:5000 > /dev/null; then
    print_status "✅ Trading Bot risponde correttamente!"
else
    print_warning "⚠️ Trading Bot non risponde, controlla i log"
fi

# 13. Informazioni Nginx Proxy Manager
if [ "$NGINX_CHOICE" = "2" ]; then
    print_info ""
    print_info "� CONFIGURAZIONE NGINX PROXY MANAGER:"
    print_info "   1. Accedi al tuo Nginx Proxy Manager"
    print_info "   2. Aggiungi nuovo Proxy Host:"
    print_info "      - Domain Names: il-tuo-dominio.com"
    print_info "      - Forward Hostname/IP: IP_DI_QUESTO_SERVER"
    print_info "      - Forward Port: 5000"
    print_info "      - Websockets Support: ON"
    print_info "   3. Nella tab SSL:"
    print_info "      - SSL Certificate: Request new SSL Certificate"
    print_info "      - Use Let's Encrypt: ON"
    print_info "      - Email: tua-email@domain.com"
    print_info "      - Agree to Terms: ON"
else
    print_info ""
    print_info "🌐 NGINX INCLUSO:"
    print_info "   Il bot include nginx interno per test rapidi"
    print_info "   Per produzione, usa Nginx Proxy Manager"
fi

# 14. Creazione script di gestione Docker
print_status "Creazione script di gestione..."

# Script di gestione Docker
cat > docker-manage.sh << 'EOF'
#!/bin/bash
# Script di gestione Docker per Trading Bot

case "$1" in
    start)
        echo "🚀 Avvio Trading Bot..."
        docker-compose up -d
        echo "✅ Trading Bot avviato!"
        ;;
    stop)
        echo "🛑 Fermando Trading Bot..."
        docker-compose down
        echo "✅ Trading Bot fermato!"
        ;;
    restart)
        echo "� Riavvio Trading Bot..."
        docker-compose down
        docker-compose up -d
        echo "✅ Trading Bot riavviato!"
        ;;
    logs)
        echo "� Log Trading Bot:"
        docker-compose logs -f --tail=50
        ;;
    status)
        echo "📊 Stato Trading Bot:"
        docker-compose ps
        echo ""
        echo "� Utilizzo risorse:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ;;
    update)
        echo "� Aggiornamento Trading Bot..."
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "Git pull fallito"
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        echo "✅ Aggiornamento completato!"
        ;;
    backup)
        BACKUP_DIR="./backups"
        DATE=$(date +%Y%m%d_%H%M%S)
        mkdir -p $BACKUP_DIR
        echo "� Backup in corso..."
        
        # Backup database dai container
        docker-compose exec trading-bot cp /app/data/trading_data.db /app/backups/trading_data_$DATE.db 2>/dev/null || true
        docker-compose exec trading-bot cp /app/data/bot_state.db /app/backups/bot_state_$DATE.db 2>/dev/null || true
        
        # Backup configurazione
        cp .env $BACKUP_DIR/env_$DATE.backup
        
        # Comprimi backup
        tar -czf $BACKUP_DIR/backup_$DATE.tar.gz -C $BACKUP_DIR *_$DATE.*
        rm $BACKUP_DIR/*_$DATE.* 2>/dev/null || true
        
        echo "✅ Backup completato: $BACKUP_DIR/backup_$DATE.tar.gz"
        ;;
    clean)
        echo "🧹 Pulizia sistema Docker..."
        docker-compose down
        docker system prune -f
        docker volume prune -f
        echo "✅ Pulizia completata!"
        ;;
    *)
        echo "🐳 Trading Bot Docker Manager"
        echo "Utilizzo: $0 {start|stop|restart|logs|status|update|backup|clean}"
        echo ""
        echo "Comandi disponibili:"
        echo "  start   - Avvia il Trading Bot"
        echo "  stop    - Ferma il Trading Bot"
        echo "  restart - Riavvia il Trading Bot"
        echo "  logs    - Mostra i log in tempo reale"
        echo "  status  - Mostra stato e risorse"
        echo "  update  - Aggiorna e ricostruisce"
        echo "  backup  - Crea backup dei dati"
        echo "  clean   - Pulisce il sistema Docker"
        exit 1
        ;;
esac
EOF

chmod +x docker-manage.sh

# 16. RISULTATI FINALI
print_status "✅ DEPLOY DOCKER COMPLETATO!"
echo ""
echo "🎉 Il tuo Trading Bot è ora attivo con Docker!"
echo ""
echo "🌐 ACCESSO:"
echo "   📊 Dashboard: http://localhost:5000"
echo "   � Dashboard (via nginx): http://IP_DEL_SERVER"
echo "   � Per domini esterni: usa Nginx Proxy Manager"
echo ""
echo "🔧 GESTIONE:"
echo "   ./docker-manage.sh start    - Avvia bot"
echo "   ./docker-manage.sh stop     - Ferma bot"
echo "   ./docker-manage.sh restart  - Riavvia bot"
echo "   ./docker-manage.sh logs     - Mostra log"
echo "   ./docker-manage.sh status   - Stato servizi"
echo "   ./docker-manage.sh update   - Aggiorna bot"
echo "   ./docker-manage.sh backup   - Backup dati"
echo ""
echo "📊 MONITORING:"
echo "   docker-compose ps           - Stato container"
echo "   docker-compose logs -f      - Log in tempo reale"
echo "   docker stats                - Utilizzo risorse"
echo ""
echo "📁 DIRECTORY:"
echo "   Progetto: $PROJECT_DIR"
echo "   Dati: $PROJECT_DIR/data/"
echo "   Log: $PROJECT_DIR/logs/"
echo "   Backup: $PROJECT_DIR/backups/"
echo ""
print_warning "NEXT STEPS:"
print_warning "1. Verifica che .env sia configurato correttamente"
print_warning "2. Accedi alla dashboard per testare il bot"
print_warning "3. Configura SSL se stai usando un dominio pubblico"
print_warning "4. Monitora i log per eventuali errori"
echo ""
print_info "🚀 Il bot è pronto! Buon trading! 📈"
