#!/usr/bin/env python3
"""
Test per verificare l'intero workflow di apertura/recovery/chiusura
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.trading_wrapper import TradingWrapper
from utils.database import trading_db
from datetime import datetime
import time

def test_complete_workflow():
    """Test completo del workflow apertura -> recovery -> chiusura"""
    
    print("🧪 Test Workflow Completo")
    print("=" * 50)
    
    # 1. Crea una sessione di test
    strategy_config = {
        'ema_period': 10,
        'close_on_cross': True,
        'symbol': 'SHIB1000USDT'
    }
    
    session_id = trading_db.start_session(
        symbol='SHIB1000USDT',
        strategy_config=strategy_config,
        initial_balance=1000.0
    )
    
    print(f"✅ Sessione creata: {session_id}")
    
    # 2. Crea wrapper e apri una posizione fittizia
    wrapper = TradingWrapper()
    wrapper.set_session(session_id)
    
    print(f"\n🔧 Test apertura posizione manuale...")
    
    # Simula apertura manuale nel database
    trade_id = trading_db.add_trade(
        session_id=session_id,
        symbol='SHIB1000USDT',
        side='SELL',
        entry_price=0.013255,
        quantity=754,
        strategy_signal="TEST_MANUAL"
    )
    
    # Crea mappatura come farebbe il wrapper normale
    external_id = f"BYBIT_SHIB1000USDT_Sell_{int(time.time())}"
    trading_db.add_trade_id_mapping(trade_id, external_id, symbol='SHIB1000USDT', side='Sell')
    
    # Aggiungi agli active_trades
    wrapper.active_trades[trade_id] = {
        'symbol': 'SHIB1000USDT',
        'side': 'Sell',
        'quantity': 754,
        'entry_price': 0.013255,
        'external_trade_id': external_id,
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"✅ Posizione aperta: {trade_id}")
    print(f"📋 External ID: {external_id}")
    
    # 3. Verifica stato normale
    print(f"\n📊 Stato normale - Trade attivi: {len(wrapper.active_trades)}")
    for tid, tinfo in wrapper.active_trades.items():
        print(f"   📋 {tid}: {tinfo['side']} {tinfo['symbol']} {tinfo['quantity']}")
    
    # 4. Simula recovery - crea un nuovo wrapper
    print(f"\n🔄 Simulazione Recovery...")
    recovery_wrapper = TradingWrapper()
    
    # Sync con database (simula recovery)
    print(f"📋 Sync database...")
    recovery_wrapper.set_session(session_id)  # Questo farà il sync automaticamente
    
    print(f"📊 Dopo sync database - Trade attivi: {len(recovery_wrapper.active_trades)}")
    for tid, tinfo in recovery_wrapper.active_trades.items():
        print(f"   📋 {tid}: {tinfo['side']} {tinfo['symbol']} {tinfo['quantity']}")
    
    # 5. Test chiusura con ID originale
    print(f"\n🔄 Test chiusura con trade_id originale...")
    
    close_result = recovery_wrapper.close_position(
        trade_id=trade_id,
        price=0.013250,
        reason="TEST_CLOSE"
    )
    
    print(f"📊 Risultato chiusura: {close_result}")
    
    if close_result.get('success'):
        print("✅ Chiusura riuscita!")
        
        # Verifica stato finale
        print(f"📊 Trade attivi finali: {len(recovery_wrapper.active_trades)}")
        
        # Verifica nel database
        trades_final = trading_db.get_trade_history(session_id, 10)
        closed_trades = [t for t in trades_final if t['status'] == 'CLOSED']
        open_trades = [t for t in trades_final if t['status'] == 'OPEN']
        
        print(f"📊 Database - Trade aperti: {len(open_trades)}, Trade chiusi: {len(closed_trades)}")
        
    else:
        print(f"❌ Chiusura fallita: {close_result.get('error')}")
    
    # 6. Test con external_id
    if len(recovery_wrapper.active_trades) == 0:
        print(f"\n🔄 Test chiusura tramite symbol+side...")
        
        # Aggiungi di nuovo la posizione per testare chiusura via symbol+side
        recovery_wrapper.active_trades[trade_id] = {
            'symbol': 'SHIB1000USDT',
            'side': 'Sell',
            'quantity': 754,
            'entry_price': 0.013255,
            'external_trade_id': external_id,
            'timestamp': datetime.now().isoformat()
        }
        
        close_result2 = recovery_wrapper.close_position(
            symbol='SHIB1000USDT',
            side='Sell',
            price=0.013240,
            reason="TEST_SYMBOL_SIDE"
        )
        
        print(f"📊 Risultato chiusura symbol+side: {close_result2}")
    
    # 7. Cleanup
    print(f"\n🧹 Cleanup sessione test...")
    trading_db.end_session(session_id, 1000.0)
    
    print("\n✅ Test workflow completato")

if __name__ == "__main__":
    test_complete_workflow()
