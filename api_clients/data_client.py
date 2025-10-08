# api_clients/data_client.py - (Phoenix Patch v7.0 Applied)
import pandas as pd
import requests

class FinancialDataClient:
    def get_klines(self, symbol, interval, source='bybit', limit=500):
        if source.lower() == 'bybit':
            return self._get_bybit_klines(symbol, interval, limit)
        return None

    def _get_bybit_klines(self, symbol, interval, limit):
        # PATCH 4: Mapping dei timeframe
        TIMEFRAME_MAP = {"1d": "D", "4h": "240", "15m": "15"}
        bybit_interval = TIMEFRAME_MAP.get(str(interval).lower(), interval)
        
        url = "https://api.bybit.com/v5/market/kline"
        params = {'category': 'spot', 'symbol': symbol, 'interval': bybit_interval, 'limit': limit}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == 0 and data['result']['list']:
                df = pd.DataFrame(data['result']['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
                df.set_index('timestamp', inplace=True)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df.dropna(inplace=True)
                return df.iloc[::-1]
            return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"Errore API Bybit: {e}")
            return None
