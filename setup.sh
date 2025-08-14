#!/bin/bash

echo "🚀 Trading Bot Setup Script"
echo "========================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found! Please install Python 3.8+ first."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "MacOS: brew install python3"
    exit 1
fi

echo "✅ Python3 found!"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found! Please install pip first."
    exit 1
fi

echo "✅ pip3 found!"

# Upgrade pip
echo "🔄 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install core requirements
echo
echo "📋 Installing core requirements..."
pip3 install -r requirements-minimal.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install core requirements!"
    exit 1
fi

echo "✅ Core requirements installed!"

# Ask for AI installation
echo
read -p "🤖 Do you want to install AI trading features? (y/n): " install_ai

if [[ $install_ai == "y" || $install_ai == "Y" ]]; then
    echo
    echo "🧠 Installing AI requirements..."
    pip3 install -r requirements-ai.txt
    
    if [ $? -ne 0 ]; then
        echo "⚠️ Some AI dependencies failed to install"
        echo "You can install them manually later with: pip3 install -r requirements-ai.txt"
    else
        echo "✅ AI requirements installed!"
    fi
fi

# Create .env file if it doesn't exist
echo
if [ ! -f ".env" ]; then
    echo "📝 Creating .env configuration file..."
    cp "frontend/.env.example" ".env"
    echo "✅ .env file created! Please edit it with your API keys."
else
    echo "✅ .env file already exists"
fi

echo
echo "🎉 Installation completed!"
echo
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: python3 frontend/app.py"
echo "3. Open: http://localhost:5000"
echo
echo "🤖 For AI features:"
echo "1. Add OPENAI_API_KEY to .env"
echo "2. Go to: http://localhost:5000/ai-trading"
echo
