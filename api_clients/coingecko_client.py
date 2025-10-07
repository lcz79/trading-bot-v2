import requests
import json
import time

# URL base per l'API di CoinGecko
BASE_URL = "https://api.coingecko.com/api/v3"

# Cache semplice per mappare i simboli (es. BTCUSDT) agli id di CoinGecko (es. bitcoin)
# Questo evita di fare una chiamata API per la lista completa ogni volta.
# Lo popoliamo con gli asset più comuni.
SYMBOL_TO_ID_CACHE = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "TRX": "tron",
    # Aggiungi altri se necessario
}

def get_crypto_bulk_data(symbols_usdt):
    """
    Recupera dati fondamentali (market cap, volume) per una lista di simboli crypto
    da CoinGecko in un'unica chiamata API.
    
    Args:
        symbols_usdt (list): Una lista di simboli con suffisso USDT (es. ['BTCUSDT', 'ETHUSDT']).

    Returns:
        dict: Un dizionario dove le chiavi sono i simboli originali (es. 'BTCUSDT')
              e i valori sono dizionari con i dati recuperati.
              Restituisce un dizionario vuoto in caso di errore.
    """
    print("-> [CoinGecko] Richiesta dati fondamentali in blocco...")
    
    # 1. Converti i simboli USDT (es. 'BTCUSDT') negli ID di CoinGecko (es. 'bitcoin')
    ids_to_fetch = []
    # Mappa inversa per ritrovare il simbolo originale dall'ID
    id_to_symbol_map = {} 
    
    for symbol_usdt in symbols_usdt:
        base_symbol = symbol_usdt.replace("USDT", "")
        coingecko_id = SYMBOL_TO_ID_CACHE.get(base_symbol)
        if coingecko_id:
            ids_to_fetch.append(coingecko_id)
            id_to_symbol_map[coingecko_id] = symbol_usdt
        else:
            print(f"  -> [CoinGecko] ATTENZIONE: Nessun ID trovato in cache per {base_symbol}. L'asset verrà saltato.")

    if not ids_to_fetch:
        print("  -> [CoinGecko] ERRORE: Nessun ID valido da recuperare.")
        return {}

    # 2. Prepara e esegui la chiamata API
    endpoint = "/coins/markets"
    params = {
        'vs_currency': 'usd',
        'ids': ','.join(ids_to_fetch), # Gli ID devono essere una stringa separata da virgole
        'order': 'market_cap_desc',
        'per_page': len(ids_to_fetch),
        'page': 1,
        'sparkline': 'false'
    }
    
    try:
        response = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        response.raise_for_status()  # Lancia un'eccezione per risposte 4xx/5xx
        data = response.json()
        
        # 3. Processa la risposta e mettila nel formato corretto
        processed_data = {}
        for item in data:
            original_symbol = id_to_symbol_map.get(item['id'])
            if original_symbol:
                processed_data[original_symbol] = {
                    'market_cap': item.get('market_cap'),
                    'total_volume': item.get('total_volume')
                }
        
        print(f"-> [CoinGecko] Successo: Dati fondamentali recuperati per {len(processed_data)} asset.")
        return processed_data

    except requests.exceptions.RequestException as e:
        print(f"🔥 [CoinGecko] ERRORE CRITICO durante la chiamata API: {e}")
        return {}
