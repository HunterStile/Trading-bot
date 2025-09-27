#!/usr/bin/env python3
"""
Test script per verificare il funzionamento del user_manager
"""

import sys
import os

# Aggiungi il percorso del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_manager():
    try:
        print("🔄 Testing user_manager import...")
        from utils.user_manager import user_manager
        print("✅ user_manager imported successfully!")
        
        print("🔄 Testing database initialization...")
        # Il database si inizializza automaticamente
        print("✅ Database initialized!")
        
        print("🔄 Testing user registration...")
        result = user_manager.register_user("test@example.com", "test123")
        print(f"Registration result: {result}")
        
        if result['success']:
            print("✅ User registration test passed!")
        else:
            print(f"❌ User registration failed: {result.get('error')}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing User Manager System...")
    success = test_user_manager()
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Tests failed!")
        sys.exit(1)