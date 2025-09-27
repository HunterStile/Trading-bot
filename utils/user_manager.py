"""
Multi-Tenant User Management System
Gestisce utenti, autenticazione e configurazioni personalizzate
"""
import sqlite3
import hashlib
import jwt
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os

class UserManager:
    def __init__(self, db_path='users.db', secret_key=None):
        self.db_path = db_path
        self.jwt_secret = secret_key or os.environ.get('JWT_SECRET', 'your-secret-key-here')
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self._init_database()
    
    def _get_or_create_encryption_key(self):
        """Ottiene o crea una chiave di encryption per i dati sensibili"""
        key_file = 'encryption.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _init_database(self):
        """Inizializza il database degli utenti"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabella utenti
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Tabella configurazioni utente (dati sensibili encrypted)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_configs (
                user_id INTEGER PRIMARY KEY,
                bybit_api_key TEXT,
                bybit_secret_key TEXT,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                trading_strategy TEXT DEFAULT 'ema_crossover',
                risk_percentage REAL DEFAULT 2.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabella sessioni bot attive
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_sessions (
                user_id INTEGER PRIMARY KEY,
                session_id TEXT,
                status TEXT DEFAULT 'stopped',
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """Hash della password"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def encrypt_data(self, data):
        """Encrypt dati sensibili"""
        if data:
            return self.fernet.encrypt(data.encode()).decode()
        return None
    
    def decrypt_data(self, encrypted_data):
        """Decrypt dati sensibili"""
        if encrypted_data:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        return None
    
    def register_user(self, email, password):
        """Registra un nuovo utente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            cursor.execute('''
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
            ''', (email, password_hash))
            
            user_id = cursor.lastrowid
            
            # Crea configurazione vuota per l'utente
            cursor.execute('''
                INSERT INTO user_configs (user_id)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'user_id': user_id}
            
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Email già registrata'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def authenticate_user(self, email, password):
        """Autentica un utente e restituisce JWT token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        
        cursor.execute('''
            SELECT id, email FROM users 
            WHERE email = ? AND password_hash = ? AND is_active = TRUE
        ''', (email, password_hash))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # Genera JWT token
            payload = {
                'user_id': user[0],
                'email': user[1],
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            return {
                'success': True,
                'token': token,
                'user': {'id': user[0], 'email': user[1]}
            }
        else:
            return {'success': False, 'error': 'Credenziali non valide'}
    
    def verify_token(self, token):
        """Verifica JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return {'success': True, 'user_id': payload['user_id'], 'email': payload['email']}
        except jwt.ExpiredSignatureError:
            return {'success': False, 'error': 'Token scaduto'}
        except jwt.InvalidTokenError:
            return {'success': False, 'error': 'Token non valido'}
    
    def get_user_config(self, user_id):
        """Ottiene la configurazione dell'utente"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bybit_api_key, bybit_secret_key, telegram_bot_token, 
                   telegram_chat_id, trading_strategy, risk_percentage
            FROM user_configs WHERE user_id = ?
        ''', (user_id,))
        
        config = cursor.fetchone()
        conn.close()
        
        if config:
            return {
                'success': True,
                'config': {
                    'bybit_api_key': self.decrypt_data(config[0]) if config[0] else '',
                    'bybit_secret_key': self.decrypt_data(config[1]) if config[1] else '',
                    'telegram_bot_token': self.decrypt_data(config[2]) if config[2] else '',
                    'telegram_chat_id': config[3] or '',
                    'trading_strategy': config[4] or 'ema_crossover',
                    'risk_percentage': config[5] or 2.0
                }
            }
        else:
            return {'success': False, 'error': 'Configurazione non trovata'}
    
    def update_user_config(self, user_id, config):
        """Aggiorna la configurazione dell'utente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Encrypt sensitive data
            encrypted_api_key = self.encrypt_data(config.get('bybit_api_key'))
            encrypted_secret_key = self.encrypt_data(config.get('bybit_secret_key'))
            encrypted_bot_token = self.encrypt_data(config.get('telegram_bot_token'))
            
            cursor.execute('''
                UPDATE user_configs SET
                    bybit_api_key = ?,
                    bybit_secret_key = ?,
                    telegram_bot_token = ?,
                    telegram_chat_id = ?,
                    trading_strategy = ?,
                    risk_percentage = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                encrypted_api_key,
                encrypted_secret_key,
                encrypted_bot_token,
                config.get('telegram_chat_id'),
                config.get('trading_strategy'),
                config.get('risk_percentage'),
                user_id
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Inizializza il manager globale
user_manager = UserManager()