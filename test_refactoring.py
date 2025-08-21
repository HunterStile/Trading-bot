#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script per TradingEngine
=============================

Script per testare il funzionamento del nuovo TradingEngine
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trading import TradingEngine, TradingService
from core.notifications import WebSocketManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_trading_engine():
    """Test del TradingEngine standalone"""
    print("🧪 Test TradingEngine...")
    
    # Crea engine senza dipendenze esterne
    engine = TradingEngine(logger=logger)
    
    # Test configurazione
    config = {
        'symbol': 'BTCUSDT',
        'quantity': 100,
        'operation': True,
        'ema_period': 20,
        'interval': 30,
        'open_candles': 3,
        'stop_candles': 3,
        'distance': 1
    }
    
    engine.configure(config)
    print(f"✅ Engine configurato: {engine.config}")
    
    # Test stato
    status = engine.get_status()
    print(f"✅ Stato engine: {status}")
    
    print("🎉 Test TradingEngine completato!")

def test_trading_service():
    """Test del TradingService standalone"""
    print("🧪 Test TradingService...")
    
    # Crea service senza dipendenze esterne
    service = TradingService(logger=logger)
    
    # Test configurazione
    config = {
        'symbol': 'ETHUSDT',
        'quantity': 25,
        'operation': False,  # Short
        'ema_period': 10,
        'interval': 15,
        'open_candles': 2,
        'stop_candles': 2,
        'distance': 0.5
    }
    
    # Test stato
    status = service.get_status()
    print(f"✅ Stato service: {status}")
    
    # Test aggiornamento impostazioni
    result = service.update_settings({'symbol': 'ADAUSDT'})
    print(f"✅ Aggiornamento impostazioni: {result}")
    
    print("🎉 Test TradingService completato!")

def test_websocket_manager():
    """Test del WebSocketManager (mock)"""
    print("🧪 Test WebSocketManager...")
    
    # Mock SocketIO più completo
    class MockSocketIO:
        def __init__(self):
            self.handlers = {}
            
        def emit(self, event, data, room=None):
            print(f"📡 Mock emit: {event} -> {str(data)[:100]}...")
        
        def on(self, event):
            def decorator(func):
                self.handlers[event] = func
                print(f"📝 Registered handler for: {event}")
                return func
            return decorator
    
    mock_socketio = MockSocketIO()
    
    # Crea WebSocket Manager
    ws_manager = WebSocketManager(mock_socketio, logger)
    
    # Test varie emissioni
    ws_manager.emit_analysis_log("Test message", "info")
    ws_manager.emit_price_update("BTCUSDT", 45000.50)
    ws_manager.emit_error("Test error")
    
    print(f"✅ Handlers registrati: {list(mock_socketio.handlers.keys())}")
    print("🎉 Test WebSocketManager completato!")

def test_integration():
    """Test di integrazione base"""
    print("🧪 Test Integrazione...")
    
    # Mock dependencies migliorato
    class MockSocketIO:
        def __init__(self):
            self.handlers = {}
            
        def emit(self, event, data, room=None):
            print(f"📡 Integration emit: {event}")
        
        def on(self, event):
            def decorator(func):
                self.handlers[event] = func
                return func
            return decorator
    
    mock_socketio = MockSocketIO()
    
    # Crea WebSocket Manager
    ws_manager = WebSocketManager(mock_socketio, logger)
    
    # Crea Trading Service
    service = TradingService(
        websocket_manager=ws_manager,
        logger=logger
    )
    
    # Test configurazione e stato
    config = {
        'symbol': 'SOLUSDT',
        'quantity': 50,
        'operation': True,
        'ema_period': 14
    }
    
    result = service.update_settings(config)
    print(f"✅ Configurazione integrata: {result}")
    
    status = service.get_status()
    print(f"✅ Stato integrato: {status['bot_status']['symbol']}")
    
    print("🎉 Test Integrazione completato!")

if __name__ == '__main__':
    print("🚀 Avvio test moduli rimodularizzati...")
    print("=" * 50)
    
    try:
        test_trading_engine()
        print()
        
        test_trading_service()
        print()
        
        test_websocket_manager()
        print()
        
        test_integration()
        print()
        
        print("=" * 50)
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ La rimodularizzazione è funzionante")
        
    except Exception as e:
        print(f"❌ ERRORE NEI TEST: {e}")
        import traceback
        traceback.print_exc()
