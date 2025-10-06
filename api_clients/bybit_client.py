import requests
import pandas as pd
from datetime import datetime
import time
import hmac
import hashlib
import os
import json

# --- CONFIGURAZIONE AUTENTICAZIONE ---
# Assicurati che queste variabili siano nel tuo file .env
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
BASE_URL = "https://api.bybit.com"

if not API_KEY or not API_SECRET:
    print("ATTENZIONE: BYBIT_API_KEY o BYBIT_API_SECRET non trovate. Le funzioni private non andranno.")

def _get_signature(timestamp, api_key, recv_window, params_str):
    """Genera la firma HMAC-SHA256 richiesta da Bybit V5."""
    payload = f"{timestamp}{api_key}{recv_window}{params_str}"
    signature = hmac.new(
        bytes(API_SECRET, "utf-8"),
        msg=bytes(payload, "utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    return signature

def _send_private_request(endpoint, params=None):
    """Funzione helper per inviare richieste autenticate (private) a Bybit."""
    if not API_KEY or not API_SECRET:
        print(f"ERRORE: Impossibile eseguire la richiesta a {endpoint}. Chiavi API mancanti.")
        return None

    timestamp = str(int(time.time() * 1000))
    recv_window = "20000"  # 20 secondi
    
    params_str = ""
    if params:
        # Ordina i parametri alfabeticamente e crea la stringa per la firma
        params_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])

    signature = _get_signature(timestamp, API_KEY, recv_window, params_str)

    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-SIGN': signature,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    try:
        session = requests.Session()
        full_url = f"{BASE_URL}{endpoint}"
        if params_str:
            full_url += f"?{params_str}"
            
        response = session.get(full_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            print(f"ERRORE API Bybit ({endpoint}): {data.get('retMsg')}")
            return None
        
        return data.get('result')

    except Exception as e:
        print(f"ERRORE CRITICO in _send_private_request ({endpoint}): {e}")
        return None

def get_wallet_balance(account_type="UNIFIED"):
    """
    Recupera il saldo del portafoglio per un dato tipo di conto.
    Per i futures, il tipo è 'UNIFIED' o 'CONTRACT'.
    """
    print("-> BybitClient: Recupero saldo portafoglio...")
    endpoint = "/v5/account/wallet-balance"
    params = {"accountType": account_type}
    
    result = _send_private_request(endpoint, params)
    
    if result and 'list' in result and len(result['list']) > 0:
        # Restituisce il primo account della lista, che di solito è quello principale
        return result['list'][0]
    
    return None

def get_open_positions(category="linear"):
    """
    Recupera le posizioni aperte per la categoria specificata (es. 'linear' per USDT perp).
    """
    print("-> BybitClient: Recupero posizioni aperte...")
    endpoint = "/v5/position/list"
    params = {"category": category}
    
    result = _send_private_request(endpoint, params)
    
    if result and 'list' in result:
        return result['list']
        
    return [] # Restituisce una lista vuota se non ci sono posizioni o in caso di errore

def get_klines(symbol: str, interval: str, limit: int = 200):
    """Recupera dati k-line da Bybit e li restituisce come DataFrame."""
    print(f"-> BybitClient: Recupero K-lines per {symbol} ({interval})...")
    
    interval_map = {"1h": "60", "4h": "240", "1d": "D"} # Bybit usa stringhe per i minuti
    bybit_interval = interval_map.get(interval.lower())
    if not bybit_interval:
        print(f"ERRORE: Intervallo {interval} non supportato da Bybit client.")
        return None

    try:
        session = requests.Session()
        response = session.get(
            f"{BASE_URL}/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": limit
            }
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            print(f"ERRORE API Bybit: {data.get('retMsg')}")
            return None

        kline_data = data.get('result', {}).get('list', [])
        if not kline_data:
            return pd.DataFrame()

        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
        df = df.set_index('timestamp')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        return df.iloc[::-1]

    except Exception as e:
        print(f"ERRORE CRITICO in bybit_client.get_klines: {e}")
        return None
