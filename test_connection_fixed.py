from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os

load_dotenv()

session = HTTP(
    api_key=os.getenv("BYBIT_API_KEY"),
    api_secret=os.getenv("BYBIT_API_SECRET"),
    testnet=False   # Deve essere False per chiavi reali
)

print("--- Test Bybit LIVE ---")
try:
    r = session.get_api_key_information()
    print("✅ Connessione riuscita:")
    print(r)
except Exception as e:
    print("❌ Errore:", e)