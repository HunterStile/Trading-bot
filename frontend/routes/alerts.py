from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import json
import threading
import time
import sys
import os

# Aggiungi il path per trading_functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trading_functions import vedi_prezzo_moneta

alerts_bp = Blueprint('alerts', __name__)

# Lista globale per memorizzare gli alert attivi
active_alerts = []
alert_monitor_thread = None
monitor_running = False
app_instance = None  # Reference all'app per il context

def set_app_instance(app):
    """Imposta l'istanza dell'app per il monitor degli alert"""
    global app_instance
    app_instance = app

@alerts_bp.route('/')
def alerts_page():
    """Pagina principale per la gestione degli alert"""
    return render_template('alerts.html')

@alerts_bp.route('/api/list', methods=['GET'])
def get_alerts():
    """Ottieni la lista degli alert attivi"""
    return jsonify({
        'success': True,
        'alerts': active_alerts,
        'count': len(active_alerts)
    })

@alerts_bp.route('/api/add', methods=['POST'])
def add_alert():
    """Aggiungi un nuovo alert"""
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['symbol', 'target_price', 'direction', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo {field} mancante'})
        
        # Controlla che il prezzo target sia valido
        try:
            target_price = float(data['target_price'])
        except ValueError:
            return jsonify({'success': False, 'error': 'Prezzo target non valido'})
        
        # Ottieni prezzo corrente per validazione
        current_price = vedi_prezzo_moneta('linear', data['symbol'])
        if current_price is None:
            return jsonify({'success': False, 'error': 'Simbolo non valido o errore API'})
        
        # Validazione direzione
        direction = data['direction'].upper()
        if direction not in ['ABOVE', 'BELOW']:
            return jsonify({'success': False, 'error': 'Direzione deve essere ABOVE o BELOW'})
        
        # Controlla logica dell'alert
        if direction == 'ABOVE' and target_price <= current_price:
            return jsonify({'success': False, 'error': 'Il prezzo target per ABOVE deve essere superiore al prezzo corrente'})
        
        if direction == 'BELOW' and target_price >= current_price:
            return jsonify({'success': False, 'error': 'Il prezzo target per BELOW deve essere inferiore al prezzo corrente'})
        
        # Crea nuovo alert
        new_alert = {
            'id': f"{data['symbol']}_{direction}_{target_price}_{int(time.time())}",
            'symbol': data['symbol'].upper(),
            'target_price': target_price,
            'current_price': current_price,
            'direction': direction,
            'message': data['message'],
            'created_at': datetime.now().isoformat(),
            'status': 'ACTIVE',
            'triggered_at': None
        }
        
        active_alerts.append(new_alert)
        
        # Avvia il monitor se non è già attivo
        start_alert_monitor()
        
        # Notifica Telegram di creazione alert
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            direction_emoji = "📈" if direction == "ABOVE" else "📉"
            message = f"""
🔔 <b>Nuovo Alert Creato</b>

{direction_emoji} <b>{data['symbol']}</b>
💰 Prezzo corrente: <code>${current_price:.4f}</code>
🎯 Target: <code>${target_price:.4f}</code>
📍 Direzione: <b>{direction}</b>
💬 Messaggio: <i>{data['message']}</i>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_notifier.send_message_sync(message)
        
        return jsonify({
            'success': True,
            'message': 'Alert aggiunto con successo',
            'alert': new_alert
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@alerts_bp.route('/api/remove/<alert_id>', methods=['DELETE'])
def remove_alert(alert_id):
    """Rimuovi un alert"""
    global active_alerts
    
    # Trova e rimuovi l'alert
    alert_to_remove = None
    for i, alert in enumerate(active_alerts):
        if alert['id'] == alert_id:
            alert_to_remove = active_alerts.pop(i)
            break
    
    if alert_to_remove:
        # Notifica Telegram di rimozione alert
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            direction_emoji = "📈" if alert_to_remove['direction'] == "ABOVE" else "📉"
            message = f"""
🗑️ <b>Alert Rimosso</b>

{direction_emoji} <b>{alert_to_remove['symbol']}</b>
🎯 Target: <code>${alert_to_remove['target_price']:.4f}</code>
📍 Direzione: <b>{alert_to_remove['direction']}</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_notifier.send_message_sync(message)
        
        return jsonify({
            'success': True,
            'message': 'Alert rimosso con successo'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Alert non trovato'
        })

@alerts_bp.route('/api/clear', methods=['POST'])
def clear_all_alerts():
    """Rimuovi tutti gli alert"""
    global active_alerts
    
    count = len(active_alerts)
    active_alerts.clear()
    
    # Notifica Telegram
    telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
    if telegram_notifier:
        message = f"""
🧹 <b>Tutti gli Alert Cancellati</b>

📊 Alert rimossi: <b>{count}</b>
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        telegram_notifier.send_message_sync(message)
    
    return jsonify({
        'success': True,
        'message': f'{count} alert rimossi'
    })

@alerts_bp.route('/api/symbols', methods=['GET'])
def get_symbols():
    """Ottieni lista simboli disponibili"""
    # Lista simboli comuni per trading
    default_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LUNAUSDT',
        'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'FILUSDT', 'ETCUSDT',
        'XLMUSDT', 'VETUSDT', 'ICPUSDT', 'THETAUSDT', 'TRXUSDT'
    ]
    
    # Carica simboli custom se esistono
    custom_symbols = []
    try:
        import os
        custom_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_symbols.json')
        if os.path.exists(custom_file):
            with open(custom_file, 'r') as f:
                custom_data = json.load(f)
                custom_symbols = [item['symbol'] for item in custom_data if 'symbol' in item]
                print(f"🔧 Caricati {len(custom_symbols)} simboli custom: {custom_symbols}")
    except Exception as e:
        print(f"⚠️ Errore caricamento simboli custom: {e}")
    
    # Combina simboli default e custom (evita duplicati)
    all_symbols = list(set(default_symbols + custom_symbols))
    all_symbols.sort()  # Ordina alfabeticamente
    
    return jsonify({
        'success': True,
        'symbols': all_symbols,
        'default_count': len(default_symbols),
        'custom_count': len(custom_symbols),
        'total_count': len(all_symbols)
    })

def start_alert_monitor():
    """Avvia il monitor degli alert"""
    global alert_monitor_thread, monitor_running
    
    if monitor_running:
        return
    
    monitor_running = True
    alert_monitor_thread = threading.Thread(target=alert_monitor_loop, daemon=True)
    alert_monitor_thread.start()
    print("🔔 Monitor alert avviato")

def alert_monitor_loop():
    """Loop principale del monitor degli alert"""
    global monitor_running, active_alerts, app_instance
    
    while monitor_running:
        try:
            if not active_alerts:
                time.sleep(5)
                continue
            
            # Controlla ogni alert attivo
            for alert in active_alerts[:]:  # Copia della lista per iterazione sicura
                if alert['status'] != 'ACTIVE':
                    continue
                
                # Ottieni prezzo corrente
                current_price = vedi_prezzo_moneta('linear', alert['symbol'])
                if current_price is None:
                    continue
                
                # Aggiorna prezzo corrente nell'alert
                alert['current_price'] = current_price
                
                # Controlla se l'alert è stato triggerato
                triggered = False
                
                if alert['direction'] == 'ABOVE' and current_price >= alert['target_price']:
                    triggered = True
                elif alert['direction'] == 'BELOW' and current_price <= alert['target_price']:
                    triggered = True
                
                if triggered:
                    # Marca alert come triggerato
                    alert['status'] = 'TRIGGERED'
                    alert['triggered_at'] = datetime.now().isoformat()
                    
                    # Invia notifica Telegram con context
                    if app_instance:
                        with app_instance.app_context():
                            send_alert_notification(alert)
                    else:
                        # Fallback senza context
                        send_alert_notification_fallback(alert)
                    
                    # Rimuovi alert dalla lista attiva (opzionale)
                    active_alerts.remove(alert)
            
            # Pausa tra controlli
            time.sleep(10)  # Controlla ogni 10 secondi
            
        except Exception as e:
            print(f"❌ Errore nel monitor alert: {e}")
            time.sleep(30)  # Pausa più lunga in caso di errore

def send_alert_notification_fallback(alert):
    """Fallback per invio notifica senza context"""
    try:
        direction_emoji = "🚀" if alert['direction'] == "ABOVE" else "📉"
        trend_text = "è salito sopra" if alert['direction'] == "ABOVE" else "è sceso sotto"
        
        print(f"""
🚨 ALERT TRIGGERATO! {direction_emoji}
💰 {alert['symbol']} {trend_text} il target!
🎯 Target: ${alert['target_price']:.4f}
📊 Attuale: ${alert['current_price']:.4f}
💬 {alert['message']}
⏰ {datetime.now().strftime('%H:%M:%S')}
""")
        
    except Exception as e:
        print(f"❌ Errore notifica fallback: {e}")

def send_alert_notification(alert):
    """Invia notifica Telegram per alert triggerato"""
    try:
        # Ottieni notificatore Telegram
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        
        if telegram_notifier:
            direction_emoji = "🚀" if alert['direction'] == "ABOVE" else "📉"
            trend_text = "è salito sopra" if alert['direction'] == "ABOVE" else "è sceso sotto"
            
            message = f"""
🚨 <b>ALERT TRIGGERATO!</b> {direction_emoji}

💰 <b>{alert['symbol']}</b> {trend_text} il target!

🎯 Prezzo target: <code>${alert['target_price']:.4f}</code>
📊 Prezzo attuale: <code>${alert['current_price']:.4f}</code>
📈 Variazione: <code>{((alert['current_price'] - alert['target_price']) / alert['target_price'] * 100):+.2f}%</code>

💬 <i>{alert['message']}</i>

⏰ {datetime.now().strftime('%H:%M:%S')}
📊 Dashboard: http://localhost:5000/alerts
"""
            telegram_notifier.send_message_sync(message)
            print(f"🔔 Alert triggerato per {alert['symbol']}: {alert['current_price']}")
        
    except Exception as e:
        print(f"❌ Errore invio notifica alert: {e}")

@alerts_bp.route('/api/test-telegram', methods=['POST'])
def test_telegram_notification():
    """Testa invio notifica Telegram"""
    try:
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        
        if not telegram_notifier:
            return jsonify({
                'success': False,
                'error': 'Sistema notifiche Telegram non configurato'
            })
        
        # Messaggio di test
        test_message = f"""
🧪 <b>Test Alert System</b>

📊 Sistema di alert funzionante!
🔔 Le notifiche Telegram sono attive
⏰ {datetime.now().strftime('%H:%M:%S')}

💡 Questo è un messaggio di test dal sistema di alert prezzi.
"""
        
        success = telegram_notifier.send_message_sync(test_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notifica di test inviata con successo!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nell\'invio della notifica'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore: {str(e)}'
        })

@alerts_bp.route('/api/status', methods=['GET'])
def get_monitor_status():
    """Ottieni stato del monitor"""
    return jsonify({
        'success': True,
        'monitor_running': monitor_running,
        'active_alerts_count': len([a for a in active_alerts if a['status'] == 'ACTIVE']),
        'total_alerts': len(active_alerts)
    })

@alerts_bp.route('/api/custom-symbols', methods=['GET'])
def get_custom_symbols():
    """Ottieni solo i simboli custom"""
    try:
        import os
        custom_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_symbols.json')
        
        if not os.path.exists(custom_file):
            return jsonify({
                'success': True,
                'symbols': [],
                'message': 'Nessun simbolo custom configurato'
            })
        
        with open(custom_file, 'r') as f:
            custom_data = json.load(f)
        
        return jsonify({
            'success': True,
            'symbols': custom_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore caricamento simboli custom: {str(e)}'
        })

@alerts_bp.route('/api/custom-symbols', methods=['POST'])
def add_custom_symbol():
    """Aggiungi un nuovo simbolo custom"""
    try:
        data = request.get_json()
        
        if not data or 'symbol' not in data:
            return jsonify({
                'success': False,
                'error': 'Simbolo mancante'
            })
        
        symbol = data['symbol'].upper().strip()
        name = data.get('name', symbol)
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': 'Simbolo non può essere vuoto'
            })
        
        # Verifica che il simbolo sia valido testando il prezzo
        try:
            test_price = vedi_prezzo_moneta('linear', symbol)
            if test_price is None:
                return jsonify({
                    'success': False,
                    'error': f'Simbolo {symbol} non valido o non disponibile su Bybit'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Errore validazione simbolo: {str(e)}'
            })
        
        # Carica simboli esistenti
        import os
        custom_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_symbols.json')
        
        custom_symbols = []
        if os.path.exists(custom_file):
            with open(custom_file, 'r') as f:
                custom_symbols = json.load(f)
        
        # Controlla se esiste già
        for existing in custom_symbols:
            if existing.get('symbol') == symbol:
                return jsonify({
                    'success': False,
                    'error': f'Simbolo {symbol} già presente'
                })
        
        # Aggiungi nuovo simbolo
        new_symbol = {
            'symbol': symbol,
            'name': name,
            'added_at': datetime.now().isoformat()
        }
        
        custom_symbols.append(new_symbol)
        
        # Salva il file
        with open(custom_file, 'w') as f:
            json.dump(custom_symbols, f, indent=2)
        
        # Notifica Telegram
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            message = f"""
➕ <b>Simbolo Custom Aggiunto</b>

💰 <b>{symbol}</b>
📝 Nome: <i>{name}</i>
💲 Prezzo attuale: <code>${test_price:.6f}</code>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_notifier.send_message_sync(message)
        
        return jsonify({
            'success': True,
            'message': f'Simbolo {symbol} aggiunto con successo',
            'symbol': new_symbol,
            'price': test_price
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore: {str(e)}'
        })

@alerts_bp.route('/api/custom-symbols/<symbol>', methods=['DELETE'])
def remove_custom_symbol(symbol):
    """Rimuovi un simbolo custom"""
    try:
        symbol = symbol.upper()
        
        import os
        custom_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_symbols.json')
        
        if not os.path.exists(custom_file):
            return jsonify({
                'success': False,
                'error': 'Nessun simbolo custom configurato'
            })
        
        with open(custom_file, 'r') as f:
            custom_symbols = json.load(f)
        
        # Trova e rimuovi il simbolo
        original_count = len(custom_symbols)
        custom_symbols = [s for s in custom_symbols if s.get('symbol') != symbol]
        
        if len(custom_symbols) == original_count:
            return jsonify({
                'success': False,
                'error': f'Simbolo {symbol} non trovato'
            })
        
        # Salva il file aggiornato
        with open(custom_file, 'w') as f:
            json.dump(custom_symbols, f, indent=2)
        
        # Notifica Telegram
        telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
        if telegram_notifier:
            message = f"""
➖ <b>Simbolo Custom Rimosso</b>

💰 <b>{symbol}</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_notifier.send_message_sync(message)
        
        return jsonify({
            'success': True,
            'message': f'Simbolo {symbol} rimosso con successo'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore: {str(e)}'
        })

# Funzione per inizializzare il sistema di alert
def init_alerts_system(app):
    """Inizializza il sistema di alert con l'app instance"""
    global app_instance
    app_instance = app
    print("🔔 Sistema Alert inizializzato")
