# api_clients/data_client.py (v3.0 - con Paginazione per Backtesting completo)
import pandas as pd
import requests
import time
from datetime import datetime, timezone

class FinancialDataClient:
    def get_klines(self, symbol, interval, source='bybit', limit=200, start_time: int = None, end_time: int = None):
        if source.lower() == 'bybit':
            return self._get_bybit_klines_paginated(symbol, interval, start_time, end_time) if start_time and end_time else self._get_bybit_klines(symbol, interval, limit)
        return None

    def _get_bybit_klines(self, symbol, interval, limit):
        """Funzione per il live trading, scarica solo i dati più recenti."""
        return self._fetch_bybit_batch(symbol, interval, limit=limit)

    def _get_bybit_klines_paginated(self, symbol, interval, start_ms, end_ms):
        """Funzione per il backtesting, scarica tutti i dati in un range usando la paginazione."""
        all_dfs = []
        current_start_ms = start_ms
        
        while current_start_ms < end_ms:
            df_batch = self._fetch_bybit_batch(symbol, interval, limit=1000, start_time=current_start_ms)
            
            if df_batch is None:
                print(f"Errore durante il fetch del batch a partire da {current_start_ms}. Interruzione.")
                break
            if df_batch.empty:
                break # Nessun altro dato disponibile

            all_dfs.append(df_batch)
            
            # Preparati per il prossimo ciclo: il nuovo inizio è l'ultimo timestamp del batch + 1ms
            last_timestamp_ms = int(df_batch.index[-1].timestamp() * 1000)
            current_start_ms = last_timestamp_ms + 1
            
            # Attesa per non sovraccaricare l'API
            time.sleep(0.2) 

        if not all_dfs:
            return pd.DataFrame()
            
        # Concatena tutti i DataFrame e rimuovi i duplicati
        full_df = pd.concat(all_dfs)
        full_df = full_df[~full_df.index.duplicated(keep='first')]
        # Filtra esattamente per il range richiesto, nel caso avessimo scaricato un po' di più
        full_df = full_df.loc[(full_df.index >= pd.to_datetime(start_ms, unit='ms', utc=True)) & (full_df.index <= pd.to_datetime(end_ms, unit='ms', utc=True))]
        return full_df.sort_index()


    def _fetch_bybit_batch(self, symbol, interval, limit, start_time=None):
        """Funzione helper che scarica un singolo blocco di dati da Bybit."""
        TIMEFRAME_MAP = {"1d": "D", "4h": "240", "15m": "15", "5m": "5"}
        bybit_interval = TIMEFRAME_MAP.get(str(interval).lower(), interval)
        
        url = "https://api.bybit.com/v5/market/kline"
        params = {'category': 'linear', 'symbol': symbol, 'interval': bybit_interval, 'limit': limit}
        if start_time:
            params['start'] = start_time

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['retCode'] == 0 and data['result']['list']:
                df = pd.DataFrame(data['result']['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
                df.set_index('timestamp', inplace=True)
                df.index = df.index.tz_localize('UTC')

                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df.dropna(inplace=True)
                return df.iloc[::-1] # Bybit restituisce in ordine inverso, quindi giriamo
            
            if data['retCode'] == 0:
                return pd.DataFrame()

            print(f"Errore API Bybit: {data.get('retMsg', 'Errore sconosciuto')}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"Errore di connessione API Bybit: {e}")
            return None
