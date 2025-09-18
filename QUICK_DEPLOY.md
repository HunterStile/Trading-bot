# 🚀 Guida Rapida di Deploy - Trading Bot

## 📋 Opzioni di Deploy

### 1. 🐳 Deploy con Docker (Raccomandato)
```bash
# Clone del repository
git clone https://github.com/TUO_USERNAME/Trading-bot.git
cd Trading-bot

# Configura .env
cp .env.example .env
nano .env  # Inserisci le tue chiavi API

# Deploy automatico
chmod +x docker-deploy.sh
./docker-deploy.sh
```

**Accesso**: https://localhost

### 2. 🖥️ Deploy Manuale su Server
```bash
# Download script di deploy
wget https://raw.githubusercontent.com/TUO_USERNAME/Trading-bot/main/deploy.sh
chmod +x deploy.sh

# Esegui setup automatico
./deploy.sh
```

### 3. 📱 Deploy su VPS/Cloud

#### DigitalOcean / Vultr / AWS EC2
```bash
# Crea droplet Ubuntu 20.04+
# Connetti via SSH
ssh root@TUO_IP

# Esegui setup
curl -fsSL https://raw.githubusercontent.com/TUO_USERNAME/Trading-bot/main/deploy.sh | bash
```

## ⚙️ Configurazione Rapida

### 1. File .env Obbligatorio
```bash
# API Bybit (OBBLIGATORIO)
BYBIT_API_KEY=la_tua_api_key
BYBIT_API_SECRET=la_tua_secret_key

# Telegram (OBBLIGATORIO per notifiche)
TELEGRAM_TOKEN=il_tuo_bot_token
TELEGRAM_CHAT_ID=il_tuo_chat_id

# Browser (auto-configurato)
CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
CHROME_BINARY_PATH=/usr/bin/google-chrome
```

### 2. Test Configurazione
```bash
python3 test_api.py
```

## 🔧 Gestione Produzione

### Comandi Base
```bash
# Stato servizi
./monitor.sh

# Deploy aggiornamenti
git pull && ./deploy.sh

# Backup dati
./backup.sh

# Restart servizi
sudo supervisorctl restart trading-bot:*
```

### Log e Debug
```bash
# Log in tempo reale
tail -f /var/log/trading-bot/frontend.out.log

# Errori
tail -f /var/log/trading-bot/frontend.err.log

# Status completo
sudo supervisorctl status
```

## 🌐 Accesso Web

- **Dashboard**: http://tuo-dominio.com
- **Controllo Bot**: http://tuo-dominio.com/control  
- **Test API**: http://tuo-dominio.com/api-test
- **Grafici**: http://tuo-dominio.com/static/charts/

## 🔒 Sicurezza

### SSL Automatico
```bash
sudo certbot --nginx -d tuo-dominio.com
```

### Firewall
```bash
sudo ufw enable
sudo ufw allow 80,443/tcp
```

## 🆘 Risoluzione Problemi

### Bot Non Si Avvia
1. Controlla chiavi API nel file `.env`
2. Verifica log: `tail -f /var/log/trading-bot/frontend.err.log`
3. Test connessione: `python3 test_api.py`

### Dashboard Non Raggiungibile
1. Controlla Nginx: `sudo systemctl status nginx`
2. Verifica porta 5000: `netstat -tlnp | grep 5000`
3. Restart servizi: `sudo supervisorctl restart trading-bot:*`

### Errori Database
1. Backup: `cp trading_data.db trading_data.db.backup`
2. Restart: `sudo supervisorctl restart trading-bot:*`

## 📞 Supporto

- 📧 Email: il_tuo_email@dominio.com
- 💬 Telegram: @il_tuo_username
- 🐛 Issues: https://github.com/TUO_USERNAME/Trading-bot/issues

---

⚡ **Deploy in 5 minuti**: `curl -fsSL https://raw.githubusercontent.com/TUO_USERNAME/Trading-bot/main/deploy.sh | bash`
