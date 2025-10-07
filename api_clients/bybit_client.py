import requests
import pandas as pd
import os
import time
import hmac
import hashlib

# --- CONFIGURAZIONE ---
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
BASE_URL = "https://api.bybit.com"

# Funzioni private per l'autenticazione (rimangono invariate)
def _get_signature(timestamp, api_key, recv_window, params_str):
    payload = f"{timestamp}{api_key}{recv_window}{params_str}"
    return hmac.new(bytes(API_SECRET, "utf-8"), msg=bytes(payload, "utf-8"), digestmod=hashlib.sha256).hexdigest()

def _send_private_request(endpoint, params=None):
    if not API_KEY or not API_SECRET:
        print(f"ERRORE: Impossibile eseguire la richiesta a {endpoint}. Chiavi API mancanti.")
        return None
    timestamp = str(int(time.time() * 1000))
    recv_window = "20000"
    params_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())]) if params else ""
    signature = _get_signature(timestamp, API_KEY, recv_window, params_str)
    headers = {'X-BAPI-API-KEY': API_KEY, 'X-BAPI-TIMESTAMP': timestamp, 'X-BAPI-SIGN': signature, 'X-BAPI-RECV-WINDOW': recv_window}
    full_url = f"{BASE_URL}{endpoint}"
    if params_str:
        full_url += f"?{params_str}"
    try:
        response = requests.get(full_url, headers=headers)
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
    return _send_private_request("/v5/account/wallet-balance", {"accountType": account_type})

def get_open_positions(category="linear"):
    result = _send_private_request("/v5/position/list", {"category": category})
    return result.get('list', []) if result else []

# --- FUNZIONE GET_KLINES MODIFICATA ---
def get_klines(symbol: str, interval: str, limit: int = 200, category: str = "linear"):
    """
    Recupera dati k-line da Bybit. Ora accetta 'category' come parametro.
    'interval' deve essere una stringa compatibile con Bybit (es. '60', '240', 'D').
    """
    print(f"-> BybitClient: Recupero K-lines per {symbol} (Interval: {interval}, Category: {category})...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/v5/market/kline",
            params={
                "category": category,
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            print(f"ERRORE API Bybit ({data.get('retCode')}): {data.get('retMsg')}")
            return pd.DataFrame()

        kline_data = data.get('result', {}).get('list', [])
        if not kline_data:
            return pd.DataFrame()

        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
        df = df.set_index('timestamp').iloc[::-1].copy() # Inverti e crea una copia
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        return df

    except Exception as e:
        print(f"ERRORE CRITICO in bybit_client.get_klines: {e}")
        return pd.DataFrame()
