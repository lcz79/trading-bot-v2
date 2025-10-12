import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

print("--- Inizio Test di Connessione a Bybit ---")
load_dotenv()
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

if not api_key or not api_secret:
    print("--- Test Fallito: Chiavi non caricate. Controlla il file .env ---")
else:
    print(f"API Key trovata, inizia con: {api_key[:5]}...")
    print("Tento la connessione a Bybit...")
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
        response = session.get_wallet_balance(accountType="UNIFIED")
        
        if response and response.get('retCode') == 0:
            print("\n--- ✅ SUCCESS! Connessione Riuscita! ---")
        else:
            print("\n--- ❌ TEST FALLITO: Errore nella risposta di Bybit. ---")
            print(f"Risposta completa: {response}")
    except Exception as e:
        print(f"\n--- ❌ TEST FALLITO: Eccezione Python. ---")
        print(e)
