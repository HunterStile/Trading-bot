# Routes package

from flask import Flask
from flask_cors import CORS

def register_blueprints(app: Flask):
    """Registra tutti i blueprint dell'applicazione"""
    
    print("🚀 STARTING register_blueprints function...")
    
    # Abilita CORS per il frontend Next.js con configurazione completa
    CORS(app, 
         origins=["http://localhost:3000", "http://localhost:3001"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    print("✅ CORS configured")
    
    # Importa e registra i blueprint esistenti
    print("🔄 Importing existing blueprints...")
    from .health import health_bp
    from .api_saas import api_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp)
    print("✅ Existing blueprints registered")
    
    # Prova ad importare i nuovi blueprint
    try:
        print("🔄 Importing NEW auth blueprint...")
        from .auth import auth_bp
        app.register_blueprint(auth_bp)
        print("✅ Auth blueprint registered")
        
        print("🔄 Importing NEW user_config blueprint...")
        from .user_config import user_config_bp
        app.register_blueprint(user_config_bp)
        print("✅ User config blueprint registered")
        
        print("✅ Authentication system attivo")
        print("✅ Multi-tenant user management attivo")
        
    except ImportError as e:
        print(f"❌ Errore import new blueprints: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Errore registrazione new blueprints: {e}")
        import traceback
        traceback.print_exc()
    
    # Debug: elenca tutte le route registrate
    print("🔍 Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")

def init_ai_systems():
    """Inizializza i sistemi AI (placeholder)"""
    print("🤖 AI Systems initialized")
    return True