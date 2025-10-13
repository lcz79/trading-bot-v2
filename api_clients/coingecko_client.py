# coingecko_client.py — Phoenix v7.2
# Client aggiornato con supporto bulk data per CoinGecko

import requests
import logging
import time

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.symbol_to_id_map = self._build_symbol_map()

    def _build_symbol_map(self):
        """Scarica la lista completa di coin e crea una mappa simbolo -> id"""
        try:
            resp = requests.get(f"{self.BASE_URL}/coins/list")
            resp.raise_for_status()
            data = resp.json()
            return {item["symbol"].lower(): item["id"] for item in data}
        except Exception as e:
            logging.error(f"CoinGeckoClient: errore nel caricamento della lista coin - {e}")
            return {}

    def get_coin_id(self, symbol: str):
        """Restituisce l’ID CoinGecko a partire dal simbolo (es. BTCUSDT -> bitcoin)."""
        base = symbol.replace("USDT", "").lower()
        return self.symbol_to_id_map.get(base)

    def get_crypto_bulk_data(self, symbols_base: list):
        """Richiede dati di mercato per un elenco di simboli."""
        coin_ids = []
        for sym in symbols_base:
            cid = self.get_coin_id(sym)
            if cid:
                coin_ids.append(cid)
        if not coin_ids:
            logging.warning("CoinGeckoClient: nessun ID valido trovato per la richiesta bulk.")
            return []

        ids_str = ",".join(coin_ids)
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids_str,
            "order": "market_cap_desc",
            "per_page": len(coin_ids),
            "page": 1,
            "sparkline": "false"
        }

        try:
            time.sleep(1.5)
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logging.error(f"CoinGeckoClient: errore nella richiesta bulk - {e}")
            return []
