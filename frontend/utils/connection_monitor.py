#!/usr/bin/env python3
"""
Connection Monitor per Trading Bot
Sistema che monitora la connessione internet e gestisce il bot di conseguenza
"""

import threading
import time
import requests
import socket
from datetime import datetime
from typing import Callable, Optional

class ConnectionMonitor:
    """Monitora la connessione internet e gestisce il trading bot"""
    
    def __init__(self, 
                 bot_control_callback: Callable = None,
                 notification_callback: Callable = None,
                 check_interval: int = 30):
        """
        Args:
            bot_control_callback: Funzione per controllare bot (start/stop)
            notification_callback: Funzione per inviare notifiche
            check_interval: Intervallo controllo in secondi
        """
        self.bot_control_callback = bot_control_callback
        self.notification_callback = notification_callback
        self.check_interval = check_interval
        
        self.is_online = True
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Timestamp per gestire notifiche
        self.last_offline_notification = None
        self.last_online_notification = None
        self.offline_duration = None
        
        # Lista di servizi da testare (backup se uno fallisce)
        self.test_endpoints = [
            "https://api.bybit.com/v5/market/time",  # Bybit API (prioritario)
            "https://www.google.com",                # Google (backup)
            "https://1.1.1.1",                      # Cloudflare DNS (backup)
        ]
    
    def test_internet_connection(self) -> bool:
        """Testa la connessione internet con multiple endpoints"""
        
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(endpoint, timeout=10)
                if response.status_code in [200, 201, 202]:
                    return True
            except (requests.RequestException, socket.error):
                continue
        
        # Se tutti i test falliscono, proviamo anche un test DNS
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except socket.error:
            pass
        
        return False
    
    def test_bybit_connection(self) -> bool:
        """Testa specificamente la connessione a Bybit"""
        try:
            response = requests.get(
                "https://api.bybit.com/v5/market/time", 
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def _handle_connection_lost(self):
        """Gestisce quando la connessione viene persa"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ CONNESSIONE INTERNET PERSA!")
        
        # Ferma il bot se sta girando
        if self.bot_control_callback:
            try:
                self.bot_control_callback('stop', 'CONNECTION_LOST')
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Bot fermato automaticamente")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore fermata bot: {e}")
        
        # Invia notifica (se possibile via metodi alternativi)
        if self.notification_callback:
            try:
                self.notification_callback(
                    "OFFLINE", 
                    "🚨 CONNESSIONE INTERNET PERSA!\n"
                    "🛑 Trading bot fermato automaticamente\n"
                    "⏳ Monitoraggio riconnessione attivo...",
                    priority="HIGH"
                )
            except:
                pass  # Notifica probabilmente fallirà se siamo offline
        
        self.last_offline_notification = datetime.now()
    
    def _handle_connection_restored(self):
        """Gestisce quando la connessione viene ripristinata"""
        offline_duration = None
        if self.last_offline_notification:
            offline_duration = datetime.now() - self.last_offline_notification
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ CONNESSIONE INTERNET RIPRISTINATA!")
        
        if offline_duration:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ Durata offline: {offline_duration}")
        
        # Invia notifica di riconnessione
        if self.notification_callback:
            try:
                duration_str = f" (offline per {offline_duration})" if offline_duration else ""
                self.notification_callback(
                    "ONLINE",
                    f"✅ CONNESSIONE RIPRISTINATA!{duration_str}\n"
                    "🔄 Pronto per riavviare il trading bot\n"
                    "💡 Usa /startbot per riavviare",
                    priority="HIGH"
                )
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore notifica riconnessione: {e}")
        
        self.last_online_notification = datetime.now()
        self.offline_duration = offline_duration
    
    def _monitor_loop(self):
        """Loop principale di monitoraggio"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Avvio monitoraggio connessione (ogni {self.check_interval}s)")
        
        while self.is_monitoring:
            try:
                # Testa connessione
                is_currently_online = self.test_internet_connection()
                
                # Controlla cambi di stato
                if self.is_online and not is_currently_online:
                    # Da online a offline
                    self.is_online = False
                    self._handle_connection_lost()
                
                elif not self.is_online and is_currently_online:
                    # Da offline a online
                    # Aspetta un po' e ri-testa per essere sicuri
                    time.sleep(5)
                    if self.test_bybit_connection():  # Test specifico Bybit
                        self.is_online = True
                        self._handle_connection_restored()
                
                # Status update periodico (ogni 5 minuti quando online)
                elif self.is_online and self.last_online_notification:
                    time_since_last = datetime.now() - self.last_online_notification
                    if time_since_last.total_seconds() > 300:  # 5 minuti
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Connessione stabile")
                        self.last_online_notification = datetime.now()
                
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Errore nel monitor connessione: {e}")
            
            # Aspetta prima del prossimo controllo
            time.sleep(self.check_interval)
    
    def start_monitoring(self):
        """Avvia il monitoraggio in background"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Monitoraggio connessione avviato")
    
    def stop_monitoring(self):
        """Ferma il monitoraggio"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Monitoraggio connessione fermato")
    
    def get_status(self) -> dict:
        """Restituisce lo stato corrente della connessione"""
        return {
            'is_online': self.is_online,
            'is_monitoring': self.is_monitoring,
            'last_offline': self.last_offline_notification.isoformat() if self.last_offline_notification else None,
            'last_online': self.last_online_notification.isoformat() if self.last_online_notification else None,
            'offline_duration': str(self.offline_duration) if self.offline_duration else None,
            'bybit_accessible': self.test_bybit_connection() if self.is_online else False
        }
    
    def force_check(self) -> dict:
        """Forza un controllo immediato della connessione"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Controllo connessione forzato...")
        
        general_connection = self.test_internet_connection()
        bybit_connection = self.test_bybit_connection()
        
        result = {
            'internet_connection': general_connection,
            'bybit_connection': bybit_connection,
            'timestamp': datetime.now().isoformat(),
            'all_endpoints_status': {}
        }
        
        # Testa tutti gli endpoint singolarmente
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                result['all_endpoints_status'][endpoint] = {
                    'accessible': True,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                result['all_endpoints_status'][endpoint] = {
                    'accessible': False,
                    'error': str(e)
                }
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Risultato controllo:")
        print(f"   Internet: {'✅' if general_connection else '❌'}")
        print(f"   Bybit API: {'✅' if bybit_connection else '❌'}")
        
        return result
