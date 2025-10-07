import traceback
import pandas as pd

# Importa i moduli client specifici
from . import bybit_client
from . import yahoo_client
# from . import binance_client # Se lo userai in futuro

def get_data(symbol: str, timeframe: str, limit: int, source: str):
    """
    Recupera i dati di mercato dalla fonte specificata, agendo come un adattatore
    che chiama ogni client con i parametri corretti.
    
    source: 'Bybit-linear' | 'Yahoo'
    """
    print(f"[DataClient] Richiesta dati per {symbol} ({timeframe}) da {source}...")
    
    df = None
    try:
        # --- LOGICA DI ADATTAMENTO ---
        if source == "Bybit-linear":
            # Chiama bybit_client con i suoi parametri: symbol, interval, limit, category
            df = bybit_client.get_klines(
                symbol=symbol, 
                interval=timeframe,  # Passa '60', '240' direttamente
                limit=limit, 
                category="linear"
            )
        elif source == "Yahoo":
            # Chiama yahoo_client con i suoi parametri: symbol, interval, limit
            df = yahoo_client.get_klines(
                symbol=symbol, 
                interval=timeframe, # Passa '1h', '1d' direttamente
                limit=limit
            )
        else:
            print(f"[DataClient] ERRORE: La fonte '{source}' non è supportata.")
            return pd.DataFrame()

        # --- GESTIONE RISPOSTA ---
        if df is None or df.empty:
            print(f"[DataClient] -> Info: Nessun dato valido restituito da {source} per {symbol}.")
            return pd.DataFrame()

        # Normalizzazione delle colonne per coerenza
        df.columns = [col.lower() for col in df.columns]
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in required_cols):
             print(f"[DataClient] -> ATTENZIONE: Colonne mancanti da {source}. Presenti: {df.columns.tolist()}")
        
        print(f"[DataClient] -> Successo: Dati ottenuti da {source} ({len(df)} candele).")
        return df[required_cols].copy()

    except Exception as e:
        print(f"🔥 [DataClient] ERRORE CRITICO durante la gestione della chiamata a {source} per {symbol}: {e}")
        traceback.print_exc()
        return pd.DataFrame()
