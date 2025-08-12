# 🤖 Trading Bot Dashboard

Un'interfaccia web moderna per monitorare e controllare il tuo trading bot Bybit.

## 🌟 Caratteristiche

- **Dashboard Real-time**: Monitoring del saldo, prezzi e performance
- **Controllo Bot**: Start/Stop e configurazione parametri
- **Test API**: Verifica connessione e funzionalità Bybit
- **Gestione Rischio**: Impostazioni avanzate per la sicurezza
- **Notifiche Telegram**: Alert automatici per eventi importanti
- **Grafici Interattivi**: Visualizzazione dati di mercato con Chart.js
- **WebSocket**: Aggiornamenti in tempo reale

## 📋 Requisiti

- Python 3.7+
- Account Bybit con API abilitata
- Bot Telegram (opzionale per notifiche)

## 🚀 Avvio Rapido

### Metodo 1: Batch File (Windows)
```bash
# Doppio click su start_dashboard.bat
./start_dashboard.bat
```

### Metodo 2: Python
```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia dashboard
python start_dashboard.py
```

### Metodo 3: Diretto
```bash
# Installa dipendenze
pip install flask flask-socketio pybit python-dotenv

# Avvia app
python app.py
```

## ⚙️ Configurazione

1. **Crea/Modifica file `.env`** nella cartella principale del trading bot:
   ```env
   # API Bybit
   BYBIT_API_KEY=your_api_key_here
   BYBIT_API_SECRET=your_api_secret_here
   
   # Telegram (opzionale)
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   CHAT_ID=your_telegram_chat_id_here
   ```

2. **Ottieni credenziali Bybit**:
   - Vai su [Bybit API Management](https://www.bybit.com/app/user/api-management)
   - Crea nuova API Key con permessi Trading
   - **IMPORTANTE**: Usa Testnet per i test iniziali

3. **Configura Telegram** (opzionale):
   - Crea un bot con [@BotFather](https://t.me/botfather)
   - Ottieni il token del bot
   - Ottieni il Chat ID del tuo account/gruppo

## 📊 Utilizzo

### Dashboard Principale
- **Saldo Wallet**: Visualizza equity totale e balance
- **Prezzo Corrente**: Monitoraggio in tempo reale del simbolo selezionato
- **Grafico Prezzi**: Chart interattivo con dati storici
- **Analisi EMA**: Indicatori tecnici automatici

### Controllo Bot
- **Start/Stop Bot**: Controllo completo del trading bot
- **Configurazione**: Modifica parametri (simbolo, quantità, EMA, intervalli)
- **Log Real-time**: Monitoring attività e errori
- **Posizioni Attive**: Visualizza posizioni aperte

### Test API
- **Test Connessione**: Verifica stato API Bybit
- **Test Funzioni**: Saldo, prezzi, dati mercato
- **Performance**: Latenza e statistiche successo
- **Simulazione Ordini**: Test sicuri senza trading reale

### Impostazioni
- **Configurazione Bot**: Parametri di default e strategia
- **Gestione Rischio**: Stop loss, take profit, limiti
- **Notifiche**: Configurazione alert Telegram
- **Preset**: Configurazioni predefinite (conservativo, bilanciato, aggressivo)

## 🔧 Struttura File

```
frontend/
├── app.py                 # Applicazione Flask principale
├── start_dashboard.py     # Launcher con controlli automatici
├── start_dashboard.bat    # Batch file Windows
├── requirements.txt       # Dipendenze Python
├── static/
│   ├── css/
│   │   └── style.css     # Stili personalizzati
│   └── js/              # JavaScript (se necessario)
├── templates/
│   ├── base.html         # Template base
│   ├── dashboard.html    # Dashboard principale
│   ├── bot_control.html  # Controllo bot
│   ├── api_test.html     # Test API
│   └── settings.html     # Impostazioni
└── README.md            # Questo file
```

## 🛡️ Sicurezza

- **Mai condividere le API Key** in pubblico
- **Usa Testnet** per i test iniziali
- **Imposta limiti di rischio** appropriati
- **Monitora sempre** le attività del bot
- **Backup regolari** della configurazione

## 🔗 Endpoints API

| Endpoint | Metodo | Descrizione |
|----------|---------|-------------|
| `/api/balance` | GET | Saldo wallet |
| `/api/price/<symbol>` | GET | Prezzo simbolo |
| `/api/market-data/<symbol>` | GET | Dati mercato e analisi |
| `/api/test-connection` | GET | Test connessione API |
| `/api/bot/start` | POST | Avvia bot |
| `/api/bot/stop` | POST | Ferma bot |
| `/api/bot/status` | GET | Stato bot |
| `/api/bot/settings` | POST | Aggiorna impostazioni |

## 🌐 WebSocket Events

| Event | Descrizione |
|-------|-------------|
| `connect` | Connessione stabilita |
| `bot_update` | Aggiornamento stato bot |
| `bot_error` | Errore bot |
| `price_update` | Aggiornamento prezzo |

## 🐛 Troubleshooting

### Errori Comuni

1. **Import Error Flask**:
   ```bash
   pip install flask flask-socketio
   ```

2. **API Key Invalid**:
   - Verifica credenziali in `.env`
   - Controlla permessi API su Bybit
   - Usa Testnet per i test

3. **Porta 5000 occupata**:
   - Modifica porta in `app.py`: `port=5001`
   - Oppure chiudi altre applicazioni

4. **Errori WebSocket**:
   - Aggiorna browser
   - Controlla firewall/antivirus
   - Prova modalità incognito

### Debug Mode

Per attivare debug dettagliato, modifica in `app.py`:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

## 📱 Accesso Mobile

Il dashboard è responsive e funziona su mobile:
- Apri browser mobile
- Vai su `http://[IP_COMPUTER]:5000`
- Esempio: `http://192.168.1.100:5000`

## 🔄 Aggiornamenti

Per aggiornare il dashboard:
1. Backup della configurazione
2. Scarica nuova versione
3. Reinstalla dipendenze: `pip install -r requirements.txt`
4. Ripristina configurazione

## 📞 Supporto

- **Issues**: Apri issue su GitHub
- **Documentazione**: Leggi commenti nel codice
- **Bybit API**: [Documentazione ufficiale](https://bybit-exchange.github.io/docs/v5/intro)

## ⚖️ Disclaimer

**ATTENZIONE**: Questo software è solo per scopi educativi. Il trading comporta rischi finanziari. L'autore non è responsabile per eventuali perdite. Usa sempre fondi che puoi permetterti di perdere e testa sempre in modalità Testnet prima di usare fondi reali.

---

🚀 **Buon Trading!** 📈
