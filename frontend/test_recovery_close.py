#!/usr/bin/env python3
"""
Test per verificare la chiusura delle posizioni durante recovery
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.trading_wrapper import TradingWrapper
from utils.database import trading_db
from datetime import datetime
import time

def test_recovery_close():
    """Test completo del sistema di recovery con chiusura posizioni"""
    
    print("🧪 Test Recovery e Chiusura Posizioni")
    print("=" * 50)
    
    # 1. Crea una sessione di test
    session_id = f"test_recovery_{int(time.time())}"
    
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
    
    # 2. Simula trading wrapper in modalità recovery
    wrapper = TradingWrapper()
    
    # Simula sync con Bybit che trova posizioni orfane
    print("\n🔄 Simulazione sync con Bybit...")
    
    # Aggiungi una posizione "orfana" manualmente
    temp_trade_id = f"RECOVERY_SHIB1000USDT_Sell_{int(time.time())}"
    external_id = f"BYBIT_SHIB1000USDT_Sell_{int(time.time())}"
    
    wrapper.active_trades[temp_trade_id] = {
        'symbol': 'SHIB1000USDT',
        'side': 'Sell',
        'quantity': 750.0,
        'entry_price': 0.013275,
        'timestamp': datetime.now().isoformat(),
        'bybit_sync': True,
        'external_trade_id': external_id,
        'recovery_orphan': True,
        'needs_session': True  # Questo è il flag che conta
    }
    
    print(f"🆘 Posizione orfana aggiunta: {temp_trade_id}")
    
    # 3. Imposta la sessione (questo dovrebbe registrare le posizioni orfane)
    print(f"\n📝 Impostazione sessione: {session_id}")
    orphan_count = wrapper.set_session(session_id)
    print(f"✅ Registrate {orphan_count} posizioni orfane")
    
    # 4. Verifica che la posizione sia stata registrata nel database
    print(f"\n🔍 Verifica registrazione nel database...")
    
    # Trova il nuovo trade_id nel database
    real_trade_id = None
    for trade_id in wrapper.active_trades:
        if trade_id != temp_trade_id and trade_id.startswith('trade_'):
            real_trade_id = trade_id
            break
    
    if real_trade_id:
        print(f"✅ Trade registrato con ID: {real_trade_id}")
        
        # Verifica nel database
        trades = trading_db.get_trade_history(session_id, 10)
        open_trades = [t for t in trades if t['status'] == 'OPEN']
        print(f"📊 Trade aperti nel database: {len(open_trades)}")
        
        for trade in open_trades:
            print(f"   📋 {trade['trade_id']}: {trade['side']} {trade['symbol']} {trade['quantity']}")
        
        # 5. Test di chiusura usando symbol+side
        print(f"\n🔄 Test chiusura per symbol+side...")
        
        close_result = wrapper.close_position(
            symbol='SHIB1000USDT',
            side='Sell',
            price=0.013270,
            reason="TEST_RECOVERY_CLOSE"
        )
        
        print(f"📊 Risultato chiusura: {close_result}")
        
        if close_result.get('success'):
            print("✅ Chiusura riuscita!")
            
            # Verifica che sia stato rimosso dagli active_trades
            print(f"📊 Trade attivi rimasti: {len(wrapper.active_trades)}")
            for tid, tinfo in wrapper.active_trades.items():
                print(f"   📋 {tid}: {tinfo['side']} {tinfo['symbol']} {tinfo['quantity']}")
            
            # Verifica nel database
            trades_after = trading_db.get_trade_history(session_id, 10)
            closed_trades = [t for t in trades_after if t['status'] == 'CLOSED']
            print(f"📊 Trade chiusi nel database: {len(closed_trades)}")
            
        else:
            print(f"❌ Chiusura fallita: {close_result.get('error')}")
            
    else:
        print("❌ Trade non trovato dopo registrazione")
    
    # 6. Test di chiusura usando trade_id diretto
    if len(wrapper.active_trades) > 0:
        print(f"\n🔄 Test chiusura per trade_id diretto...")
        active_trade_id = list(wrapper.active_trades.keys())[0]
        
        close_result2 = wrapper.close_position(
            trade_id=active_trade_id,
            price=0.013265,
            reason="TEST_DIRECT_ID_CLOSE"
        )
        
        print(f"📊 Risultato chiusura diretta: {close_result2}")
    
    # 7. Cleanup
    print(f"\n🧹 Cleanup sessione test...")
    trading_db.end_session(session_id, 1000.0)
    
    print("\n✅ Test completato")

if __name__ == "__main__":
    test_recovery_close()
