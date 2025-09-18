# Trading Bot - Installazione e Deploy in Produzione

## 📋 Requisiti di Sistema

### Sistema Operativo
- Ubuntu 18.04+ / CentOS 7+ / Debian 9+
- Python 3.8+
- Node.js 16+ (per eventuali frontend)

### Hardware Minimo
- CPU: 2 core
- RAM: 4GB
- Spazio disco: 10GB liberi
- Connessione internet stabile

## 🚀 Guida Completa per Deploy in Produzione

### 1. Preparazione del Server

```bash
# Aggiorna il sistema
sudo apt update && sudo apt upgrade -y

# Installa dipendenze di sistema
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor redis-server

# Installa Google Chrome (per Selenium)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Installa ChromeDriver
CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -N http://chromedriver.storage.googleapis.com//$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip
```

### 2. Setup Utente di Sistema

```bash
# Crea utente dedicato per il trading bot
sudo adduser tradingbot
sudo usermod -aG sudo tradingbot

# Passa all'utente tradingbot
sudo su - tradingbot
```

### 3. Clone e Configurazione del Progetto

```bash
# Clone del repository
cd /home/tradingbot
git clone https://github.com/TUO_USERNAME/Trading-bot.git
cd Trading-bot

# Crea ambiente virtuale Python
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze Python
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurazione Ambiente

```bash
# Copia e configura file di ambiente
cp .env.example .env
nano .env
```

Modifica il file `.env` con le tue configurazioni reali:
```bash
# API Bybit
BYBIT_API_KEY=la_tua_vera_api_key
BYBIT_API_SECRET=la_tua_vera_secret_key

# Telegram
TELEGRAM_TOKEN=il_tuo_token_telegram
TELEGRAM_CHAT_ID=il_tuo_chat_id

# Configurazione Browser per produzione
CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
CHROME_BINARY_PATH=/usr/bin/google-chrome
```

### 5. Configurazione Database

```bash
# Il bot userà SQLite by default, ma per produzione è meglio PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Crea database e utente
sudo -u postgres psql
CREATE DATABASE trading_bot;
CREATE USER tradingbot WITH ENCRYPTED PASSWORD 'password_sicura';
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO tradingbot;
\q
```

### 6. Configurazione Nginx (Reverse Proxy)

```bash
sudo nano /etc/nginx/sites-available/trading-bot
```

Contenuto del file nginx:
```nginx
server {
    listen 80;
    server_name il_tuo_dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Abilita il sito
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Configurazione SSL con Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d il_tuo_dominio.com
```

### 8. Configurazione Supervisor per Gestione Processi

```bash
sudo nano /etc/supervisor/conf.d/trading-bot.conf
```

Contenuto del file supervisor:
```ini
[program:trading-bot-frontend]
command=/home/tradingbot/Trading-bot/venv/bin/python /home/tradingbot/Trading-bot/frontend/app.py
directory=/home/tradingbot/Trading-bot
user=tradingbot
autostart=true
autorestart=true
stderr_logfile=/var/log/trading-bot/frontend.err.log
stdout_logfile=/var/log/trading-bot/frontend.out.log
environment=PATH="/home/tradingbot/Trading-bot/venv/bin"

[program:trading-bot-worker]
command=/home/tradingbot/Trading-bot/venv/bin/python /home/tradingbot/Trading-bot/Apertura\ e\ chiusura\ operazioni.py
directory=/home/tradingbot/Trading-bot
user=tradingbot
autostart=false
autorestart=true
stderr_logfile=/var/log/trading-bot/worker.err.log
stdout_logfile=/var/log/trading-bot/worker.out.log
environment=PATH="/home/tradingbot/Trading-bot/venv/bin"

[group:trading-bot]
programs=trading-bot-frontend,trading-bot-worker
```

```bash
# Crea directory per i log
sudo mkdir -p /var/log/trading-bot
sudo chown tradingbot:tradingbot /var/log/trading-bot

# Ricarica configurazione supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start trading-bot-frontend
```

### 9. Script di Deploy Automatico

Crea uno script per automatizzare i deploy:

```bash
nano /home/tradingbot/deploy.sh
```

```bash
#!/bin/bash
# Script di deploy automatico

set -e

echo "🚀 Inizio deploy Trading Bot..."

# Vai nella directory del progetto
cd /home/tradingbot/Trading-bot

# Ferma i processi
sudo supervisorctl stop trading-bot:*

# Pull delle modifiche
git pull origin main

# Attiva environment virtuale
source venv/bin/activate

# Aggiorna dipendenze se necessario
pip install -r requirements.txt

# Backup del database
cp trading_data.db trading_data.db.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Riavvia i servizi
sudo supervisorctl start trading-bot-frontend

echo "✅ Deploy completato!"
echo "📊 Dashboard: https://il_tuo_dominio.com"
echo "📋 Status: sudo supervisorctl status trading-bot:*"
```

```bash
chmod +x /home/tradingbot/deploy.sh
```

### 10. Monitoraggio e Logging

```bash
# Script di monitoraggio
nano /home/tradingbot/monitor.sh
```

```bash
#!/bin/bash
# Script di monitoraggio

echo "📊 STATO TRADING BOT"
echo "===================="

echo ""
echo "🔧 Processi Supervisor:"
sudo supervisorctl status trading-bot:*

echo ""
echo "🌐 Nginx Status:"
sudo systemctl status nginx --no-pager

echo ""
echo "💾 Spazio Disco:"
df -h /home/tradingbot

echo ""
echo "🐍 Processi Python:"
ps aux | grep python | grep -v grep

echo ""
echo "📝 Ultimi Log Frontend (ultimi 10 righe):"
tail -n 10 /var/log/trading-bot/frontend.out.log

echo ""
echo "⚠️ Errori Frontend (ultimi 5 righe):"
tail -n 5 /var/log/trading-bot/frontend.err.log
```

```bash
chmod +x /home/tradingbot/monitor.sh
```

### 11. Backup Automatico

```bash
nano /home/tradingbot/backup.sh
```

```bash
#!/bin/bash
# Script di backup automatico

BACKUP_DIR="/home/tradingbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "📦 Inizio backup Trading Bot..."

# Backup database
cp /home/tradingbot/Trading-bot/trading_data.db $BACKUP_DIR/trading_data_$DATE.db 2>/dev/null || true
cp /home/tradingbot/Trading-bot/bot_state.db $BACKUP_DIR/bot_state_$DATE.db 2>/dev/null || true

# Backup configurazioni
cp /home/tradingbot/Trading-bot/.env $BACKUP_DIR/env_$DATE.backup
cp /home/tradingbot/Trading-bot/config.py $BACKUP_DIR/config_$DATE.py 2>/dev/null || true

# Backup custom symbols
cp /home/tradingbot/Trading-bot/custom_symbols.json $BACKUP_DIR/custom_symbols_$DATE.json 2>/dev/null || true

# Comprimi e pulisci backup vecchi (mantieni ultimi 30 giorni)
cd $BACKUP_DIR
tar -czf backup_$DATE.tar.gz *_$DATE.*
rm *_$DATE.db *_$DATE.backup *_$DATE.py *_$DATE.json 2>/dev/null || true

# Rimuovi backup più vecchi di 30 giorni
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "✅ Backup completato: $BACKUP_DIR/backup_$DATE.tar.gz"
```

```bash
chmod +x /home/tradingbot/backup.sh

# Aggiungi al crontab per backup automatico
crontab -e
# Aggiungi questa riga per backup giornaliero alle 2:00
0 2 * * * /home/tradingbot/backup.sh
```

## 🔧 Comandi Utili per la Gestione

### Controllo Stato
```bash
# Stato generale
./monitor.sh

# Log in tempo reale
sudo supervisorctl tail -f trading-bot-frontend stdout
sudo supervisorctl tail -f trading-bot-frontend stderr

# Restart servizi
sudo supervisorctl restart trading-bot:*
```

### Deploy Aggiornamenti
```bash
# Deploy automatico
./deploy.sh

# Deploy manuale
cd /home/tradingbot/Trading-bot
git pull
sudo supervisorctl restart trading-bot-frontend
```

### Backup e Ripristino
```bash
# Backup manuale
./backup.sh

# Ripristino
cd /home/tradingbot/Trading-bot
cp /home/tradingbot/backups/trading_data_YYYYMMDD_HHMMSS.db trading_data.db
sudo supervisorctl restart trading-bot-frontend
```

## 🛡️ Sicurezza

### Firewall
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### Aggiornamenti Automatici
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

### Monitoraggio Risorse
```bash
# Installa htop per monitoraggio
sudo apt install -y htop

# Configura logrotate per i log del bot
sudo nano /etc/logrotate.d/trading-bot
```

Contenuto logrotate:
```
/var/log/trading-bot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

## 📱 Accesso alla Dashboard

Dopo il deploy, la dashboard sarà accessibile a:
- **HTTP**: http://il_tuo_dominio.com
- **HTTPS**: https://il_tuo_dominio.com (con SSL)

### URL Principali:
- Dashboard principale: `/`
- Controllo Bot: `/control`
- Test API: `/api-test`
- Grafici Backtest: `/static/charts/`

## 🚨 Troubleshooting

### Problemi Comuni
1. **Bot non si avvia**: Controlla log con `sudo supervisorctl tail trading-bot-frontend stderr`
2. **Errori API**: Verifica chiavi nel file `.env`
3. **Dashboard non raggiungibile**: Controlla nginx con `sudo systemctl status nginx`
4. **Database locked**: Riavvia il bot con `sudo supervisorctl restart trading-bot-frontend`

### Log Location
- Frontend: `/var/log/trading-bot/frontend.out.log`
- Errori: `/var/log/trading-bot/frontend.err.log`
- Nginx: `/var/log/nginx/access.log` e `/var/log/nginx/error.log`
