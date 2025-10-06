import os
import time
import hmac
import hashlib
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
BASE_URL = "https://api.bybit.com"

# --- Wrapper API sicuro con retry (dal consulente) ---
def safe_request(method, url, headers=None, params=None, data=None, retries=3, timeout=10):
    for i in range(retries):
        try:
            response = requests.request(method, url, headers=headers, params=params, data=data, timeout=timeout)
            response.raise_for_status()
            if not response.text:
                print(f"WARN: Risposta vuota da {url} (status: {response.status_code})")
                return None
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"ERRORE HTTP ({i+1}/{retries}): {e.response.status_code} - {e.response.text}")
            if e.response.status_code in [401, 403]:
                return e.response.json() if e.response.text else None
            time.sleep(2 ** i)
        except requests.exceptions.RequestException as e:
            print(f"ERRORE di Rete ({i+1}/{retries}): {e}")
            time.sleep(2 ** i)
        except json.JSONDecodeError:
            print(f"ERRORE JSONDecode ({i+1}/{retries}): Impossibile decodificare la risposta da {url}")
            time.sleep(2 ** i)
            
    print(f"ERRORE FATALE: Impossibile eseguire la richiesta a {url} dopo {retries} tentativi.")
    return None

# Firma HMAC: timestamp + apiKey + recvWindow + (queryString | requestBody)
def get_signature(payload_str, timestamp, recv_window="5000"):
    param_str = str(timestamp) + API_KEY + recv_window + payload_str
    return hmac.new(bytes(API_SECRET, "utf-8"), param_str.encode("utf-8"), hashlib.sha256).hexdigest()

def http_request(method, endpoint, payload):
    timestamp = int(time.time() * 1000)
    recv_window = "5000"
    headers = {'X-BAPI-API-KEY': API_KEY, 'X-BAPI-TIMESTAMP': str(timestamp), 'X-BAPI-RECV-WINDOW': recv_window, 'Content-Type': 'application/json'}
    url = BASE_URL + endpoint
    
    if method == "POST":
        body_str = json.dumps(payload)
        headers['X-BAPI-SIGN'] = get_signature(body_str, timestamp, recv_window)
        return safe_request(method, url, headers=headers, data=body_str)
    else: # GET
        sorted_payload = sorted(payload.items())
        params_str = '&'.join([f"{key}={value}" for key, value in sorted_payload])
        headers['X-BAPI-SIGN'] = get_signature(params_str, timestamp, recv_window)
        return safe_request(method, url, headers=headers, params=payload)

def get_wallet_balance():
    payload = {"accountType": "UNIFIED"}
    response = http_request("GET", "/v5/account/wallet-balance", payload)
    if response and response.get('retCode') == 0:
        return response['result']['list'][0]
    print(f"Errore API get_wallet_balance: {response}")
    return None

def get_klines(symbol, interval, limit=200):
    interval_map = {"1h": "60", "4h": "240", "1d": "D"}
    mapped_interval = interval_map.get(interval, interval)

    # --- CORREZIONE FINALE: Assicura che il simbolo sia sempre in maiuscolo per Bybit ---
    payload = {"category": "linear", "symbol": symbol.upper(), "interval": mapped_interval, "limit": limit}
    
    response = http_request("GET", "/v5/market/klines", payload)
    if response and response.get('retCode') == 0:
        data = response['result']['list']
        if not data: return None
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp').sort_index()
        df = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
        return df
    return None

def get_open_positions():
    payload = {"category": "linear", "settleCoin": "USDT"}
    response = http_request("GET", "/v5/position/list", payload)
    if response and response.get('retCode') == 0:
        return response['result']['list']
    print(f"Errore API get_open_positions: {response}")
    return []
