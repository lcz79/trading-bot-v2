# Lista degli asset da analizzare.
# Ogni asset è un dizionario con simbolo, sorgente dati e tipo.
ASSETS_TO_ANALYZE = [
    {'symbol': 'BTCUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'ETHUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'SOLUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'XRPUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'DOGEUSDT',     'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'ADAUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'AVAXUSDT',     'source': 'Bybit-linear', 'type': 'crypto'},
    # {'symbol': '1000SHIBUSDT', 'source': 'Bybit-linear', 'type': 'crypto'}, # Disabilitato perché non più valido su Bybit
    {'symbol': 'DOTUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'LINKUSDT',     'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'TRXUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'BCHUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'LTCUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'ATOMUSDT',     'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'NEARUSDT',     'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'UNIUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'ICPUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'FTMUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'APEUSDT',      'source': 'Bybit-linear', 'type': 'crypto'},
]

# Configurazione dei timeframe da analizzare per tipo di asset
TIMEFRAMES_CONFIG = {
    'crypto': ['60', '240'],  # 60 min (1h), 240 min (4h)
    # Esempio per altri tipi di asset
    # 'stock': ['D'],
    # 'forex': ['60', 'D'],
}
