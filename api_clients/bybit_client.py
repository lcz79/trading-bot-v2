# bybit_client.py — Phoenix v8.2 (Auth via pybit + Kline stabile)
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Client ufficiale Bybit (gestisce firma in automatico)
from pybit.unified_trading import HTTP

# Carica .env dalla root progetto
ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ROOT_ENV, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class BybitClient:
    def __init__(self):
        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET")
        self.testnet = os.getenv("BYBIT_TESTNET", "False").lower() == "true"

        if not self.api_key or not self.api_secret:
            raise ValueError("❌ BYBIT_API_KEY / BYBIT_API_SECRET mancanti nel .env")

        # Sessione autenticata per endpoints privati
        self.session = HTTP(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )
        self.endpoint = "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"
        logging.info(f"BybitClient pronto → {'TESTNET' if self.testnet else 'MAINNET'} ({self.endpoint})")

    # ---- Wallet & Positions (autenticate) ----
    def get_wallet_balance(self, account_type: str = "UNIFIED"):
        try:
            return self.session.get_wallet_balance(accountType=account_type)
        except Exception as e:
            logging.error(f"get_wallet_balance error: {e}")
            return None

    def get_positions(self, category: str = "linear", settle_coin: str = "USDT"):
        try:
            # v5 richiede symbol OPPURE settleCoin: passiamo settleCoin
            return self.session.get_positions(category=category, settleCoin=settle_coin)
        except Exception as e:
            logging.error(f"get_positions error: {e}")
            return None

    # ---- Market data (pubblici) ----
    def fetch_ohlc(self, symbol: str, interval: str = "60", limit: int = 200):
        """Restituisce list di candele (Bybit v5) in formato nativo (liste)."""
        try:
            data = self.session.get_kline(category="linear", symbol=symbol, interval=interval, limit=limit)
            if data and data.get("retCode") == 0:
                return data["result"]["list"]  # lista di liste [ts, open, high, low, close, volume, ...]
            logging.error(f"fetch_ohlc {symbol} errore: {data}")
            return []
        except Exception as e:
            logging.error(f"fetch_ohlc error {symbol}: {e}")
            return []

    def get_ticker(self, symbol: str):
        try:
            data = self.session.get_tickers(category="linear", symbol=symbol)
            if data and data.get("retCode") == 0:
                return float(data["result"]["list"][0]["lastPrice"])
            return None
        except Exception as e:
            logging.error(f"get_ticker error {symbol}: {e}")
            return None
  
