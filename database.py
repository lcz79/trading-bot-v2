# database.py - v3.1 (con filtro anti-duplicati)
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

DB_FILE = "trading_signals.db"

def init_db():
    # ... (il codice di init_db rimane identico) ...
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            timeframe TEXT,
            strategy TEXT,
            score REAL,
            details TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL
        )
        """)
        for col in ["entry_price", "stop_loss", "take_profit"]:
            try: cursor.execute(f"ALTER TABLE signals ADD COLUMN {col} REAL")
            except sqlite3.OperationalError: pass
        conn.commit()
        conn.close()
        logging.info("Database inizializzato con successo.")
    except Exception as e:
        logging.error(f"Errore durante l'inizializzazione del database: {e}")


# --- NUOVA FUNZIONE DI CONTROLLO ---
def check_recent_signal(symbol: str, signal_type: str, minutes: int = 120) -> bool:
    """
    Controlla se un segnale dello stesso tipo per lo stesso simbolo
    è stato già registrato negli ultimi 'minutes' minuti.
    Restituisce True se esiste un segnale recente, False altrimenti.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        query = """
        SELECT COUNT(*) FROM signals 
        WHERE symbol = ? AND signal_type = ? AND timestamp >= ?
        """
        
        cursor.execute(query, (symbol, signal_type, time_threshold))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    except Exception as e:
        logging.error(f"Errore durante il controllo dei segnali recenti: {e}")
        return False # In caso di errore, meglio permettere il salvataggio

def save_signal(signal_data: dict):
    # ... (il codice di save_signal rimane identico) ...
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        query = """
        INSERT INTO signals (timestamp, symbol, signal_type, timeframe, strategy, score, details, entry_price, stop_loss, take_profit)
        VALUES (:timestamp, :symbol, :signal_type, :timeframe, :strategy, :score, :details, :entry_price, :stop_loss, :take_profit)
        """
        for key in ['entry_price', 'stop_loss', 'take_profit']:
            signal_data.setdefault(key, None)
        cursor.execute(query, signal_data)
        conn.commit()
        conn.close()
        logging.info(f"Segnale per {signal_data['symbol']} salvato nel database.")
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del segnale: {e}")
