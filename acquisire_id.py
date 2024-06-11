from config import *
import requests

# URL per ottenere gli aggiornamenti
url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'

# Richiesta HTTP per ottenere gli aggiornamenti
response = requests.get(url)
data = response.json()

# Stampa i dati degli aggiornamenti per vedere il chat ID
print(data)

# Estrai il chat ID dall'ultimo messaggio
if 'result' in data and len(data['result']) > 0:
    chat_id = data['result'][-1]['message']['chat']['id']
    print(f"Il tuo chat ID è: {chat_id}")
else:
    print("Non sono stati trovati messaggi. Invia un messaggio al tuo bot e riprova.")