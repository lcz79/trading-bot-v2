import requests
import time

class CoinGeckoClient:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        print("-> Inizializzazione CoinGeckoClient...")

    def _make_request(self, endpoint, params=None):
        url = self.base_url + endpoint
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            time.sleep(1.5) 
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"🔥 [CoinGecko] Errore di connessione: {e}")
            return None
        except Exception as e:
            print(f"🔥 [CoinGecko] Errore generico: {e}")
            return None

    def get_crypto_bulk_data(self, symbols: list) -> dict:
        print(f"-> [CoinGecko] Richiesta dati fondamentali per {len(symbols)} simboli...")
        
        id_map = {
            'BTCUSDT': 'bitcoin', 'ETHUSDT': 'ethereum', 'SOLUSDT': 'solana',
            'XRPUSDT': 'ripple', 'DOGEUSDT': 'dogecoin', 'ADAUSDT': 'cardano',
            'AVAXUSDT': 'avalanche-2', 'SHIBUSDT': 'shiba-inu', 'DOTUSDT': 'polkadot',
            'LINKUSDT': 'chainlink', 'TRXUSDT': 'tron', 'MATICUSDT': 'matic-network',
            'BCHUSDT': 'bitcoin-cash', 'LTCUSDT': 'litecoin', 'ATOMUSDT': 'cosmos',
            'NEARUSDT': 'near', 'UNIUSDT': 'uniswap', 'ICPUSDT': 'internet-computer',
            'FTMUSDT': 'fantom', 'APEUSDT': 'apecoin'
        }
        
        coingecko_ids = [id_map.get(s) for s in symbols if id_map.get(s)]
        if not coingecko_ids: return {}

        params = { 'ids': ','.join(coingecko_ids), 'vs_currency': 'usd', 'per_page': len(coingecko_ids), 'page': 1, 'sparkline': 'false' }
        data = self._make_request("/coins/markets", params=params)

        if not data: return {}
        
        formatted_data = {}
        reverse_id_map = {v: k for k, v in id_map.items()}
        for item in data:
            base_symbol = reverse_id_map.get(item['id'])
            if base_symbol: formatted_data[base_symbol] = item
        
        print(f"-> [CoinGecko] Successo: Dati fondamentali recuperati per {len(formatted_data)} asset.")
        return formatted_data
