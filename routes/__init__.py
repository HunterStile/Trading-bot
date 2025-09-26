# Routes package

from flask import Flask
from flask_cors import CORS

def register_blueprints(app: Flask):
    """Registra tutti i blueprint dell'applicazione"""
    
    # Abilita CORS per il frontend Next.js con configurazione completa
    CORS(app, 
         origins=["http://localhost:3000", "http://localhost:3001"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    # Importa e registra i blueprint
    from .health import health_bp
    from .api_saas import api_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp)
    
    print("✅ API Routes registrate per SaaS integration")

def init_ai_systems():
    """Inizializza i sistemi AI (placeholder)"""
    print("🤖 AI Systems initialized")
    return True