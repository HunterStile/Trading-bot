#!/bin/bash
# Script di deploy rapido per Trading Bot

set -e

echo "🚀 DEPLOY TRADING BOT - SETUP AUTOMATICO"
echo "========================================"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check se eseguito come root
if [[ $EUID -eq 0 ]]; then
   print_error "Non eseguire questo script come root!"
   exit 1
fi

# 1. Aggiornamento sistema
print_status "Aggiornamento sistema..."
sudo apt update -y

# 2. Installazione dipendenze di sistema
print_status "Installazione dipendenze di sistema..."
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor redis-server curl wget unzip

# 3. Installazione Google Chrome (OPZIONALE - solo per scraping)
read -p "Vuoi installare Chrome per le funzioni di scraping? (y/n): " INSTALL_CHROME
if [[ $INSTALL_CHROME == "y" || $INSTALL_CHROME == "Y" ]]; then
    print_status "Installazione Google Chrome..."
    if ! command -v google-chrome &> /dev/null; then
        # Prova prima l'installazione normale
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add - 2>/dev/null || true
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
        sudo apt update
        
        if sudo apt install -y google-chrome-stable; then
            print_status "Chrome installato con successo"
        else
            print_warning "Installazione Chrome fallita - continuo senza Chrome"
            print_warning "Il bot funzionerà comunque per il trading (senza scraping)"
        fi
    else
        print_warning "Chrome già installato"
    fi

    # 4. Installazione ChromeDriver (solo se Chrome è installato)
    if command -v google-chrome &> /dev/null; then
        print_status "Installazione ChromeDriver..."
        if ! command -v chromedriver &> /dev/null; then
            CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE 2>/dev/null || echo "114.0.5735.90")
            wget -N http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip -O /tmp/chromedriver.zip 2>/dev/null || true
            if [ -f "/tmp/chromedriver.zip" ]; then
                unzip /tmp/chromedriver.zip -d /tmp/
                sudo mv /tmp/chromedriver /usr/local/bin/ 2>/dev/null || true
                sudo chmod +x /usr/local/bin/chromedriver 2>/dev/null || true
                rm /tmp/chromedriver.zip 2>/dev/null || true
                print_status "ChromeDriver installato"
            else
                print_warning "Download ChromeDriver fallito - configura manualmente se necessario"
            fi
        else
            print_warning "ChromeDriver già installato"
        fi
    fi
else
    print_warning "Chrome NON installato - il bot funzionerà senza scraping"
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

# 13. Creazione script di gestione
print_status "Creazione script di gestione..."

# Script di deploy
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e
echo "🚀 Deploy Trading Bot..."
PROJECT_DIR=$(pwd)
cd $PROJECT_DIR
sudo supervisorctl stop trading-bot:* 2>/dev/null || true
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "Git pull fallito"
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl start trading-bot:* 2>/dev/null || echo "Supervisor non configurato"
echo "✅ Deploy completato!"
EOF

# Script di monitoraggio
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "📊 STATO TRADING BOT"
echo "===================="
echo ""
echo "🔧 Processi:"
sudo supervisorctl status trading-bot:*
echo ""
echo "🌐 Nginx:"
sudo systemctl status nginx --no-pager -l
echo ""
echo "📝 Log Frontend (ultime 10 righe):"
tail -n 10 /var/log/trading-bot/frontend.out.log
echo ""
echo "⚠️ Errori (ultime 5 righe):"
tail -n 5 /var/log/trading-bot/frontend.err.log
EOF

# Script di backup
cat > backup.sh << 'EOF'
#!/bin/bash
PROJECT_DIR=$(pwd)
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
echo "📦 Backup in corso..."
cp trading_data.db $BACKUP_DIR/trading_data_$DATE.db 2>/dev/null || true
cp bot_state.db $BACKUP_DIR/bot_state_$DATE.db 2>/dev/null || true
cp .env $BACKUP_DIR/env_$DATE.backup
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz -C $BACKUP_DIR *_$DATE.*
rm $BACKUP_DIR/*_$DATE.db $BACKUP_DIR/*_$DATE.backup 2>/dev/null || true
echo "✅ Backup: $BACKUP_DIR/backup_$DATE.tar.gz"
EOF

chmod +x deploy.sh monitor.sh backup.sh

# 14. Setup cron per backup automatico
print_status "Setup backup automatico..."
CURRENT_DIR=$(pwd)
(crontab -l 2>/dev/null; echo "0 2 * * * cd $CURRENT_DIR && ./backup.sh") | crontab -

# 15. Configurazione firewall
print_status "Configurazione firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

print_status "✅ SETUP COMPLETATO!"
echo ""
echo "🎉 Il tuo Trading Bot è ora configurato in produzione!"
echo ""
echo "📊 Dashboard: http://$DOMAIN (o https se hai configurato SSL)"
echo "🔧 Controllo: sudo supervisorctl status trading-bot:*"
echo "📋 Monitor: ./monitor.sh"
echo "🚀 Deploy: ./deploy.sh"
echo "📦 Backup: ./backup.sh"
echo ""
echo "📁 Directory progetto: $PROJECT_DIR"
echo "📝 Log: /var/log/trading-bot/"
echo ""
print_warning "IMPORTANTE:"
print_warning "1. Configura il file .env con le tue chiavi API reali"
print_warning "2. Testa la connessione con: python3 test_api.py"
print_warning "3. Monitora i log per errori: tail -f /var/log/trading-bot/frontend.out.log"
print_warning "4. Per avviare il bot: accedi alla dashboard e usa il pannello di controllo"
