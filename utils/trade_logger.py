# utils/trade_logger.py
import csv
import os
from datetime import datetime
from threading import Lock

# Definiamo il nome del file di log e le colonne che conterrà
TRADE_LOG_FILE = 'trade_log.csv'
FIELDNAMES = [
    'close_timestamp', 'symbol', 'direction', 'quantity', 
    'entry_price', 'exit_price', 'pnl', 'exit_reason', 'entry_timestamp'
]

# Usiamo un "Lock" per evitare che più parti del programma scrivano sul file contemporaneamente,
# causando errori. È una misura di sicurezza.
_lock = Lock()

def log_trade(trade_data: dict):
    """
    Scrive i dettagli di una singola operazione chiusa nel file CSV.

    Args:
        trade_data (dict): Un dizionario contenente i dati del trade,
                           corrispondenti a FIELDNAMES.
    """
    with _lock:
        try:
            # Controlliamo se il file esiste già e se è vuoto per scrivere l'intestazione
            file_exists = os.path.exists(TRADE_LOG_FILE)
            is_empty = os.path.getsize(TRADE_LOG_FILE) == 0 if file_exists else True

            with open(TRADE_LOG_FILE, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

                if is_empty:
                    writer.writeheader()
                
                # Arrotondiamo i valori numerici per una migliore leggibilità
                trade_data['entry_price'] = round(trade_data.get('entry_price', 0), 4)
                trade_data['exit_price'] = round(trade_data.get('exit_price', 0), 4)
                trade_data['pnl'] = round(trade_data.get('pnl', 0), 4)
                
                writer.writerow(trade_data)

        except Exception as e:
            # Se c'è un errore nella scrittura del log, lo stampiamo ma non blocchiamo il bot
            print(f"ERRORE CRITICO: Impossibile scrivere nel trade log: {e}")
