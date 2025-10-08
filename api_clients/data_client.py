# api_clients/data_client.py - v3.0.0 (Robust & Clean)
# ----------------------------------------------------------------
# - Risolve il FutureWarning convertendo correttamente i tipi di dato.
# - Migliora il logging degli errori.
# ----------------------------------------------------------------

import pandas as pd
import logging
from .bybit_client import BybitClient

class FinancialDataClient:
    def get_klines(self, symbol: str, interval: str, source: str, limit: int = 200) -> pd.DataFrame | None:
        if source != 'bybit':
            logging.warning(f"Sorgente dati '{source}' non supportata.")
            return None
        try:
            client = BybitClient()
            response = client.session.get_kline(category="linear", symbol=symbol, interval=interval, limit=limit)
            if not response or response.get('retCode') != 0:
                msg = response.get('retMsg', 'Errore sconosciuto') if response else "Nessuna risposta dall'API"
                logging.error(f"Errore API Bybit per {symbol} ({interval}): {msg}")
                return None
            
            klines = response['result']['list']
            if not klines: return None
            
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            return df.iloc[::-1][['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logging.error(f"ERRORE CRITICO in DataClient ({symbol}, {interval}): {e}", exc_info=False)
            return None
