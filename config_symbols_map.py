# config_symbols_map.py
# Mappa simbolo -> ID CoinGecko (ID ufficiali usati nelle API di CoinGecko)
# Nota: CoinGecko per MATIC usa l'ID "polygon" (non "matic-network").
COINGECKO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "MATIC": "polygon",  # <- punto chiave della tua warning
}

def get_coingecko_id(symbol: str) -> str | None:
    """
    Ritorna l'ID CoinGecko corrispondente al simbolo.
    Esempio: "MATIC" -> "polygon"
    """
    sym = (symbol or "").upper().replace("USDT", "").replace("USDC", "")
    return COINGECKO_ID_MAP.get(sym)

