# database.py - v3.2 (Aggiunge supporto per dettagli di management)
import sqlite3
import logging
from datetime import datetime, timedelta, timezone

DB_NAME = 'trading_signals.db'

def init_db():
    """Crea la tabella dei segnali se non esiste, aggiungendo la colonna mgmt_details."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crea la tabella se non esiste
    cursor.execute('''
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
            take_profit REAL,
            mgmt_details TEXT
        )
    ''')
    
    # Aggiungiamo la colonna se non esiste, per non rompere database esistenti
    try:
        cursor.execute('ALTER TABLE signals ADD COLUMN mgmt_details TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        # La colonna esiste già, va bene così
        pass

    conn.close()

def save_signal(signal_data):
    """Salva un singolo segnale nel database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO signals (timestamp, symbol, signal_type, timeframe, strategy, score, details, entry_price, stop_loss, take_profit, mgmt_details)
        VALUES (:timestamp, :symbol, :signal_type, :timeframe, :strategy, :score, :details, :entry_price, :stop_loss, :take_profit, :mgmt_details)
    ''', signal_data)
    conn.commit()
    conn.close()
    logging.info(f"Salvataggio segnale per {signal_data['symbol']} nel database.")

def get_all_signals():
    """Recupera tutti i segnali dal database per la dashboard."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM signals ORDER BY timestamp DESC')
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return signals

def check_recent_signal(symbol, signal_type):
    """Controlla se un segnale identico è già stato salvato nelle ultime 6 ore."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    time_window = datetime.now(timezone.utc) - timedelta(hours=6)
    cursor.execute('''
        SELECT 1 FROM signals 
        WHERE symbol = ? AND signal_type = ? AND timestamp > ?
        LIMIT 1
    ''', (symbol, signal_type, time_window))
    exists = cursor.fetchone()
    conn.close()
    return exists is not None

def delete_all_signals():
    """Cancella tutti i segnali dal database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM signals')
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="signals"')
        conn.commit()
        conn.close()
        logging.info("Tutti i segnali sono stati cancellati dal database.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Errore durante la cancellazione dei segnali: {e}")
        return False

# Inizializza il DB all'importazione del modulo
init_db()
