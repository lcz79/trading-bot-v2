import traceback
import pandas as pd

# Importiamo le funzioni direttamente, questo ora funziona grazie a __init__.py
from api_clients.bybit_client import get_klines as get_bybit_klines
from api_clients.binance_client import get_klines as get_binance_klines
from api_clients.yahoo_client import get_klines as get_yahoo_klines

def get_data(symbol: str, timeframe: str, limit: int, source: str):
    """
    Recupera i dati di mercato dalla fonte specificata.
    Usa un approccio pulito per gestire i DataFrame.
    """
    print(f"[DataClient] Richiesta dati per {symbol} ({timeframe}) da {source}...")

    CLIENT_MAP = {
        'Binance': get_binance_klines,
        'Yahoo': get_yahoo_klines,
        'Bybit': get_bybit_klines
    }
    
    primary_func = CLIENT_MAP.get(source)
    
    if not primary_func:
        print(f"[DataClient] ERRORE: Nessuna funzione client trovata per la fonte '{source}'")
        return None

    try:
        df = primary_func(symbol, interval=timeframe, limit=limit)
        
        # --- LA CORREZIONE CHIAVE È QUI ---
        # Controlliamo se il DataFrame è None (errore) o è vuoto (no dati)
        if df is None or df.empty:
            print(f"[DataClient] -> Info: Nessun dato valido da {source}.")
            return None # Restituiamo None per segnalare il fallimento
        
        print(f"[DataClient] -> Successo: Dati ottenuti da {source} ({len(df)} candele).")
        return df
            
    except Exception as e:
        print(f"[DataClient] ERRORE CRITICO durante chiamata a {source}: {e}")
        traceback.print_exc()
        return None
