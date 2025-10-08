# api_clients/coingecko_client.py - v3.0.0 (Robust & Clean)
# ----------------------------------------------------------------
# - Logica di normalizzazione dei simboli pulita e affidabile.
# - Gestione degli errori migliorata.
# ----------------------------------------------------------------

from pycoingecko import CoinGeckoAPI
import logging

class CoinGeckoClient:
    def __init__(self):
        try:
            self.cg = CoinGeckoAPI()
            self.cg.ping()
        except Exception as e:
            logging.critical(f"Impossibile connettersi a CoinGecko: {e}")
            self.cg = None

    def get_crypto_bulk_data(self, symbols_base: list) -> list:
        if not self.cg: return []
        logging.info(f"Richiesta dati fondamentali per {len(symbols_base)} simboli da CoinGecko...")
        try:
            market_data = self.cg.get_coins_markets(vs_currency='usd')
            market_map = {item['symbol'].upper(): item for item in market_data}
            
            all_data = []
            for symbol in symbols_base:
                asset_data = market_map.get(symbol.upper())
                if isinstance(asset_data, dict):
                    all_data.append(asset_data)
                else:
                    logging.warning(f"Nessun dato CoinGecko trovato per il simbolo: {symbol}")
            
            logging.info(f"Dati fondamentali recuperati per {len(all_data)} asset.")
            return all_data
        except Exception as e:
            logging.error(f"Errore durante il recupero dei dati da CoinGecko: {e}")
            return []
