@echo off
title Trading Bot Dashboard v2.0 - Con Storico
echo.
echo ===============================================
echo     🤖 TRADING BOT DASHBOARD v2.0
echo     Con Sistema di Storico Completo!
echo ===============================================
echo.

cd /d "%~dp0"

echo 🔍 Controllo Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trovato!
    echo 📥 Scarica Python da: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python trovato
echo.

echo 📦 Installazione dipendenze...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Errore nell'installazione delle dipendenze
    echo 🔧 Prova a eseguire manualmente: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Dipendenze installate
echo.

echo 🚀 Avvio Trading Bot Dashboard...
echo.
echo 📊 Dashboard sarà disponibile su: http://localhost:5000
echo 💡 Usa Ctrl+C per fermare il server
echo.

python start_dashboard.py

echo.
echo 👋 Dashboard chiuso
pause
