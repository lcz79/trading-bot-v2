import requests
import pandas as pd

BASE_URL = "https://api.binance.com/api/v3"

def get_klines(symbol: str, interval: str, limit: int = 500):
    """Recupera dati storici da Binance e li restituisce come DataFrame."""
    endpoint = f"{BASE_URL}/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return pd.DataFrame() # Restituisce un DataFrame vuoto

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'number_of_trades', 
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        return df[numeric_cols]

    except requests.exceptions.RequestException as e:
        print(f"ERRORE in binance_client.get_klines per {symbol}: {e}")
        return None
