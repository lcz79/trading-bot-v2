import requests
import pandas as pd # <-- ECCO LA RIGA MANCANTE!

# --- For Yahoo Finance Assets ---
YAHOO_ASSETS = ['SPY', 'QQQ', 'AAPL', 'GOOGL', 'MSFT', 'TSLA']

# --- For Binance Assets ---
BINANCE_API_URL = "https://api.binance.com/api/v3"

# --- For CoinGecko Bulk Metrics ---
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

def get_binance_assets(limit=50):
    """
    Recupera le coppie USDT con il maggior volume di trading da Binance.
    """
    try:
        tickers = requests.get(f"{BINANCE_API_URL}/ticker/24hr").json()
        usdt_tickers = [
            t for t in tickers 
            if isinstance(t, dict) and 'symbol' in t and t['symbol'].endswith('USDT') 
            and not any(x in t['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL'])
        ]
        sorted_tickers = sorted(usdt_tickers, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        return [t['symbol'] for t in sorted_tickers[:limit]]
    except Exception as e:
        print(f"ERRORE: Impossibile recuperare gli asset da Binance. {e}")
        return []

def get_yahoo_assets():
    """
    Restituisce la lista statica di asset per Yahoo Finance.
    """
    return YAHOO_ASSETS

def get_crypto_bulk_metrics(asset_symbols):
    """
    Recupera dati di market cap e volume da CoinGecko per una lista di simboli.
    """
    if not asset_symbols: return {}
    try:
        all_coins_list = requests.get(f"{COINGECKO_API_URL}/coins/list").json()
        symbol_to_id = {c['symbol'].upper(): c['id'] for c in all_coins_list}
        ids_to_fetch = [symbol_to_id[s.replace('USDT', '').upper()] for s in asset_symbols if s.replace('USDT', '').upper() in symbol_to_id]
        if not ids_to_fetch: return {}
        
        params = {'vs_currency': 'eur', 'ids': ','.join(ids_to_fetch)}
        market_data = requests.get(f"{COINGECKO_API_URL}/coins/markets", params=params).json()

        results = {}
        id_to_symbol = {v: k for k, v in symbol_to_id.items()}
        for data in market_data:
            coin_id = data.get('id')
            if coin_id in id_to_symbol:
                results[f"{id_to_symbol[coin_id]}USDT"] = data
        return results
    except Exception as e:
        print(f"ERRORE: Impossibile recuperare i dati da CoinGecko. {e}")
        return {}

def get_binance_klines(symbol, timeframe, limit=200):
    """
    Recupera i dati klines direttamente da Binance (fallback).
    """
    try:
        interval_map = {"1h": "1h", "4h": "4h", "1d": "1d"}
        params = {'symbol': symbol.upper(), 'interval': interval_map.get(timeframe, "1h"), 'limit': limit}
        response = requests.get(f"{BINANCE_API_URL}/klines", params=params)
        response.raise_for_status()
        data = response.json()
        if not data: return None

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
        return df
    except Exception as e:
        print(f"ERRORE: Impossibile recuperare klines da Binance per {symbol}. {e}")
        return None
