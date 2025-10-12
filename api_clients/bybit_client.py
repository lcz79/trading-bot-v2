import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import logging

load_dotenv()

class BybitClient:
    def __init__(self):
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError("ERRORE: BYBIT_API_KEY o BYBIT_API_SECRET non trovati. Controlla il file .env.")

        self.session = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
        )

    def get_wallet_balance(self, accountType="UNIFIED"):
        try:
            return self.session.get_wallet_balance(accountType=accountType)
        except Exception as e:
            logging.error(f"Errore Bybit nel recuperare il saldo: {e}")
            return None

    def get_positions(self, category="linear", settleCoin="USDT"):
        try:
            return self.session.get_position_list(category=category, settleCoin=settleCoin)
        except Exception as e:
            logging.error(f"Errore Bybit nel recuperare le posizioni: {e}")
            return None
    
    def get_klines(self, category="linear", symbol="BTCUSDT", interval="15", limit=200):
        try:
            return self.session.get_kline(
                category=category,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
        except Exception as e:
            logging.error(f"Errore Bybit nel recuperare le klines per {symbol}: {e}")
            return None
