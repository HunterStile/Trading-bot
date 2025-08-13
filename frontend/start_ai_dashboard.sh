#!/bin/bash
# Avvio ambiente virtuale e dashboard Trading Bot

cd "$(dirname "$0")"

# Attiva virtualenv
source bot_env/bin/activate

# Installa requirements se non già installati
pip install -r requirements.txt
pip install -r ai_modules/ai_requirements.txt

# Avvia la dashboard
python3 start_dashboard.py
