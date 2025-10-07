import os
import time
from pybit.unified_trading import HTTP

class BybitClient:
    def __init__(self):
        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise ValueError("BYBIT_API_KEY e BYBIT_API_SECRET devono essere impostati nel file .env")
        
        self.session = HTTP(
            testnet=False,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

    def _make_request(self, method, *args, **kwargs):
        try:
            time.sleep(0.2) # 200ms di attesa per non sovraccaricare l'API
            response = method(*args, **kwargs)
            if response.get('retCode') != 0:
                print(f"Errore durante la richiesta a Bybit: {response.get('retMsg')} (Codice: {response.get('retCode')}).\nRequest → {response.get('req_info')}.")
                return None
            return response['result']
        except Exception as e:
            print(f"Errore durante la richiesta a Bybit: {e}")
            return None

    def get_klines(self, symbol, interval, category="linear", limit=200):
        print(f"-> BybitClient: Recupero K-lines per {symbol} (Interval: {interval}, Category: {category})...")
        return self._make_request(
            self.session.get_kline,
            category=category,
            symbol=symbol,
            interval=interval,
            limit=limit
        )
    # ... (gli altri metodi come get_equity, place_order rimangono invariati)