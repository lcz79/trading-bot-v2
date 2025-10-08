# db_inspector.py
# Uno script di diagnostica per leggere e stampare il contenuto
# della tabella 'trade_intents' dal database.

import pandas as pd
import database
import os

print("--- AVVIO ISPEZIONE DATABASE ---")

# Assicurati che il database esista
db_path = 'phoenix_trading.db'
if not os.path.exists(db_path):
    print(f"ERRORE CRITICO: Il file di database '{db_path}' non è stato trovato nella cartella corrente.")
    print("--- FINE ISPEZIONE ---")
    exit()

print(f"Trovato database '{db_path}'. Connessione in corso...")

try:
    # Inizializza la connessione
    database.init_db()

    with database.session_scope() as session:
        # Leggi l'intera tabella 'trade_intents' in un DataFrame pandas
        query = session.query(database.TradeIntent).statement
        df = pd.read_sql(query, database.engine, parse_dates=['timestamp'])

    print("\n--- CONTENUTO TABELLA 'trade_intents' ---")
    if df.empty:
        print("La tabella è VUOTA. Nessun segnale presente.")
    else:
        # Stampa il dataframe completo
        print(df.to_string())
    
    print("\n--- FINE ISPEZIONE ---")

except Exception as e:
    print(f"\nERRORE durante la connessione o la lettura dal database: {e}")
    print("--- FINE ISPEZIONE ---")