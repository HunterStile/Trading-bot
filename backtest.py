#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtesting Engine per Trading Bot
Testa le strategie EMA su dati storici senza rischi
"""

import sys
from datetime import datetime, timedelta
import pandas as pd
import traceback

try:
    from config import *
    from trading_functions import (
        get_kline_data,
        media_esponenziale,
        vedi_prezzo_moneta
    )
    print("✅ Import delle configurazioni riuscito!")
except ImportError as e:
    print(f"❌ Errore nell'import: {e}")
    sys.exit(1)

class BacktestEngine:
    def __init__(self, simbolo, categoria="linear", capitale_iniziale=1000):
        self.simbolo = simbolo
        self.categoria = categoria
        self.capitale_iniziale = capitale_iniziale
        self.capitale_attuale = capitale_iniziale
        self.posizione_aperta = False
        self.tipo_posizione = None  # True = Long, False = Short
        self.prezzo_entrata = 0
        self.quantita = 0
        self.trades = []
        self.equity_curve = []
        
    def print_header(self, title):
        """Stampa un header formattato"""
        print("\n" + "="*60)
        print(f"📊 {title}")
        print("="*60)
    
    def aggiungi_trade(self, tipo, prezzo, quantita, timestamp, motivo=""):
        """Registra un trade"""
        trade = {
            'timestamp': timestamp,
            'tipo': 'COMPRA' if tipo else 'VENDI',
            'prezzo': prezzo,
            'quantita': quantita,
            'capitale': self.capitale_attuale,
            'motivo': motivo
        }
        self.trades.append(trade)
        
    def apri_posizione(self, tipo_operazione, prezzo, timestamp, quantita_usdt, motivo=""):
        """Apre una posizione"""
        if self.posizione_aperta:
            return False
            
        self.posizione_aperta = True
        self.tipo_posizione = tipo_operazione
        self.prezzo_entrata = prezzo
        
        # Calcola la quantità di asset (es. BTC) che possiamo comprare con quantita_usdt
        self.quantita = quantita_usdt / prezzo
        
        # Non sottraiamo il capitale qui perché ora tutto il capitale viene investito
        # Il capitale sarà aggiornato solo alla chiusura della posizione
        
        self.aggiungi_trade(tipo_operazione, prezzo, self.quantita, timestamp, motivo)
        print(f"   💰 Aperta posizione {'LONG' if tipo_operazione else 'SHORT'}: "
              f"{self.quantita:.6f} {self.simbolo[:3]} @ ${prezzo:,.2f} "
              f"(Investiti: ${quantita_usdt:.2f})")
        return True
    
    def chiudi_posizione(self, prezzo, timestamp, motivo=""):
        """Chiude una posizione"""
        if not self.posizione_aperta:
            return False
            
        # Calcola il valore iniziale investito
        capitale_investito = self.quantita * self.prezzo_entrata
        
        # Calcola il valore attuale della posizione
        valore_attuale = self.quantita * prezzo
        
        # Calcola il P&L
        if self.tipo_posizione:  # Long
            # Per long: abbiamo comprato crypto, ora vendiamo
            pnl = valore_attuale - capitale_investito
            self.capitale_attuale = valore_attuale  # Il capitale diventa il valore della vendita
        else:  # Short  
            # Per short: abbiamo venduto crypto, ora ricompriamo
            pnl = capitale_investito - valore_attuale
            self.capitale_attuale = capitale_investito + pnl  # Capitale iniziale + profitto/perdita
            
        percentuale_pnl = (pnl / capitale_investito) * 100
        
        self.aggiungi_trade(not self.tipo_posizione, prezzo, self.quantita, timestamp, 
                          f"{motivo} - P&L: ${pnl:.2f} ({percentuale_pnl:+.2f}%)")
        
        print(f"   🔚 Chiusa posizione {'LONG' if self.tipo_posizione else 'SHORT'}: "
              f"{self.quantita:.6f} {self.simbolo[:3]} @ ${prezzo:,.2f} "
              f"P&L: ${pnl:.2f} ({percentuale_pnl:+.2f}%) - Capitale: ${self.capitale_attuale:.2f}")
        
        self.posizione_aperta = False
        self.tipo_posizione = None
        self.prezzo_entrata = 0
        self.quantita = 0
        
        return True
    
    def controlla_candele_ema_backtest(self, prezzi, ema_values, numero_candele, sopra=True):
        """Versione backtest di controlla_candele_sopra/sotto_ema"""
        if len(prezzi) < numero_candele or len(ema_values) < numero_candele:
            return 0
            
        candele_consecutive = 0
        for i in range(numero_candele):
            idx = -(i+1)  # Parti dall'ultima candela
            if sopra:
                if prezzi[idx] > ema_values[idx]:
                    candele_consecutive += 1
                else:
                    break
            else:
                if prezzi[idx] < ema_values[idx]:
                    candele_consecutive += 1
                else:
                    break
                    
        return candele_consecutive
    
    def calcola_distanza_ema(self, prezzo, ema_value):
        """Calcola la distanza percentuale dall'EMA"""
        return ((prezzo - ema_value) / ema_value) * 100
    
    def testa_strategia_ema(self, periodo_ema=10, candele_richieste=3, distanza_max=1.0, 
                          percentuale_capitale_per_trade=100, timeframe="30", giorni_backtest=30):
        """Testa la strategia EMA sui dati storici"""
        
        # Calcola il capitale effettivo per trade
        quantita_per_trade = (self.capitale_attuale * percentuale_capitale_per_trade) / 100
        
        self.print_header(f"BACKTEST STRATEGIA EMA - {self.simbolo}")
        print(f"📈 Simbolo: {self.simbolo}")
        print(f"⏰ Timeframe: {timeframe} minuti")
        print(f"📊 EMA Periodo: {periodo_ema}")
        print(f"🕯️ Candele richieste: {candele_richieste}")
        print(f"📏 Distanza max EMA: {distanza_max}%")
        print(f"💰 Capitale totale: ${self.capitale_attuale:.2f}")
        print(f"💰 Percentuale per trade: {percentuale_capitale_per_trade}%")
        print(f"💰 Capitale per trade: ${quantita_per_trade:.2f}")
        print(f"📅 Periodo test: {giorni_backtest} giorni")
        
        # Calcola il limite di candele necessarie basato sul timeframe
        if timeframe == "M":
            limit = max(24, periodo_ema + 10)  # Minimo 24 candele mensili (2 anni)
        elif timeframe == "W":
            limit = max(52, periodo_ema + 10)  # Minimo 52 candele settimanali (1 anno)
        elif timeframe == "D":
            limit = max(giorni_backtest + periodo_ema + 10, 100)
        elif timeframe == "720":  # 12 ore
            limit = (giorni_backtest * 2) + periodo_ema + 10
        elif timeframe == "360":  # 6 ore
            limit = (giorni_backtest * 4) + periodo_ema + 10
        elif timeframe == "240":  # 4 ore
            limit = (giorni_backtest * 6) + periodo_ema + 10
        elif timeframe == "120":  # 2 ore
            limit = (giorni_backtest * 12) + periodo_ema + 10
        elif timeframe == "60":   # 1 ora
            limit = (giorni_backtest * 24) + periodo_ema + 10
        elif timeframe == "30":   # 30 minuti
            limit = (giorni_backtest * 48) + periodo_ema + 10
        elif timeframe == "15":   # 15 minuti
            limit = (giorni_backtest * 96) + periodo_ema + 10
        elif timeframe == "5":    # 5 minuti
            limit = (giorni_backtest * 288) + periodo_ema + 10
        elif timeframe == "3":    # 3 minuti
            limit = (giorni_backtest * 480) + periodo_ema + 10
        elif timeframe == "1":    # 1 minuto
            limit = (giorni_backtest * 1440) + periodo_ema + 10
        else:
            limit = 200
            
        # Bybit ha limiti sulle richieste (max 1000 per chiamata)
        limit = min(limit, 1000)
        
        print(f"📥 Scarico {limit} candele...")
        
        # Ottieni dati storici
        kline_data = get_kline_data(self.categoria, self.simbolo, timeframe, limit=limit)
        
        if not kline_data or len(kline_data) < periodo_ema + candele_richieste:
            print("❌ Dati insufficienti per il backtest")
            return
        
        # Prepara i dati
        timestamps = [int(candle[0]) for candle in reversed(kline_data)]
        opens = [float(candle[1]) for candle in reversed(kline_data)]
        highs = [float(candle[2]) for candle in reversed(kline_data)]
        lows = [float(candle[3]) for candle in reversed(kline_data)]
        closes = [float(candle[4]) for candle in reversed(kline_data)]
        
        # Calcola EMA
        ema_values = media_esponenziale(closes, periodo_ema)
        
        print(f"✅ Elaboro {len(closes)} candele per il backtest...")
        print(f"📊 Range prezzi: ${min(closes):.2f} - ${max(closes):.2f}")
        
        # Simula il trading
        segnali_long = 0
        segnali_short = 0
        
        for i in range(periodo_ema + candele_richieste, len(closes)):
            timestamp = timestamps[i]
            prezzo_attuale = closes[i]
            ema_attuale = ema_values[i]
            
            # Registra equity curve
            equity_point = {
                'timestamp': timestamp,
                'prezzo': prezzo_attuale,
                'capitale': self.capitale_attuale,
                'ema': ema_attuale
            }
            self.equity_curve.append(equity_point)
            
            # Controlla segnali solo se non abbiamo posizioni aperte
            if not self.posizione_aperta:
                
                # Segnale LONG: candele sopra EMA
                candele_sopra = self.controlla_candele_ema_backtest(
                    closes[:i+1], ema_values[:i+1], candele_richieste, sopra=True
                )
                
                if candele_sopra >= candele_richieste:
                    distanza = self.calcola_distanza_ema(prezzo_attuale, ema_attuale)
                    
                    if distanza <= distanza_max and distanza >= 0:
                        # Apri posizione LONG
                        if self.apri_posizione(True, prezzo_attuale, timestamp, quantita_per_trade,
                                             f"LONG: {candele_sopra} candele sopra EMA, dist: {distanza:.2f}%"):
                            segnali_long += 1
                
                # Segnale SHORT: candele sotto EMA
                candele_sotto = self.controlla_candele_ema_backtest(
                    closes[:i+1], ema_values[:i+1], candele_richieste, sopra=False
                )
                
                if candele_sotto >= candele_richieste:
                    distanza = self.calcola_distanza_ema(prezzo_attuale, ema_attuale)
                    
                    if abs(distanza) <= distanza_max and distanza <= 0:
                        # Apri posizione SHORT
                        if self.apri_posizione(False, prezzo_attuale, timestamp, quantita_per_trade,
                                             f"SHORT: {candele_sotto} candele sotto EMA, dist: {distanza:.2f}%"):
                            segnali_short += 1
            
            else:
                # Controlla uscita (trailing stop)
                if self.tipo_posizione:  # Long aperta
                    candele_sotto = self.controlla_candele_ema_backtest(
                        closes[:i+1], ema_values[:i+1], candele_richieste, sopra=False
                    )
                    
                    if candele_sotto >= candele_richieste:
                        self.chiudi_posizione(prezzo_attuale, timestamp, 
                                            f"TRAILING STOP LONG: {candele_sotto} candele sotto EMA")
                
                else:  # Short aperta
                    candele_sopra = self.controlla_candele_ema_backtest(
                        closes[:i+1], ema_values[:i+1], candele_richieste, sopra=True
                    )
                    
                    if candele_sopra >= candele_richieste:
                        self.chiudi_posizione(prezzo_attuale, timestamp,
                                            f"TRAILING STOP SHORT: {candele_sopra} candele sopra EMA")
        
        # Chiudi eventuale posizione aperta alla fine
        if self.posizione_aperta:
            self.chiudi_posizione(closes[-1], timestamps[-1], "FINE BACKTEST")
        
        # Analizza risultati
        self.analizza_risultati(segnali_long, segnali_short)

    def analizza_risultati(self, segnali_long, segnali_short):
        """Analizza e mostra i risultati del backtest"""
        
        self.print_header("RISULTATI BACKTEST")
        
        # Statistiche generali
        rendimento_totale = self.capitale_attuale - self.capitale_iniziale
        rendimento_percentuale = (rendimento_totale / self.capitale_iniziale) * 100
        numero_trades = len(self.trades) // 2  # Ogni trade ha apertura e chiusura
        
        print(f"💰 Capitale iniziale: ${self.capitale_iniziale:.2f}")
        print(f"💰 Capitale finale: ${self.capitale_attuale:.2f}")
        print(f"📈 Rendimento: ${rendimento_totale:.2f} ({rendimento_percentuale:.2f}%)")
        print(f"🔄 Numero di trades: {numero_trades}")
        print(f"📊 Segnali Long: {segnali_long}")
        print(f"📊 Segnali Short: {segnali_short}")
        
        if numero_trades > 0:
            # Analizza trades individuali
            trades_chiusi = []
            for i in range(0, len(self.trades), 2):
                if i + 1 < len(self.trades):
                    apertura = self.trades[i]
                    chiusura = self.trades[i + 1]
                    
                    if apertura['tipo'] == 'COMPRA':
                        pnl = (chiusura['prezzo'] - apertura['prezzo']) * apertura['quantita']
                    else:
                        pnl = (apertura['prezzo'] - chiusura['prezzo']) * apertura['quantita']
                    
                    trades_chiusi.append({
                        'apertura': apertura,
                        'chiusura': chiusura,
                        'pnl': pnl,
                        'durata': chiusura['timestamp'] - apertura['timestamp']
                    })
            
            if trades_chiusi:
                pnl_trades = [t['pnl'] for t in trades_chiusi]
                trades_vincenti = [t for t in trades_chiusi if t['pnl'] > 0]
                trades_perdenti = [t for t in trades_chiusi if t['pnl'] < 0]
                
                print(f"\n📊 ANALISI TRADES:")
                print(f"✅ Trades vincenti: {len(trades_vincenti)} ({len(trades_vincenti)/len(trades_chiusi)*100:.1f}%)")
                print(f"❌ Trades perdenti: {len(trades_perdenti)} ({len(trades_perdenti)/len(trades_chiusi)*100:.1f}%)")
                
                if trades_vincenti:
                    avg_win = sum(t['pnl'] for t in trades_vincenti) / len(trades_vincenti)
                    print(f"💚 Guadagno medio vincente: ${avg_win:.2f}")
                
                if trades_perdenti:
                    avg_loss = sum(t['pnl'] for t in trades_perdenti) / len(trades_perdenti)
                    print(f"💔 Perdita media perdente: ${avg_loss:.2f}")
                
                print(f"🎯 Miglior trade: ${max(pnl_trades):.2f}")
                print(f"💥 Peggior trade: ${min(pnl_trades):.2f}")
        
        # Mostra ultimi trades
        print(f"\n📋 ULTIMI TRADES:")
        for trade in self.trades[-6:]:  # Ultimi 6 movimenti
            dt = datetime.fromtimestamp(trade['timestamp']/1000)
            print(f"   {trade['tipo']} {trade['quantita']:.6f} @ ${trade['prezzo']:.2f} "
                  f"({dt.strftime('%m-%d %H:%M')}) - {trade['motivo']}")
        
        # Raccomandazioni
        print(f"\n💡 RACCOMANDAZIONI:")
        if rendimento_percentuale > 5:
            print("   ✅ Strategia promettente! Considera di usarla con capitale reale")
        elif rendimento_percentuale > 0:
            print("   ⚠️  Strategia marginalmente profittevole. Ottimizza i parametri")
        else:
            print("   ❌ Strategia non profittevole. Rivedi parametri o cambia approccio")
            
        if numero_trades > 0:
            win_rate = len(trades_vincenti) / len(trades_chiusi) * 100 if trades_chiusi else 0
            if win_rate > 60:
                print("   ✅ Win rate eccellente (>60%)")
            elif win_rate > 50:
                print("   ⚠️  Win rate accettabile (>50%)")
            else:
                print("   ❌ Win rate troppo basso (<50%)")

def menu_backtest():
    """Menu principale per il backtesting"""
    print("\n🚀 BACKTESTING ENGINE - TRADING BOT")
    print("="*50)
    
    while True:
        print("\n📊 MENU BACKTEST:")
        print("1. 🔥 Test strategia EMA - BTCUSDT (Raccomandato)")
        print("2. ⚡ Test strategia EMA - ETHUSDT")
        print("3. 🎯 Test strategia EMA - Simbolo personalizzato")
        print("4. 🧪 Test multipli parametri (Ottimizzazione)")
        print("5. 📈 Confronto timeframes")
        print("0. ❌ Esci")
        
        scelta = input("\n👉 Scegli un'opzione: ").strip()
        
        if scelta == "1":
            test_singolo("BTCUSDT")
        elif scelta == "2":
            test_singolo("ETHUSDT")
        elif scelta == "3":
            simbolo = input("📝 Inserisci simbolo (es. AVAXUSDT): ").strip().upper()
            if simbolo:
                test_singolo(simbolo)
        elif scelta == "4":
            test_ottimizzazione()
        elif scelta == "5":
            test_timeframes()
        elif scelta == "0":
            print("👋 Uscita dal backtesting...")
            break
        else:
            print("❌ Opzione non valida!")

def test_singolo(simbolo):
    """Test singolo con parametri personalizzabili"""
    print(f"\n🎯 BACKTEST SINGOLO - {simbolo}")
    
    # Parametri default
    periodo_ema = 10
    candele = 3
    distanza = 1.0
    capitale = 1000
    percentuale_capitale = 100  # Usa tutto il capitale per trade
    timeframe = "30"
    giorni = 30
    
    # Opzioni personalizzazione
    personalizza = input("🔧 Vuoi personalizzare i parametri? (s/N): ").strip().lower()
    
    if personalizza == 's':
        try:
            periodo_ema = int(input(f"📊 Periodo EMA (default {periodo_ema}): ") or periodo_ema)
            candele = int(input(f"🕯️  Candele richieste (default {candele}): ") or candele)
            distanza = float(input(f"📏 Distanza max EMA % (default {distanza}): ") or distanza)
            capitale = float(input(f"💰 Capitale iniziale (default {capitale}): ") or capitale)
            percentuale_capitale = float(input(f"💰 Percentuale capitale per trade (default {percentuale_capitale}%): ") or percentuale_capitale)
            timeframe = input(f"⏰ Timeframe minuti (default {timeframe}): ") or timeframe
            giorni = int(input(f"📅 Giorni backtest (default {giorni}): ") or giorni)
        except ValueError:
            print("⚠️  Parametri non validi, uso default")
    
    # Esegui backtest
    engine = BacktestEngine(simbolo, capitale_iniziale=capitale)
    engine.testa_strategia_ema(
        periodo_ema=periodo_ema,
        candele_richieste=candele,
        distanza_max=distanza,
        percentuale_capitale_per_trade=percentuale_capitale,
        timeframe=timeframe,
        giorni_backtest=giorni
    )

def test_ottimizzazione():
    """Test con parametri multipli per trovare la combinazione migliore"""
    simbolo = input("📝 Simbolo da ottimizzare (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    
    print(f"\n🧪 OTTIMIZZAZIONE PARAMETRI - {simbolo}")
    print("⏳ Questo potrebbe richiedere alcuni minuti...")
    
    migliore_rendimento = -999999
    migliori_parametri = {}
    risultati = []
    
    # Test parametri diversi
    parametri_ema = [5, 10, 15, 20]
    parametri_candele = [2, 3, 4, 5]
    parametri_distanza = [0.5, 1.0, 1.5, 2.0]
    
    totale_test = len(parametri_ema) * len(parametri_candele) * len(parametri_distanza)
    test_corrente = 0
    
    for ema in parametri_ema:
        for candele in parametri_candele:
            for distanza in parametri_distanza:
                test_corrente += 1
                print(f"🔄 Test {test_corrente}/{totale_test}: EMA={ema}, Candele={candele}, Dist={distanza}%")
                
                try:
                    engine = BacktestEngine(simbolo, capitale_iniziale=1000)
                    engine.testa_strategia_ema(
                        periodo_ema=ema,
                        candele_richieste=candele,
                        distanza_max=distanza,
                        percentuale_capitale_per_trade=100,  # Usa tutto il capitale
                        timeframe="30",
                        giorni_backtest=30
                    )
                    
                    rendimento = ((engine.capitale_attuale - 1000) / 1000) * 100
                    risultati.append({
                        'ema': ema,
                        'candele': candele,
                        'distanza': distanza,
                        'rendimento': rendimento,
                        'capitale_finale': engine.capitale_attuale,
                        'trades': len(engine.trades) // 2
                    })
                    
                    if rendimento > migliore_rendimento:
                        migliore_rendimento = rendimento
                        migliori_parametri = {
                            'ema': ema,
                            'candele': candele,
                            'distanza': distanza,
                            'rendimento': rendimento
                        }
                        
                except Exception as e:
                    print(f"❌ Errore nel test: {e}")
    
    # Mostra risultati ottimizzazione
    print("\n🏆 RISULTATI OTTIMIZZAZIONE:")
    print("="*60)
    print(f"🥇 Migliori parametri:")
    print(f"   📊 EMA: {migliori_parametri.get('ema', 'N/A')}")
    print(f"   🕯️  Candele: {migliori_parametri.get('candele', 'N/A')}")
    print(f"   📏 Distanza: {migliori_parametri.get('distanza', 'N/A')}%")
    print(f"   📈 Rendimento: {migliori_parametri.get('rendimento', 'N/A'):.2f}%")
    
    # Top 5 combinazioni
    risultati_ordinati = sorted(risultati, key=lambda x: x['rendimento'], reverse=True)
    print(f"\n🏅 TOP 5 COMBINAZIONI:")
    for i, r in enumerate(risultati_ordinati[:5]):
        print(f"   {i+1}. EMA={r['ema']}, Candele={r['candele']}, Dist={r['distanza']}% → {r['rendimento']:.2f}%")

def test_timeframes():
    """Test della stessa strategia su timeframe diversi"""
    simbolo = input("📝 Simbolo da testare (default BTCUSDT): ").strip().upper() or "BTCUSDT"
    
    timeframes = [
        ("1", "1 minuto"),
        ("3", "3 minuti"),
        ("5", "5 minuti"),
        ("15", "15 minuti"), 
        ("30", "30 minuti"),
        ("60", "1 ora"),
        ("120", "2 ore"),
        ("240", "4 ore"),
        ("360", "6 ore"),
        ("720", "12 ore"),
        ("D", "1 giorno"),
        ("W", "1 settimana"),
        ("M", "1 mese")
    ]
    
    print(f"\n📊 CONFRONTO TIMEFRAMES - {simbolo}")
    print("="*60)
    print("📋 Timeframes supportati da Bybit:")
    for tf, nome in timeframes:
        print(f"   • {tf} = {nome}")
    
    # Selezione timeframes da testare
    print(f"\n🎯 Seleziona timeframes da testare:")
    print("1. ⚡ Rapidi (1m, 5m, 15m, 30m)")
    print("2. 📊 Medi (1h, 4h, 12h, 1D)")
    print("3. 📈 Lunghi (1D, 1W, 1M)")
    print("4. 🎯 Personalizzati")
    print("5. 🔥 Tutti (richiede tempo)")
    
    scelta = input("\n👉 Scegli opzione (default 2): ").strip() or "2"
    
    if scelta == "1":
        timeframes_test = [("1", "1 minuto"), ("5", "5 minuti"), ("15", "15 minuti"), ("30", "30 minuti")]
    elif scelta == "2":
        timeframes_test = [("60", "1 ora"), ("240", "4 ore"), ("720", "12 ore"), ("D", "1 giorno")]
    elif scelta == "3":
        timeframes_test = [("D", "1 giorno"), ("W", "1 settimana"), ("M", "1 mese")]
    elif scelta == "4":
        print("📝 Inserisci timeframes separati da virgola (es: 5,30,240,D):")
        custom_tf = input("👉 Timeframes: ").strip().split(",")
        timeframes_test = []
        for tf in custom_tf:
            tf = tf.strip()
            nome = next((nome for tfk, nome in timeframes if tfk == tf), f"{tf} (custom)")
            timeframes_test.append((tf, nome))
    else:
        timeframes_test = timeframes
    
    risultati_tf = []
    
    for tf, nome in timeframes_test:
        print(f"\n⏰ Test timeframe: {nome}")
        try:
            # Calcola giorni backtest appropriati per il timeframe
            if tf in ["1", "3", "5"]:
                giorni = 7  # 1 settimana per timeframe molto corti
            elif tf in ["15", "30", "60"]:
                giorni = 14  # 2 settimane per timeframe corti
            elif tf in ["120", "240", "360"]:
                giorni = 30  # 1 mese per timeframe medi
            elif tf == "720":
                giorni = 60  # 2 mesi per 12 ore
            elif tf == "D":
                giorni = 90  # 3 mesi per giornaliero
            elif tf == "W":
                giorni = 365  # 1 anno per settimanale
            elif tf == "M":
                giorni = 730  # 2 anni per mensile
            else:
                giorni = 30  # default
            
            engine = BacktestEngine(simbolo, capitale_iniziale=1000)
            engine.testa_strategia_ema(
                periodo_ema=10,
                candele_richieste=3,
                distanza_max=1.0,
                percentuale_capitale_per_trade=100,  # Usa tutto il capitale
                timeframe=tf,
                giorni_backtest=giorni
            )
            
            rendimento = ((engine.capitale_attuale - 1000) / 1000) * 100
            numero_trades = len(engine.trades) // 2
            
            risultati_tf.append({
                'timeframe': nome,
                'tf_code': tf,
                'rendimento': rendimento,
                'trades': numero_trades,
                'giorni_testati': giorni
            })
            
        except Exception as e:
            print(f"❌ Errore su timeframe {nome}: {e}")
    
    # Mostra confronto
    print(f"\n📊 CONFRONTO RISULTATI:")
    print("="*60)
    risultati_tf_ord = sorted(risultati_tf, key=lambda x: x['rendimento'], reverse=True)
    
    for i, r in enumerate(risultati_tf_ord):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📊"
        print(f"{emoji} {r['timeframe']}: {r['rendimento']:.2f}% ({r['trades']} trades in {r['giorni_testati']} giorni)")
    
    # Raccomandazioni per timeframe
    if risultati_tf_ord:
        migliore = risultati_tf_ord[0]
        print(f"\n💡 RACCOMANDAZIONI:")
        print(f"🏆 Miglior timeframe: {migliore['timeframe']} ({migliore['rendimento']:.2f}%)")
        
        if migliore['tf_code'] in ["1", "3", "5"]:
            print("   ⚡ Timeframe molto veloce - Richiede monitoraggio costante")
        elif migliore['tf_code'] in ["15", "30", "60"]:
            print("   ⚖️  Timeframe bilanciato - Buon compromesso velocità/stabilità")
        elif migliore['tf_code'] in ["240", "720", "D"]:
            print("   🎯 Timeframe stabile - Meno stress, trades di qualità")
        else:
            print("   📈 Timeframe lungo - Per investimenti a lungo termine")

def mostra_timeframes_bybit():
    """Mostra tutti i timeframe supportati da Bybit"""
    print("\n📊 TIMEFRAMES SUPPORTATI DA BYBIT:")
    print("="*50)
    
    timeframes = {
        "🚀 MINUTI": [
            ("1", "1 minuto"),
            ("3", "3 minuti"),
            ("5", "5 minuti"),
            ("15", "15 minuti"),
            ("30", "30 minuti")
        ],
        "⏰ ORE": [
            ("60", "1 ora"),
            ("120", "2 ore"),
            ("240", "4 ore"),
            ("360", "6 ore"),
            ("720", "12 ore")
        ],
        "📅 PERIODI LUNGHI": [
            ("D", "1 giorno"),
            ("W", "1 settimana"),
            ("M", "1 mese")
        ]
    }
    
    for categoria, tf_list in timeframes.items():
        print(f"\n{categoria}:")
        for tf_code, tf_nome in tf_list:
            print(f"   • {tf_code:3} = {tf_nome}")
    
    print(f"\n💡 CONSIGLI:")
    print("   🚀 1-5 min: Scalping, molti trades, alta attenzione")
    print("   ⚖️  15-60 min: Day trading, buon equilibrio")
    print("   🎯 4h-1D: Swing trading, trades di qualità")
    print("   📈 1W-1M: Position trading, investimenti lunghi")

if __name__ == "__main__":
    try:
        menu_backtest()
    except KeyboardInterrupt:
        print("\n\n⏹️  Backtesting interrotto dall'utente")
    except Exception as e:
        print(f"\n💥 Errore imprevisto: {e}")
        print(f"📝 Traceback:\n{traceback.format_exc()}")
