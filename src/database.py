import sqlite3
import json
from datetime import datetime, timedelta
from config import Config

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('albion_bot.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                albion_nickname TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Monitoring sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                location TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                known_players TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Resource timers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_timers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                location TEXT,
                resource_type TEXT,
                resource_tier INTEGER,
                harvested_at TIMESTAMP,
                expected_respawn TIMESTAMP,
                notified BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Player cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_cache (
                player_name TEXT PRIMARY KEY,
                kill_fame INTEGER DEFAULT 0,
                pvp_kills INTEGER DEFAULT 0,
                last_checked TIMESTAMP,
                guild_name TEXT,
                alliance_name TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, albion_nickname=None):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO users (user_id, albion_nickname) VALUES (?, ?)',
            (user_id, albion_nickname)
        )
        self.conn.commit()
    
    def get_user_albion_nickname(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT albion_nickname FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def start_monitoring_session(self, user_id, location):
        cursor = self.conn.cursor()
        # Deactivate any existing sessions
        cursor.execute(
            'UPDATE monitoring_sessions SET is_active = FALSE WHERE user_id = ?',
            (user_id,)
        )
        # Start new session
        cursor.execute(
            'INSERT INTO monitoring_sessions (user_id, location) VALUES (?, ?)',
            (user_id, location)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def stop_monitoring_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE monitoring_sessions SET is_active = FALSE WHERE user_id = ? AND is_active = TRUE',
            (user_id,)
        )
        self.conn.commit()
    
    def get_active_monitoring_sessions(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ms.id, ms.user_id, ms.location, ms.known_players, u.albion_nickname
            FROM monitoring_sessions ms
            JOIN users u ON ms.user_id = u.user_id
            WHERE ms.is_active = TRUE
        ''')
        return cursor.fetchall()
    
    def update_known_players(self, session_id, known_players):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE monitoring_sessions SET known_players = ? WHERE id = ?',
            (json.dumps(list(known_players)), session_id)
        )
        self.conn.commit()
    
    def get_known_players(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT known_players FROM monitoring_sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        return set(json.loads(result[0])) if result and result[0] else set()
    
    def add_resource_timer(self, user_id, location, resource_type, resource_tier, harvested_at, expected_respawn):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO resource_timers 
            (user_id, location, resource_type, resource_tier, harvested_at, expected_respawn)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, location, resource_type, resource_tier, harvested_at, expected_respawn))
        self.conn.commit()
    
    def get_pending_resource_notifications(self):
        cursor = self.conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT rt.*, u.user_id
            FROM resource_timers rt
            JOIN users u ON rt.user_id = u.user_id
            WHERE rt.expected_respawn <= ? AND rt.notified = FALSE
        ''', (now,))
        return cursor.fetchall()
    
    def mark_resource_notified(self, timer_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE resource_timers SET notified = TRUE WHERE id = ?',
            (timer_id,)
        )
        self.conn.commit()
    
    def cache_player_info(self, player_name, kill_fame, pvp_kills, guild_name, alliance_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO player_cache 
            (player_name, kill_fame, pvp_kills, last_checked, guild_name, alliance_name)
            VALUES (?, ?, ?, datetime('now'), ?, ?)
        ''', (player_name, kill_fame, pvp_kills, guild_name, alliance_name))
        self.conn.commit()
    
    def get_cached_player_info(self, player_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM player_cache WHERE player_name = ?', (player_name,))
        return cursor.fetchone()

# Global database instance
db = Database()
