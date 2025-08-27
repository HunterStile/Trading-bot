"""
Test e Documentazione - Strategie di Uscita Avanzate per Crypto Trading Bot

Questo file contiene:
1. Test delle nuove strategie
2. Esempi di configurazione  
3. Documentazione d'uso
4. Scenarios per pump&dump

Author: Luigi's Trading Bot
Date: 2025
"""

import sys
import os

# Aggiungi il percorso del trading bot
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from frontend.utils.advanced_exit_strategies import (
        AdvancedExitManager, create_advanced_exit_manager, 
        analyze_advanced_exit_conditions, EXAMPLE_ADVANCED_EXIT_CONFIG
    )
    print("✅ Import successful - Advanced Exit Strategies loaded")
except ImportError as e:
    print(f"❌ Import error: {e}")

def test_configuration_examples():
    """Esempi di configurazione per diverse situazioni di trading"""
    
    print("\n" + "="*60)
    print("📋 ESEMPI DI CONFIGURAZIONE STRATEGIE AVANZATE")
    print("="*60)
    
    # Configurazione CONSERVATIVA (per principianti)
    conservative_config = {
        'enable_multi_timeframe': True,
        'enable_dynamic_trailing': False,  # Disattivato per semplicità
        'enable_quick_exit': True,
        
        'spike_threshold': 2.0,           # Attiva MTF già al 2%
        'volatile_threshold': 4.0,        # Quick exit al 4%
        'trailing_stop_percent': 3.0,     # Trailing più largo
        'advanced_exit_debug': True
    }
    
    # Configurazione AGGRESSIVA (per trader esperti)
    aggressive_config = {
        'enable_multi_timeframe': True,
        'enable_dynamic_trailing': True,
        'enable_quick_exit': True,
        
        'spike_threshold': 1.5,           # MTF molto sensibile
        'volatile_threshold': 3.0,        # Quick exit rapido
        'trailing_stop_percent': 1.5,     # Trailing stretto
        'min_distance_for_trailing': 1.0, # Trailing attivo subito
        'advanced_exit_debug': False     # Meno log in prod
    }
    
    # Configurazione PUMP & DUMP (per altcoin volatili)
    pump_dump_config = {
        'enable_multi_timeframe': True,
        'enable_dynamic_trailing': True,
        'enable_quick_exit': True,
        
        'spike_threshold': 2.5,           # Balance tra sensibilità e rumore
        'volatile_threshold': 6.0,        # Tolleranza maggiore per pump normali
        'trailing_stop_percent': 2.5,     # Trailing moderato
        'min_distance_for_trailing': 2.0, # Attiva trailing solo su movimenti significativi
        'advanced_exit_debug': True      # Debug attivo per monitorare pump&dump
    }
    
    print("🛡️ CONSERVATIVA (principianti):")
    for key, value in conservative_config.items():
        print(f"   {key}: {value}")
    
    print("\n⚡ AGGRESSIVA (esperti):")
    for key, value in aggressive_config.items():
        print(f"   {key}: {value}")
        
    print("\n🎢 PUMP & DUMP (altcoin volatili):")
    for key, value in pump_dump_config.items():
        print(f"   {key}: {value}")
    
    return conservative_config, aggressive_config, pump_dump_config


def explain_strategies():
    """Spiega come funzionano le strategie"""
    
    print("\n" + "="*60)
    print("📚 COME FUNZIONANO LE STRATEGIE AVANZATE")
    print("="*60)
    
    print("""
🎯 1. MULTI-TIMEFRAME EXIT (MTF)
   
   Quando si attiva:
   • Il prezzo si allontana dalla EMA oltre 'spike_threshold' (default 3%)
   
   Come funziona:
   • Passa a monitorare un timeframe più piccolo (es. da 30m a 5m)  
   • Se ANCHE UNA SOLA candela chiude contro il trend su timeframe piccolo, CHIUDI
   • Per LONG: chiudi se 1 candela sotto EMA su timeframe piccolo
   • Per SHORT: chiudi se 1 candela sopra EMA su timeframe piccolo
   
   Vantaggio:
   • Uscita rapidissima su spike improvvisi
   • Ideale per pump&dump dove il reversal è veloce

🎯 2. DYNAMIC TRAILING STOP (DTS)
   
   Quando si attiva:
   • Il prezzo si allontana dalla EMA oltre 'spike_threshold' (default 3%)
   
   Come funziona:
   • Crea un trailing stop che segue il prezzo favorevole
   • Per LONG: stop sotto il prezzo, sale quando prezzo sale
   • Per SHORT: stop sopra il prezzo, scende quando prezzo scende
   • Si attiva solo se distanza EMA > 'min_distance_for_trailing'
   
   Vantaggio:
   • Segui il trend finché dura
   • Uscita automatica su retrace del 'trailing_stop_percent' (default 2%)

🎯 3. QUICK EXIT ON SPIKE 
   
   Quando si attiva:
   • Movimento estremo > 'volatile_threshold' (default 5%)
   
   Come funziona:
   • Uscita IMMEDIATA senza aspettare candele
   • Per LONG: esci se crollo > 5% sotto EMA
   • Per SHORT: esci se pump > 5% sopra EMA
   
   Vantaggio:
   • Protezione massima contro crash improvvisi
   • Zero ritardo su movimenti anomali
""")


def simulate_scenarios():
    """Simula scenari comuni di pump&dump"""
    
    print("\n" + "="*60) 
    print("🎬 SIMULAZIONE SCENARI PUMP & DUMP")
    print("="*60)
    
    scenarios = [
        {
            'name': 'PUMP GRADUALE',
            'description': 'Prezzo sale +4% in 2 ore, poi retrace -1.5%',
            'distance_percent': 4.0,
            'expected_mtf': 'Attivato - monitora timeframe piccolo',
            'expected_trailing': 'Attivato - segue il pump', 
            'expected_quick': 'Non attivato - sotto soglia 5%'
        },
        {
            'name': 'PUMP & DUMP VIOLENTO',
            'description': 'Prezzo esplode +8% poi crolla -6% in 10 minuti',
            'distance_percent': -6.0,
            'expected_mtf': 'Attivato - uscita immediata su retrace',
            'expected_trailing': 'Attivato - stop loss trailing',
            'expected_quick': 'ATTIVATO - USCITA IMMEDIATA!'
        },
        {
            'name': 'OSCILLAZIONE NORMALE',
            'description': 'Prezzo oscilla ±1.5% attorno alla EMA',
            'distance_percent': 1.5,
            'expected_mtf': 'Non attivato - sotto soglia 3%',
            'expected_trailing': 'Non attivato - sotto soglia 3%',
            'expected_quick': 'Non attivato - movimento normale'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 SCENARIO: {scenario['name']}")
        print(f"   Descrizione: {scenario['description']}")
        print(f"   Distanza EMA: {scenario['distance_percent']:+.1f}%")
        print(f"   🎯 Multi-Timeframe: {scenario['expected_mtf']}")
        print(f"   🎯 Trailing Stop: {scenario['expected_trailing']}")
        print(f"   🎯 Quick Exit: {scenario['expected_quick']}")


def configuration_guide():
    """Guida alla configurazione ottimale"""
    
    print("\n" + "="*60)
    print("⚙️ GUIDA CONFIGURAZIONE OTTIMALE")
    print("="*60)
    
    print("""
🔧 CONFIGURAZIONE BASE RACCOMANDATA:

Per la maggior parte delle crypto (BTC, ETH, major altcoin):
• spike_threshold: 3.0%           # Attiva strategie avanzate
• volatile_threshold: 5.0%        # Quick exit su movimenti estremi  
• trailing_stop_percent: 2.0%     # Trailing stop moderato
• enable_all: True                # Tutte le strategie attive

Per altcoin ad alta volatilità (nuovi token, meme coin):
• spike_threshold: 2.0%           # Più sensibile
• volatile_threshold: 8.0%        # Tolleranza maggiore per pump normali
• trailing_stop_percent: 3.0%     # Trailing più largo
• enable_all: True

Per stable coin / bassa volatilità:
• spike_threshold: 1.5%           # Molto sensibile
• volatile_threshold: 3.0%        # Quick exit su piccoli movimenti
• trailing_stop_percent: 1.0%     # Trailing stretto
• enable_multi_timeframe: True    # Solo MTF, trailing potrebbe essere troppo
• enable_dynamic_trailing: False
• enable_quick_exit: True

📈 ESEMPI PRATICI:

1. Bot su BTCUSDT 30m:
   • Normale: Esce dopo 3 candele sotto EMA (90 minuti)
   • Con MTF: Se spike >3%, monitora 5m. Esce appena 1 candela 5m contro trend (5 min max!)
   • Con Trailing: Su pump >3%, trailing 2%. Segue il pump, esce su retrace 2%
   • Con Quick: Su crash >5%, uscita immediata

2. Bot su DOGEUSDT 15m (volatile):
   • spike_threshold: 2.5%
   • volatile_threshold: 7.0%  
   • trailing_stop_percent: 2.5%
   • Bilanciamento tra reattività e falsi segnali

🚨 ATTENZIONE:
• Più basse le soglie = più uscite premature ma maggiore protezione
• Più alte le soglie = più profitti potenziali ma maggior rischio
• Testa sempre con piccole quantità prima!
""")


def usage_examples():
    """Esempi d'uso nel codice"""
    
    print("\n" + "="*60)
    print("💻 ESEMPI D'USO NEL CODICE")
    print("="*60)
    
    print("""
🔹 Come attivare nel bot_status (app.py):

bot_status = {
    # ... configurazioni esistenti ...
    
    # Advanced Exit Strategies
    'enable_multi_timeframe': True,
    'spike_threshold': 3.0,
    'enable_dynamic_trailing': True,
    'trailing_stop_percent': 2.0,
    'enable_quick_exit': True,
    'volatile_threshold': 5.0,
    'advanced_exit_debug': True
}

🔹 Le strategie si attivano automaticamente quando:

1. Multi-Timeframe Exit:
   • Distanza da EMA >= spike_threshold
   • Monitora automaticamente timeframe più piccolo
   • Chiude su prima candela avversa su timeframe piccolo

2. Dynamic Trailing Stop:
   • Distanza da EMA >= spike_threshold  
   • Crea trailing stop che segue il prezzo
   • Chiude su retrace >= trailing_stop_percent

3. Quick Exit:
   • Distanza da EMA >= volatile_threshold
   • Chiusura immediata senza aspettare

🔹 Priorità di esecuzione:
1. Quick Exit (priorità ALTA)      → Chiusura immediata su spike estremi
2. Multi-Timeframe (priorità ALTA) → Chiusura rapida su timeframe piccoli
3. Trailing Stop (priorità MEDIA)  → Segui trend con protezione
4. EMA Standard (priorità BASSA)   → Logica tradizionale del bot

🔹 Logging e Debug:
Tutte le strategie loggano dettagli con tag [MTF], [DTS], [SPIKE] per debug.
""")


def main():
    """Esegue tutti i test e mostra documentazione"""
    
    print("🚀 TESTING ADVANCED EXIT STRATEGIES")
    print("="*60)
    
    # Test configurazioni
    conservative, aggressive, pump_dump = test_configuration_examples()
    
    # Spiegazione strategie
    explain_strategies()
    
    # Simulazioni scenari
    simulate_scenarios()
    
    # Guida configurazione
    configuration_guide()
    
    # Esempi d'uso
    usage_examples()
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETATO - STRATEGIE PRONTE PER L'USO!")
    print("="*60)
    
    print("""
🎯 PROSSIMI PASSI:

1. Modifica frontend/app.py per configurare le soglie che preferisci
2. Riavvia il bot con la nuova configurazione
3. Monitora i log per vedere quando si attivano le strategie
4. Regola le soglie in base ai risultati

🔥 CONFIGURAZIONE VELOCE:
Per partire subito, le configurazioni di default dovrebbero andare bene.
Le strategie si attivano automaticamente quando necessario!

📱 LOGS DA MONITORARE:
• [MTF] Multi-Timeframe Exit attivato
• [DTS] Trailing stop aggiornato  
• [SPIKE] Quick exit triggered
• 🚨 ADVANCED EXIT TRIGGERED!

🎮 SUGGERIMENTO:
Inizia con bot_status['advanced_exit_debug'] = True per vedere 
tutti i dettagli delle decisioni delle strategie.
""")


if __name__ == "__main__":
    main()
