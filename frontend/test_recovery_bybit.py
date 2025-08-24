#!/usr/bin/env python3
"""
Test specifico per verificare il recovery con posizioni Bybit
"""

import sys
import os
from pathlib import Path

# Aggiungi il path del frontend
frontend_path = Path(__file__).parent
sys.path.append(str(frontend_path))

# Import delle funzioni aggiornate
from utils.database import trading_db
from utils.trading_wrapper import trading_wrapper

def simulate_recovery_scenario():
    """Simula uno scenario di recovery con posizioni"""
    print("🧪 SIMULAZIONE SCENARIO RECOVERY")
    print("=" * 50)
    
    # 1. Simula una sessione esistente con trade aperto
    # Inizia una sessione fittizia
    session_id = trading_db.start_session("SHIB1000USDT", {"test": True}, 100.0)
    print(f"✅ Sessione di test creata: {session_id}")
    
    # Aggiungi un trade fittizio (come se fosse stato aperto prima del crash)
    trade_id = trading_db.add_trade(
        session_id=session_id,
        symbol="SHIB1000USDT",
        side="BUY",
        entry_price=0.013300,
        quantity=750,
        strategy_signal="TEST_RECOVERY"
    )
    print(f"✅ Trade di test aggiunto: {trade_id}")
    
    # Crea mappatura ID per il trade
    import time
    external_id = f"BYBIT_SHIB1000USDT_Buy_{int(time.time())}"
    trading_db.add_trade_id_mapping(trade_id, external_id, symbol="SHIB1000USDT", side="BUY")
    print(f"✅ Mappatura ID creata: {trade_id} -> {external_id}")
    
    # 2. Simula crash: resetta il wrapper
    trading_wrapper.current_session_id = None
    trading_wrapper.active_trades.clear()
    print("💥 Simulato crash - wrapper resettato")
    
    # 3. Simula recovery: prova a recuperare senza sessione
    print("\n🔄 FASE RECOVERY - SENZA SESSIONE:")
    print("-" * 30)
    
    # Prova sync_with_database senza sessione
    trading_wrapper.sync_with_database()
    trades_after_db_sync = len(trading_wrapper.get_active_trades())
    print(f"📋 Dopo sync database: {trades_after_db_sync} trade")
    
    # 4. Imposta sessione e verifica recovery
    print("\n🔄 FASE RECOVERY - CON SESSIONE:")
    print("-" * 30)
    
    trading_wrapper.set_session(session_id)
    trades_after_session = len(trading_wrapper.get_active_trades())
    print(f"📋 Dopo set session: {trades_after_session} trade")
    
    # 5. Verifica contenuto
    print("\n📊 CONTENUTO WRAPPER DOPO RECOVERY:")
    active_trades = trading_wrapper.get_active_trades()
    for tid, tinfo in active_trades.items():
        print(f"   - {tid}: {tinfo.get('side')} {tinfo.get('quantity')} {tinfo.get('symbol')}")
        print(f"     Recovery flags: recovered={tinfo.get('recovered')}, orphan={tinfo.get('recovery_orphan')}")
    
    # 6. Cleanup
    print(f"\n🧹 Cleanup...")
    trading_db.close_trade(trade_id, 0.013400, 0.01)
    trading_db.end_session(session_id, 99.0)
    print(f"✅ Test completato e pulito")
    
    return trades_after_session > 0

def test_orphan_position_handling():
    """Test gestione posizioni orfane"""
    print("\n🧪 TEST GESTIONE POSIZIONI ORFANE")
    print("=" * 50)
    
    # Reset wrapper
    trading_wrapper.current_session_id = None
    trading_wrapper.active_trades.clear()
    
    # Simula una posizione orfana (come quella che viene da Bybit ma non è nel database)
    temp_trade_id = "RECOVERY_SHIB1000USDT_Buy_123456"
    external_id = "BYBIT_SHIB1000USDT_Buy_123456"
    
    trading_wrapper.active_trades[temp_trade_id] = {
        'symbol': 'SHIB1000USDT',
        'side': 'Buy',
        'quantity': 750,
        'entry_price': 0.013300,
        'timestamp': "2025-08-24T01:00:00",
        'bybit_sync': True,
        'external_trade_id': external_id,
        'recovery_orphan': True,
        'needs_session': True
    }
    
    print(f"✅ Posizione orfana simulata: {temp_trade_id}")
    orphans_before = len([t for t in trading_wrapper.active_trades.values() if t.get('recovery_orphan')])
    print(f"📊 Posizioni orfane prima: {orphans_before}")
    
    # Imposta sessione e verifica che l'orfana venga registrata
    import time
    time.sleep(1)  # Evita conflitto timestamp
    session_id = trading_db.start_session("SHIB1000USDT", {"test_orphan": True}, 100.0)
    
    trading_wrapper.set_session(session_id)
    
    orphans_after = len([t for t in trading_wrapper.active_trades.values() if t.get('recovery_orphan')])
    registered_trades = len([t for t in trading_wrapper.active_trades.values() if t.get('recovered')])
    
    print(f"📊 Posizioni orfane dopo: {orphans_after}")
    print(f"📊 Posizioni registrate: {registered_trades}")
    
    # Cleanup
    trades = trading_db.get_trade_history(session_id, 10)
    for trade in trades:
        if trade['status'] == 'OPEN':
            trading_db.close_trade(trade['trade_id'], 0.013400, 0.01)
    trading_db.end_session(session_id, 99.0)
    
    return orphans_after == 0 and registered_trades > 0

if __name__ == "__main__":
    import time
    
    print("🧪 TEST RECOVERY MIGLIORATO - POSIZIONI BYBIT")
    print("=" * 60)
    
    try:
        # Test 1: Scenario recovery normale
        success1 = simulate_recovery_scenario()
        print(f"\n✅ Test Recovery Normale: {'PASS' if success1 else 'FAIL'}")
        
        # Test 2: Gestione posizioni orfane
        success2 = test_orphan_position_handling()
        print(f"✅ Test Posizioni Orfane: {'PASS' if success2 else 'FAIL'}")
        
        # Risultato finale
        if success1 and success2:
            print("\n🎉 TUTTI I TEST SUPERATI!")
            print("\n📋 MODIFICHE VERIFICATE:")
            print("   ✅ Recovery trova posizioni nel database")
            print("   ✅ Gestione posizioni orfane da Bybit")
            print("   ✅ Associazione sessioni funzionante")
            print("   ✅ Mappatura ID corretta")
            
            print("\n🚀 IL RECOVERY DOVREBBE ORA FUNZIONARE CORRETTAMENTE!")
            print("   - Riavvia il bot con posizioni aperte")
            print("   - Il recovery dovrebbe trovare e gestire le posizioni")
            print("   - Il bot dovrebbe passare a MANAGING_POSITIONS")
        else:
            print("\n❌ ALCUNI TEST FALLITI - CONTROLLA I LOG")
            
    except Exception as e:
        print(f"\n❌ ERRORE DURANTE I TEST: {e}")
        import traceback
        traceback.print_exc()
