# api_clients/bybit_client.py
# Client per interagire con le API private di Bybit (saldo, posizioni).

from pybit.unified_trading import HTTP
import config

class BybitClient:
    def __init__(self):
        try:
            self.session = HTTP(
                api_key=config.BYBIT_API_KEY,
                api_secret=config.BYBIT_API_SECRET
            )
        except Exception as e:
            print(f"Errore durante l'inizializzazione del client Bybit: {e}")
            self.session = None

    def get_wallet_balance(self, account_type="UNIFIED"):
        if not self.session: return None
        try:
            return self.session.get_wallet_balance(accountType=account_type)
        except Exception as e:
            print(f"Errore nel recuperare il saldo: {e}")
            return None

    def get_positions(self, category="linear"):
        if not self.session: return None
        try:
            # Per i perpetual USDT, la categoria è "linear"
            return self.session.get_positions(category=category, settleCoin="USDT")
        except Exception as e:
            print(f"Errore nel recuperare le posizioni: {e}")
            return None
