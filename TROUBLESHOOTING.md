# 🔧 Trading Bot Troubleshooting Guide

## Problemi Comuni e Soluzioni

### 1. Socket.IO Errors

**Errore**: "The client is using an unsupported version of the Socket.IO"

**Soluzione**:
```bash
pip install --upgrade Flask-SocketIO==5.3.6 python-socketio==5.9.0
```

### 2. Moduli AI Mancanti

**Errore**: "No module named 'yfinance'" o altri moduli AI

**Soluzione**:
```bash
pip install -r requirements-minimal.txt
pip install yfinance openai requests python-dotenv
```

### 3. Errori API Keys

**Errore**: "API key not configured" o "Invalid API response"

**Soluzione**:
1. Crea file `.env` nella root del progetto
2. Aggiungi le tue API keys:
```
OPENAI_API_KEY=sk-your-key-here
BYBIT_API_KEY=your-bybit-key
BYBIT_API_SECRET=your-bybit-secret
```

### 4. Errori di Importazione

**Errore**: "ModuleNotFoundError" vari

**Soluzione**:
```bash
# Reinstalla tutte le dipendenze
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### 5. Port già in uso

**Errore**: "Address already in use" porta 5000

**Soluzione**:
```powershell
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

### 6. Errori di Connessione Bybit

**Errore**: "Connection failed" o "API error"

**Soluzione**:
1. Verifica le credenziali API
2. Controlla i permessi API (trading, wallet)
3. Verifica connessione internet
4. Testa con endpoint di test

### 7. AI Analysis Errors

**Errore**: "AI analysis failed" o timeout

**Soluzione**:
1. Verifica OPENAI_API_KEY
2. Controlla crediti OpenAI
3. Verifica connessione internet
4. Riduci frequenza analisi

### 8. Database Errors

**Errore**: SQLite errors vari

**Soluzione**:
```bash
# Elimina e ricrea database
rm -f trading_bot.db
python frontend/setup_database.py
```

### 9. Template/Static Files Errors

**Errore**: "Template not found" o CSS non caricato

**Soluzione**:
1. Verifica struttura cartelle
2. Controlla paths in app.py
3. Riavvia il server

### 10. Performance Issues

**Problema**: App lenta o timeout

**Soluzione**:
1. Riduci frequenza aggiornamenti
2. Limita simboli monitorati
3. Ottimizza query database
4. Aumenta timeout requests

## 🚀 Setup Completo da Zero

### Windows:
```cmd
# 1. Clona repository
git clone <repo-url>
cd Trading-bot

# 2. Installa dipendenze
setup.bat

# 3. Configura .env
copy frontend\.env.example .env
# Modifica .env con le tue API keys

# 4. Avvia dashboard
cd frontend
python start_dashboard.py
```

### Linux/Mac:
```bash
# 1. Clona repository
git clone <repo-url>
cd Trading-bot

# 2. Installa dipendenze
chmod +x setup.sh
./setup.sh

# 3. Configura .env
cp frontend/.env.example .env
# Modifica .env con le tue API keys

# 4. Avvia dashboard
cd frontend
python3 start_dashboard.py
```

## 🧪 Test e Debug

### Test Connessione API:
```python
# Test script rapido
python -c "
from config import api, api_sec
from pybit.unified_trading import HTTP
session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
print('API Test:', session.get_server_time())
"
```

### Test AI Modules:
```bash
cd frontend
python test_ai_integration.py
```

### Test Dashboard:
1. Vai su: http://localhost:5000/api-test
2. Testa connessioni API
3. Verifica responses

## 📞 Support

1. **Log Files**: Controlla logs in console
2. **Error Messages**: Copia messaggio completo
3. **Configuration**: Verifica .env e requirements
4. **Network**: Testa connessione internet
5. **API Status**: Controlla status Bybit/OpenAI

## 🔄 Reset Completo

Se tutto fallisce:
```bash
# 1. Backup configurazione
cp .env .env.backup

# 2. Reset ambiente Python
pip freeze > installed_packages.txt
pip uninstall -r installed_packages.txt -y

# 3. Reinstalla tutto
pip install -r requirements.txt

# 4. Reset database
rm -f *.db

# 5. Riavvia tutto
python frontend/start_dashboard.py
```
