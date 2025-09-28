# 🚀 Trading Bot Dashboards - Docker Setup

Questa directory contiene tutto il necessario per deployare i dashboard del trading bot usando Docker.

## 📋 Struttura File

```
docker/
├── Dockerfile.dashboards          # Dockerfile per tutti i dashboard
├── docker-compose.dashboards.yml  # Orchestrazione Docker Compose
├── requirements-dashboards.txt    # Dipendenze Python per dashboard
├── nginx-dashboards.conf          # Configurazione Nginx reverse proxy
├── setup-dashboards.sh           # Script setup per Linux/Mac
├── setup-dashboards.ps1          # Script setup per Windows PowerShell
└── README-DOCKER.md              # Questa documentazione
```

## 🎯 Dashboard Inclusi

| Dashboard | Porta | Descrizione | URL Docker |
|-----------|-------|-------------|------------|
| **Multi-Symbol** | 5007 | Dashboard semplice multi-moneta (BTCUSDT, SUIUSDT, ETHUSDT, SOLUSDT) | http://localhost:5007 |
| **Professional** | 5006 | Dashboard avanzato con candele, volume profile, POC/VAH/VAL | http://localhost:5006 |
| **Simple** | 5004 | Dashboard semplice originale (solo BTCUSDT) | http://localhost:5004 |
| **Fixed** | 5003 | Dashboard di backup con correzioni | http://localhost:5003 |

## 🔧 Quick Start

### Windows (PowerShell)
```powershell
cd docker
.\setup-dashboards.ps1
```

### Linux/Mac (Bash)
```bash
cd docker
chmod +x setup-dashboards.sh
./setup-dashboards.sh
```

### Setup Manuale
```bash
cd docker
docker-compose -f docker-compose.dashboards.yml up -d --build
```

## 🌐 Accesso ai Servizi

### 🏠 Development (Localhost)
| Servizio | Porta | URL |
|----------|--------|-----|
| Nginx Proxy | 8080 | http://localhost:8080 |
| Professional | 5006 | http://localhost:5006 |
| Multi-Symbol | 5007 | http://localhost:5007 |
| Simple | 5004 | http://localhost:5004 |
| Redis | 16379 | localhost:16379 |
| Portainer | 9000 | http://localhost:9000 |

### 🏭 Production Server (Ubuntu)
Usa il file `docker-compose.prod.yml` per evitare conflitti di porte:

| Servizio | Porta | URL |
|----------|--------|-----|
| Nginx Proxy | 9080 | http://your-server-ip:9080 |
| Professional | 15006 | http://your-server-ip:15006 |
| Multi-Symbol | 15007 | http://your-server-ip:15007 |
| Simple | 15004 | http://your-server-ip:15004 |
| Redis | 19379 | your-server-ip:19379 |
| Portainer | 19000 | http://your-server-ip:19000 |

### Deployment Produzione Ubuntu
```bash
cd docker
chmod +x setup-dashboards-prod.sh
./setup-dashboards-prod.sh
```

### Tramite Nginx Reverse Proxy (Raccomandato)
- **Dashboard Multi-Symbol**: http://localhost/ 
- **Dashboard Professionale**: http://localhost/professional
- **Dashboard Semplice**: http://localhost/simple  
- **Dashboard Fixed**: http://localhost/fixed

### Accesso Diretto
- **Multi-Symbol**: http://localhost:5007
- **Professional**: http://localhost:5006
- **Simple**: http://localhost:5004
- **Fixed**: http://localhost:5003

### Monitoring e Tools
- **Portainer**: http://localhost:9000 (admin/admin123)
- **Redis**: localhost:6379 (password: dashboards2024)

## 📊 Caratteristiche

### 🔴 Multi-Symbol Dashboard (Default - Porta 5007)
- ✅ 4 Simboli: BTCUSDT, SUIUSDT, ETHUSDT, SOLUSDT
- ✅ Soglie Large Orders personalizzate per simbolo
- ✅ Selector drop-down per cambio simbolo istantaneo
- ✅ Bolle dimensionate proporzionalmente
- ✅ Design pulito e veloce

### 🚀 Professional Dashboard (Porta 5006)  
- ✅ Candele multi-timeframe (1m, 5m, 15m, 1h)
- ✅ Volume Profile con POC, VAH, VAL
- ✅ Storico dati separati per simbolo
- ✅ API avanzate per dati storici
- ✅ Design professionale con sidebar

### 🔄 Simple Dashboard (Porta 5004)
- ✅ Dashboard originale con bolle
- ✅ Solo BTCUSDT 
- ✅ Grafico lineare real-time
- ✅ Stream ordini large

### 🛠️ Fixed Dashboard (Porta 5003)
- ✅ Versione di backup
- ✅ Correzioni per stabilità
- ✅ Fallback in caso di problemi

## 🐋 Soglie Large Orders

| Simbolo | Soglia | Valore Approssimativo |
|---------|--------|-----------------------|
| BTCUSDT | 2.0 BTC | ~$220,000 |
| SUIUSDT | 10,000 SUI | ~$50,000 |
| ETHUSDT | 50.0 ETH | ~$200,000 |
| SOLUSDT | 500.0 SOL | ~$100,000 |

## 🔧 Comandi Docker Utili

### Gestione Container
```bash
# Avvia tutti i servizi
docker-compose -f docker-compose.dashboards.yml up -d

# Ferma tutti i servizi  
docker-compose -f docker-compose.dashboards.yml down

# Riavvia un servizio specifico
docker-compose -f docker-compose.dashboards.yml restart dashboard-multi-simple

# Visualizza logs
docker-compose -f docker-compose.dashboards.yml logs -f

# Visualizza logs di un servizio specifico
docker-compose -f docker-compose.dashboards.yml logs -f dashboard-professional

# Rebuild e riavvio
docker-compose -f docker-compose.dashboards.yml up -d --build
```

### Monitoring
```bash
# Status dei container
docker ps

# Stats utilizzo risorse
docker stats

# Health check di tutti i servizi
docker-compose -f docker-compose.dashboards.yml ps

# Esegui comando in container
docker exec -it dashboard-multi-simple /bin/bash
```

### Debugging
```bash
# Controlla logs errori
docker-compose -f docker-compose.dashboards.yml logs dashboard-professional | grep ERROR

# Testa connettività
curl http://localhost:5007/debug
curl http://localhost:5006/api/symbols

# Restart servizio singolo
docker restart dashboard-multi-simple
```

## 🔐 Configurazione Ambiente

Il file `.env` viene creato automaticamente con queste variabili:

```env
FLASK_ENV=production
PYTHONPATH=/app  
PYTHONUNBUFFERED=1
REDIS_PASSWORD=dashboards2024
```

## 📁 Volume Mount

I seguenti volumi sono montati per persistenza dati:

```yaml
volumes:
  - ../data:/app/data          # Dati applicazione
  - ../logs:/app/logs          # Log files  
  - redis_data:/data           # Dati Redis
  - portainer_data:/data       # Dati Portainer
```

## 🌐 Nginx Configuration

Il reverse proxy Nginx fornisce:

- ✅ Load balancing 
- ✅ WebSocket support per Socket.IO
- ✅ Compressione Gzip
- ✅ Rate limiting
- ✅ Security headers
- ✅ Static file caching
- ✅ Health checks

## 📈 Performance Tips

### Ottimizzazione Resource
```yaml
# Nel docker-compose.yml, aggiungi:
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Scale Services
```bash
# Scala un servizio a più istanze
docker-compose -f docker-compose.dashboards.yml up -d --scale dashboard-multi-simple=3
```

## 🚨 Troubleshooting

### Problemi Comuni

1. **Porte già in uso**
   ```bash
   # Trova processi su porta
   netstat -tulpn | grep :5007
   # Termina processo
   sudo kill -9 <PID>
   ```

2. **Container non si avvia**
   ```bash
   # Controlla logs
   docker-compose -f docker-compose.dashboards.yml logs dashboard-name
   # Rebuild da zero
   docker-compose -f docker-compose.dashboards.yml build --no-cache
   ```

3. **WebSocket non funziona**
   - Controlla che Nginx proxy_pass sia configurato per WebSocket
   - Verifica headers `Upgrade` e `Connection`
   - Testa connessione diretta alla porta del servizio

4. **Dashboard non carica**
   ```bash
   # Testa health endpoint
   curl http://localhost:5007/debug
   # Controlla status container  
   docker ps | grep dashboard
   ```

## 🔄 Updates e Deployment

### Update Dashboard Code
```bash
# Pull codice aggiornato
git pull origin main

# Rebuild e restart
docker-compose -f docker-compose.dashboards.yml up -d --build

# Zero-downtime update (con load balancer)
docker-compose -f docker-compose.dashboards.yml up -d --no-deps dashboard-multi-simple
```

### Backup e Restore
```bash
# Backup volumi
docker run --rm -v trading-bot_redis_dashboards_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz /data

# Restore volumi  
docker run --rm -v trading-bot_redis_dashboards_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis_backup.tar.gz
```

## 📞 Support

Per problemi o domande:
1. Controlla i logs: `docker-compose logs -f`
2. Verifica health: `curl http://localhost/health`  
3. Testa servizi diretti: `curl http://localhost:5007/debug`

## 🎉 Ready to Trade!

Una volta completato il setup, avrai:

- 🔴 **4 Dashboard** funzionanti in Docker
- 🌐 **Nginx Proxy** per accesso unificato  
- 📊 **Redis** per caching e sessioni
- 🛠️ **Portainer** per management Docker
- 🔒 **Health Checks** automatici
- 📈 **Monitoring** completo

**Enjoy your containerized trading dashboards!** 🚀📈🐋