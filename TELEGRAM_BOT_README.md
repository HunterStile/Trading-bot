# 🤖 Telegram Bot Integration

Questo sistema include un bot Telegram completo per monitorare e controllare remotamente il trading bot.

## 📋 Funzionalità

### 🔔 Notifiche Automatiche
- **Apertura posizioni**: Notifica quando viene aperta una posizione LONG/SHORT
- **Chiusura posizioni**: Notifica con profitti/perdite quando viene chiusa una posizione
- **Crash del sistema**: Alert immediato quando il bot si arresta inaspettatamente
- **Recovery completato**: Conferma quando il sistema si riprende da un crash
- **Start/Stop bot**: Notifiche quando il bot viene avviato o fermato

### 🎛️ Controllo Interattivo
- **/start** - Avvia il bot e mostra menu principale
- **/status** - Stato corrente del bot (SEEKING_ENTRY, MANAGING_POSITIONS, STOPPED)
- **/positions** - Lista delle posizioni attive con dettagli
- **/history** - Storico recente delle operazioni
- **/stats** - Statistiche di performance del bot
- **/startbot** - Avvia il trading bot da remoto
- **/stopbot** - Ferma il trading bot da remoto

## ⚙️ Configurazione

### 1. Crea un Bot Telegram

1. Apri Telegram e cerca **@BotFather**
2. Invia `/newbot` e segui le istruzioni
3. Scegli un nome per il bot (es. "My Trading Bot")
4. Scegli un username (es. "mytradingbot_bot")
5. Copia il **token** che ti viene fornito

### 2. Ottieni il Chat ID

1. Avvia una conversazione con il tuo bot
2. Invia un messaggio qualsiasi
3. Apri nel browser: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Cerca "chat":{"id": **NUMERO** e copia il numero

### 3. Configura il file .env

Aggiungi al tuo file `.env` (nella root del progetto):

```bash
# Telegram Bot Configuration
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## 🚀 Avvio

### Avvio Automatico (Raccomandato)
Il bot Telegram si avvia automaticamente quando lanci la dashboard:

```bash
cd frontend
python app.py
```

### Avvio Separato
Puoi avviare solo il bot Telegram senza la dashboard:

```bash
cd frontend
python start_telegram_bot.py
```

## 📱 Utilizzo

1. **Avvia il bot** e invia `/start`
2. **Usa i comandi** o i bottoni del menu
3. **Ricevi notifiche** automatiche per tutte le operazioni
4. **Controlla remotamente** il bot anche quando non sei al computer

## 🔧 Personalizzazione

### Modificare le Notifiche
Modifica `utils/telegram_notifier.py` per personalizzare i messaggi.

### Aggiungere Comandi
Modifica `utils/telegram_bot.py` per aggiungere nuovi comandi.

### Cambiare la Frequenza
Modifica gli interval nei timer per cambiare frequenza aggiornamenti.

## 🛠️ Troubleshooting

### "Bot token mancante"
- Verifica che `TELEGRAM_TOKEN` sia nel file .env
- Controlla che il token sia corretto

### "Chat ID non valido"
- Verifica che `TELEGRAM_CHAT_ID` sia nel file .env
- Assicurati di aver inviato almeno un messaggio al bot

### "Bot non risponde"
- Riavvia il bot con `/start`
- Controlla che la dashboard sia in esecuzione su localhost:5000

### "Notifiche non arrivano"
- Verifica la connessione internet
- Controlla i log per errori Telegram
- Riavvia il sistema

## 📊 Log e Debug

I log del bot Telegram sono disponibili nella console della dashboard. Per debug avanzato, controlla:

- `frontend/data/recovery_log.json` - Log di recovery del sistema
- Console output della dashboard - Messaggi di debug in tempo reale

## 🔒 Sicurezza

- **Non condividere mai il token** del bot
- **Mantieni privato il chat ID**
- Il bot funziona solo con il chat ID configurato
- Tutte le comunicazioni sono crittografate da Telegram
