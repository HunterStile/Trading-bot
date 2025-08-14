@echo off
echo 🚀 Trading Bot Setup Script
echo =========================

echo.
echo 📦 Installing Python dependencies...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found!

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip not found! Please install pip first.
    pause
    exit /b 1
)

echo ✅ pip found!

REM Upgrade pip
echo 🔄 Upgrading pip...
python -m pip install --upgrade pip

REM Install core requirements
echo.
echo 📋 Installing core requirements...
pip install -r requirements-minimal.txt

if errorlevel 1 (
    echo ❌ Failed to install core requirements!
    pause
    exit /b 1
)

echo ✅ Core requirements installed!

REM Ask for AI installation
echo.
set /p install_ai="🤖 Do you want to install AI trading features? (y/n): "

if /i "%install_ai%"=="y" (
    echo.
    echo 🧠 Installing AI requirements...
    pip install -r requirements-ai.txt
    
    if errorlevel 1 (
        echo ⚠️ Some AI dependencies failed to install
        echo You can install them manually later with: pip install -r requirements-ai.txt
    ) else (
        echo ✅ AI requirements installed!
    )
)

REM Create .env file if it doesn't exist
echo.
if not exist ".env" (
    echo 📝 Creating .env configuration file...
    copy "frontend\.env.example" ".env"
    echo ✅ .env file created! Please edit it with your API keys.
) else (
    echo ✅ .env file already exists
)

echo.
echo 🎉 Installation completed!
echo.
echo 📋 Next steps:
echo 1. Edit .env file with your API keys
echo 2. Run: python frontend/app.py
echo 3. Open: http://localhost:5000
echo.
echo 🤖 For AI features:
echo 1. Add OPENAI_API_KEY to .env
echo 2. Go to: http://localhost:5000/ai-trading
echo.
pause
