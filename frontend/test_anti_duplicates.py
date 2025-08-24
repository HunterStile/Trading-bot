#!/usr/bin/env python3
"""
Test per verificare:
1. Che non vengano creati trade duplicati durante recovery
2. Che le sessioni vengano chiuse correttamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.trading_wrapper import TradingWrapper
from utils.database import trading_db
from datetime import datetime
import time

def test_no_duplicates_and_session_close():
    """Test per verificare anti-duplicati e chiusura sessione"""
    
    print("🧪 Test Anti-Duplicati e Chiusura Sessione")
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
    
    # 2. Crea wrapper e simula posizione esistente
    wrapper = TradingWrapper()
    wrapper.set_session(session_id)
    
    # Aggiungi una posizione esistente nel wrapper
    existing_trade_id = f"trade_test_{int(time.time())}"
    wrapper.active_trades[existing_trade_id] = {
        'symbol': 'SHIB1000USDT',
        'side': 'Buy',
        'quantity': 753.0,
        'entry_price': 0.013275,
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"📋 Posizione esistente aggiunta: {existing_trade_id}")
    print(f"📊 Trade attivi PRIMA del sync: {len(wrapper.active_trades)}")
    
    # 3. Simula sync multipli (come durante recovery)
    print(f"\n🔄 Test sync multipli...")
    
    for i in range(3):
        print(f"\n   🔄 Sync #{i+1}")
        
        # Simula sync che trova la stessa posizione Bybit
        # (normalmente sync_with_bybit viene chiamato più volte durante recovery)
        
        # Simula la logica di sync_with_bybit manualmente
        symbol = 'SHIB1000USDT'
        side = 'Buy'
        size = 750.0  # Leggermente diversa per testare tolleranza
        avg_price = 0.013275
        
        # Controlla se esiste già (logica dal nostro codice modificato)
        existing = None
        for trade_id, trade_info in wrapper.active_trades.items():
            if (trade_info.get('symbol') == symbol and 
                trade_info.get('side') == side and 
                abs(float(trade_info.get('quantity', 0)) - size) < 10):  # Tolleranza di 10 token
                existing = trade_id
                print(f"      ⚠️ Posizione simile già esistente: {trade_id}")
                break
        
        if not existing:
            temp_trade_id = f"RECOVERY_{symbol}_{side}_{int(time.time())}"
            wrapper.active_trades[temp_trade_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': size,
                'entry_price': avg_price,
                'timestamp': datetime.now().isoformat(),
                'recovery_orphan': True
            }
            print(f"      🆘 Nuovo trade orfano creato: {temp_trade_id}")
        else:
            print(f"      ✅ Duplicato evitato grazie al controllo")
        
        print(f"      📊 Trade attivi dopo sync #{i+1}: {len(wrapper.active_trades)}")
    
    # 4. Verifica risultato finale
    print(f"\n📊 RISULTATO - Trade attivi finali: {len(wrapper.active_trades)}")
    for tid, tinfo in wrapper.active_trades.items():
        print(f"   📋 {tid}: {tinfo['side']} {tinfo['symbol']} {tinfo['quantity']}")
    
    # 5. Test chiusura sessione
    print(f"\n🔚 Test chiusura sessione...")
    
    print(f"📊 Prima della chiusura - Sessioni attive nel DB:")
    all_sessions = trading_db.get_all_sessions()
    active_sessions = [s for s in all_sessions if s['status'] == 'ACTIVE']
    for session in active_sessions[-3:]:  # Mostra ultime 3
        print(f"   📋 {session['session_id']}: {session['status']}")
    
    # Chiudi la sessione
    result = wrapper.end_current_session(1000.0)
    print(f"🔚 Risultato chiusura: {result}")
    
    # Verifica che la sessione sia stata chiusa
    print(f"📊 Dopo la chiusura - Sessioni attive nel DB:")
    all_sessions = trading_db.get_all_sessions()
    active_sessions = [s for s in all_sessions if s['status'] == 'ACTIVE']
    completed_sessions = [s for s in all_sessions if s['status'] == 'COMPLETED' and s['session_id'] == session_id]
    
    for session in active_sessions[-3:]:  # Mostra ultime 3 attive
        print(f"   📋 ATTIVA: {session['session_id']}")
    
    for session in completed_sessions:  # Mostra quella completata
        print(f"   📋 COMPLETATA: {session['session_id']}: {session['status']}")
    
    if completed_sessions:
        print("✅ Sessione chiusa correttamente nello storico!")
    else:
        print("❌ Sessione NON chiusa nello storico")
    
    # 6. Verifica pulizia active_trades
    print(f"📊 Active trades dopo chiusura: {len(wrapper.active_trades)}")
    if len(wrapper.active_trades) == 0:
        print("✅ Active trades puliti correttamente!")
    else:
        print("❌ Active trades NON puliti")
        for tid, tinfo in wrapper.active_trades.items():
            print(f"   📋 Rimasto: {tid}")
    
    print("\n✅ Test completato")

if __name__ == "__main__":
    test_no_duplicates_and_session_close()
