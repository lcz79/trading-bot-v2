# coingecko_client.py - Phoenix v7.0
# Aggiunto supporto per richieste bulk e fallback automatico ID

import requests
import logging
import time

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.coin_list = self._get_coin_list()
        if not self.coin_list:
            logging.warning("CoinGeckoClient: impossibile caricare la lista monete.")
            self.symbol_to_id_map = {}
        else:
            self.symbol_to_id_map = {item['symbol'].lower(): item['id'] for item in self.coin_list}

    def _get_coin_list(self):
        """Scarica la lista completa di monete da CoinGecko per la mappatura simbolo→id"""
        try:
            url = f"{self.BASE_URL}/coins/list"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"CoinGeckoClient: errore scaricamento lista monete: {e}")
            return None

    def get_coin_id(self, symbol: str) -> str | None:
        """Restituisce l'ID CoinGecko corretto per un simbolo tipo 'BTC'."""
        if not symbol:
            return None
        base_symbol = symbol.replace('USDT', '').replace('USDC', '').lower()
        return self.symbol_to_id_map.get(base_symbol)

    def get_market_data(self, coin_id: str) -> dict | None:
        """Recupera i dati di mercato per un singolo ID CoinGecko."""
        if not coin_id:
            return None
        try:
            url = f"{self.BASE_URL}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': coin_id,
                'order': 'market_cap_desc',
                'per_page': 1,
                'page': 1,
                'sparkline': 'false'
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return data[0]
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"CoinGeckoClient: errore API per ID {coin_id}: {e}")
            return None

    def get_crypto_bulk_data(self, symbols_base: list) -> list:
        """
        Scarica in un'unica chiamata i dati di mercato per più asset.
        """
        ids = []
        for sym in symbols_base:
            cid = self.get_coin_id(sym)
            if cid:
                ids.append(cid)
            else:
                logging.warning(f"CoinGeckoClient: ID non trovato per simbolo {sym}")

        if not ids:
            logging.warning("CoinGeckoClient: nessun ID valido trovato per richiesta bulk.")
            return []

        try:
            joined_ids = ",".join(ids)
            url = f"{self.BASE_URL}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': joined_ids,
                'order': 'market_cap_desc',
                'per_page': len(ids),
                'page': 1,
                'sparkline': 'false'
            }

            logging.info(f"CoinGeckoClient: Richiesta bulk per {len(ids)} asset...")
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            time.sleep(1.5)  # rispetta il rate limit
            return data
        except requests.exceptions.RequestException as e:
            logging.error(f"CoinGeckoClient: errore durante richiesta bulk: {e}")
            return []
