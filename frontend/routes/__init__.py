
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

def register_blueprints(app):
    """Registra tutti i blueprints nell'app Flask"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(bot_control_bp, url_prefix='/api/bot')
    app.register_blueprint(trading_bp, url_prefix='/api/trading')
    app.register_blueprint(history_bp, url_prefix='/api/history')
    app.register_blueprint(symbols_bp, url_prefix='/api/symbols')
    app.register_blueprint(backtest_bp, url_prefix='/backtest')
    app.register_blueprint(alerts_bp, url_prefix='/alerts')
    app.register_blueprint(market_analysis_bp, url_prefix='/market-analysis')
    
    # Inizializza il sistema di alert
    init_alerts_system(app)
    
    # Inizializza il sistema di analisi mercato
    telegram_notifier = app.config.get('TELEGRAM_NOTIFIER')
    init_market_analysis_routes(app, telegram_notifier)