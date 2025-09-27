
from flask import Blueprint
from .main import main_bp
from .api import api_bp
from .bot_control import bot_control_bp
from .trading import trading_bp
from .history import history_bp
from .symbols import symbols_bp
from .backtest import backtest_bp
from .alerts import alerts_bp, init_alerts_system
from .market_analysis_routes import market_analysis_bp, init_market_analysis_routes
from .ai_trading import ai_trading_bp, init_ai_trading_system

# Import SaaS blueprints from parent directory
import sys
import os

# Add parent directory to path (go up from frontend/routes to Trading-bot)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)
print(f"📂 Added to path: {parent_dir}")

# Check if auth.py exists
auth_path = os.path.join(parent_dir, 'routes', 'auth.py')
config_path = os.path.join(parent_dir, 'routes', 'user_config.py')
print(f"🔍 Auth file exists: {os.path.exists(auth_path)}")
print(f"🔍 Config file exists: {os.path.exists(config_path)}")

try:
    # Import directly from file path to avoid conflicts
    import importlib.util
    
    # Load auth blueprint
    spec_auth = importlib.util.spec_from_file_location("auth_module", auth_path)
    auth_module = importlib.util.module_from_spec(spec_auth)
    spec_auth.loader.exec_module(auth_module)
    auth_bp = auth_module.auth_bp
    
    # Load user_config blueprint  
    spec_config = importlib.util.spec_from_file_location("user_config_module", config_path)
    config_module = importlib.util.module_from_spec(spec_config)
    spec_config.loader.exec_module(config_module)
    user_config_bp = config_module.user_config_bp
    
    print("✅ SaaS blueprints imported successfully")
except Exception as e:
    print(f"❌ Error importing SaaS blueprints: {e}")
    import traceback
    traceback.print_exc()
    auth_bp = None
    user_config_bp = None

def register_blueprints(app):
    """Registra tutti i blueprints nell'app Flask"""
    print("🚀 Starting blueprint registration...")
    
    # Existing blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(bot_control_bp, url_prefix='/api/bot')
    app.register_blueprint(trading_bp, url_prefix='/api/trading')
    app.register_blueprint(history_bp, url_prefix='/api/history')
    app.register_blueprint(symbols_bp, url_prefix='/api/symbols')
    app.register_blueprint(backtest_bp, url_prefix='/backtest')
    app.register_blueprint(alerts_bp, url_prefix='/alerts')
    app.register_blueprint(market_analysis_bp, url_prefix='/market-analysis')
    app.register_blueprint(ai_trading_bp, url_prefix='/ai-trading')
    
    print("✅ Standard blueprints registered")
    
    # SaaS blueprints
    if auth_bp:
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        print("✅ Auth blueprint registered at /api/auth")
    
    if user_config_bp:
        app.register_blueprint(user_config_bp, url_prefix='/api/user')
        print("✅ User config blueprint registered at /api/user")
    
    # Inizializza il sistema di alert
    init_alerts_system(app)
    
    # Inizializza il sistema di analisi mercato
    telegram_notifier = app.config.get('TELEGRAM_NOTIFIER')
    init_market_analysis_routes(app, telegram_notifier)

def init_ai_systems(app):
    """Inizializza i sistemi AI dopo la configurazione dell'app"""
    init_ai_trading_system(app)