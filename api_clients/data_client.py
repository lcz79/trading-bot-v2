import pandas as pd
import traceback
from .bybit_client import BybitClient

class FinancialDataClient:
    def __init__(self):
        self.bybit_client = BybitClient()

    def get_data(self, symbol, interval, limit, source):
        try:
            if source == 'Bybit-linear':
                bybit_symbol = symbol
                # Questa logica non è più strettamente necessaria se disabilitiamo 1000SHIBUSDT in config,
                # ma la lasciamo per robustezza futura.
                if symbol == '1000SHIBUSDT':
                    bybit_symbol = 'SHIBUSDT'
                    print(f"-> [DataClient] Traduzione simbolo: '{symbol}' -> '{bybit_symbol}' per Bybit.")

                response = self.bybit_client.get_klines(bybit_symbol, interval, category="linear", limit=limit)
                
                if not response or not response.get('list'):
                    print(f"⚠️ [DataClient] Nessun dato ricevuto da Bybit per {symbol} ({interval}).")
                    return None

                df = pd.DataFrame(response['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                df['timestamp'] = pd.to_numeric(df['timestamp'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df.sort_index(ascending=True, inplace=True)
                return df
            
            else:
                print(f"⚠️ [DataClient] Sorgente dati '{source}' non supportata.")
                return None
                
        except Exception as e:
            print(f"🔥 [DataClient] ERRORE CRITICO IMPREVISTO durante la gestione di {symbol}: {e}")
            traceback.print_exc()
            return None
