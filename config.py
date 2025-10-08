# config.py - v4.1.0 (Ticker Correction)
# ----------------------------------------------------------------
# - Corretto il ticker di PEPE da 'PEPEUSDT' a '1000PEPEUSDT' per
#   allineamento con l'API di Bybit.
# ----------------------------------------------------------------

# Lista degli asset crypto da analizzare.
ASSETS_TO_ANALYZE = [
    # --- Major Caps (I Pilastri) ---
    {'symbol': 'BTCUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ETHUSDT', 'source': 'bybit', 'type': 'crypto'},
    
    # --- Large Caps & Piattaforme Layer 1 ---
    {'symbol': 'SOLUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'BNBUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'XRPUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ADAUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'AVAXUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'TRXUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'DOTUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'TONUSDT', 'source': 'bybit', 'type': 'crypto'},
    
    # --- Meme Coins & Community Driven ---
    {'symbol': 'DOGEUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'SHIB1000USDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': '1000PEPEUSDT', 'source': 'bybit', 'type': 'crypto'}, # <-- CORREZIONE APPLICATA QUI
    {'symbol': 'WIFUSDT', 'source': 'bybit', 'type': 'crypto'},
    
    # --- Oracoli & Interoperabilità ---
    {'symbol': 'LINKUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ICPUSDT', 'source': 'bybit', 'type': 'crypto'},
    
    # --- Layer 2 & Scaling Solutions ---
    {'symbol': 'MATICUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'OPUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ARBUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'IMXUSDT', 'source': 'bybit', 'type': 'crypto'},
    
    # --- Altre Large & Mid Caps ---
    # ... (il resto della lista rimane invariato)
    {'symbol': 'BCHUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'LTCUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'NEARUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'UNIUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'INJUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ETCUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'XLMUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'FILUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'APTUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'HBARUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'CROUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'VETUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'RNDRUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'GRTUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'AAVEUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'MKRUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'FETUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'SUIUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'SEIUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'SANDUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'MANAUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'AXSUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'FTMUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'EOSUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'XTZUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ALGOUSDT', 'source': 'bybit', 'type': 'crypto'},
    {'symbol': 'ATOMUSDT', 'source': 'bybit', 'type': 'crypto'},
]

# Configurazione dei timeframe da analizzare.
TIMEFRAMES_CONFIG = {
    'crypto': ['60', '240', 'D'],
}

# Parametri per le strategie di analisi.
STRATEGY_PARAMS = {
    'mean_reversion': {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
    },
    'trend_following': {
        'fast_ema_period': 20,
        'slow_ema_period': 50,
    }
}
