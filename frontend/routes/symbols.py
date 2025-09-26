from flask import Blueprint, request, jsonify
import json
import os
import sys
from datetime import datetime

# Aggiungi il path per trading_functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.trading_functions import vedi_prezzo_moneta

symbols_bp = Blueprint('symbols', __name__)

# Coppie di trading default
DEFAULT_SYMBOLS = [
    {'symbol': 'AVAXUSDT', 'name': 'AVAX/USDT'},
    {'symbol': 'BTCUSDT', 'name': 'BTC/USDT'},
    {'symbol': 'ETHUSDT', 'name': 'ETH/USDT'},
    {'symbol': 'SOLUSDT', 'name': 'SOL/USDT'},
    {'symbol': 'ADAUSDT', 'name': 'ADA/USDT'},
    {'symbol': 'DOTUSDT', 'name': 'DOT/USDT'},
    {'symbol': 'XRPUSDT', 'name': 'XRP/USDT'},
    {'symbol': 'BNBUSDT', 'name': 'BNB/USDT'},
    {'symbol': 'DOGEUSDT', 'name': 'DOGE/USDT'},
    {'symbol': 'LINKUSDT', 'name': 'LINK/USDT'}
]

# File per salvare coppie personalizzate - usa il path del progetto root
def get_custom_symbols_file():
    """Ottieni il path del file custom symbols nel root del progetto"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom_symbols.json')

def load_custom_symbols():
    """Carica le coppie personalizzate dal file"""
    try:
        custom_file = get_custom_symbols_file()
        if os.path.exists(custom_file):
            with open(custom_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento coppie personalizzate: {e}")
    return []

def save_custom_symbols(symbols):
    """Salva le coppie personalizzate nel file"""
    try:
        custom_file = get_custom_symbols_file()
        with open(custom_file, 'w') as f:
            json.dump(symbols, f, indent=2)
        return True
    except Exception as e:
        print(f"Errore nel salvataggio coppie personalizzate: {e}")
        return False

def get_all_symbols():
    """Restituisce tutte le coppie (default + personalizzate)"""
    custom_symbols = load_custom_symbols()
    return DEFAULT_SYMBOLS + custom_symbols

@symbols_bp.route('')
def get_symbols():
    """Restituisce tutti i simboli disponibili (default + custom)"""
    try:
        # Simboli default
        all_symbols = DEFAULT_SYMBOLS.copy()
        
        # Aggiungi simboli custom
        custom_symbols = load_custom_symbols()
        
        # Converti i simboli custom nel formato corretto se necessario
        for custom in custom_symbols:
            if isinstance(custom, dict):
                # Se è già nel formato corretto
                if 'symbol' in custom:
                    symbol_obj = {
                        'symbol': custom['symbol'],
                        'name': custom.get('name', custom['symbol'].replace('USDT', '/USDT'))
                    }
                    # Aggiungi solo se non esiste già
                    if not any(s['symbol'] == symbol_obj['symbol'] for s in all_symbols):
                        all_symbols.append(symbol_obj)
            else:
                # Se è solo una stringa
                symbol_obj = {
                    'symbol': custom,
                    'name': custom.replace('USDT', '/USDT')
                }
                if not any(s['symbol'] == symbol_obj['symbol'] for s in all_symbols):
                    all_symbols.append(symbol_obj)
        
        # Ordina alfabeticamente
        all_symbols.sort(key=lambda x: x['symbol'])
        
        return jsonify({
            'success': True,
            'symbols': all_symbols,
            'total_count': len(all_symbols),
            'default_count': len(DEFAULT_SYMBOLS),
            'custom_count': len(custom_symbols)
        })
        
    except Exception as e:
        print(f"Errore nel caricamento simboli: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbols': DEFAULT_SYMBOLS  # Fallback ai simboli default
        })

@symbols_bp.route('/verify/<symbol>')
def verify_symbol(symbol):
    """Verifica se un simbolo esiste su Bybit"""
    try:
        # Prova a ottenere il prezzo per verificare l'esistenza
        price_data = vedi_prezzo_moneta('linear', symbol.upper())
        if price_data and price_data > 0:
            return jsonify({
                'success': True,
                'exists': True,
                'price': price_data,
                'symbol': symbol.upper()
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'error': 'Simbolo non trovato'
            })
    except Exception as e:
        return jsonify({
            'success': True,
            'exists': False,
            'error': str(e)
        })

@symbols_bp.route('/add', methods=['POST'])
def add_custom_symbol():
    """Aggiunge un nuovo simbolo personalizzato"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        name = data.get('name', '').strip()
        
        if not symbol or not name:
            return jsonify({
                'success': False,
                'error': 'Simbolo e nome sono richiesti'
            })
        
        # Verifica che il simbolo non esista già
        all_symbols = get_all_symbols()
        existing_symbols = [s['symbol'] for s in all_symbols]
        
        if symbol in existing_symbols:
            return jsonify({
                'success': False,
                'error': 'Simbolo già esistente'
            })
        
        # Verifica esistenza su Bybit
        try:
            price = vedi_prezzo_moneta('linear', symbol)
            if not price or price <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Simbolo non trovato su Bybit'
                })
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Simbolo non valido o non esistente su Bybit'
            })
        
        # Aggiunge il simbolo alle coppie personalizzate
        custom_symbols = load_custom_symbols()
        new_symbol = {'symbol': symbol, 'name': name}
        custom_symbols.append(new_symbol)
        
        if save_custom_symbols(custom_symbols):
            return jsonify({
                'success': True,
                'symbol': new_symbol,
                'message': f'Simbolo {symbol} aggiunto con successo'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nel salvataggio del simbolo'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@symbols_bp.route('/remove/<symbol>', methods=['DELETE'])
def remove_custom_symbol(symbol):
    """Rimuove un simbolo personalizzato"""
    try:
        symbol = symbol.upper()
        
        # Verifica che non sia un simbolo default
        default_symbols = [s['symbol'] for s in DEFAULT_SYMBOLS]
        if symbol in default_symbols:
            return jsonify({
                'success': False,
                'error': 'Non è possibile rimuovere simboli di default'
            })
        
        custom_symbols = load_custom_symbols()
        custom_symbols = [s for s in custom_symbols if s['symbol'] != symbol]
        
        if save_custom_symbols(custom_symbols):
            return jsonify({
                'success': True,
                'message': f'Simbolo {symbol} rimosso con successo'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nella rimozione del simbolo'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })