# data_sources.py - v1.0
# Modulo centralizzato per la connessione alle fonti dati.

from binance.client import Client
import os

# NOTA: Per sicurezza, le chiavi API non dovrebbero essere scritte direttamente nel codice.
# In un'implementazione reale, si userebbero variabili d'ambiente.
# Esempio:
# api_key = os.environ.get('BINANCE_API_KEY')
# api_secret = os.environ.get('BINANCE_API_SECRET')
#
# Per semplicità, in questa fase di test usiamo valori vuoti,
# dato che per scaricare i dati storici pubblici non servono chiavi.

API_KEY = ""
API_SECRET = ""

# Inizializza il client di Binance una sola volta
try:
    binance_client = Client(API_KEY, API_SECRET)
    # Testiamo la connessione
    binance_client.ping()
    print("Connessione a Binance stabilita con successo.")
except Exception as e:
    print(f"Errore durante la connessione a Binance: {e}")
    binance_client = None
