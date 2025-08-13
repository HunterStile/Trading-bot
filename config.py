import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# API Bybit
api = os.getenv('BYBIT_API_KEY', '')
api_sec = os.getenv('BYBIT_API_SECRET', '')

# Configurazione Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Configurazione Spotify
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')

# Scelta browser
path = os.getenv('CHROME_DRIVER_PATH', '')
chrome_scelto = os.getenv('CHROME_BINARY_PATH', '')

