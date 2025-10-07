# ==============================================================================
# CONFIGURAZIONE CENTRALE DEL PROGETTO PHOENIX (v1.1)
# ==============================================================================

# --- 1. ASSET DA ANALIZZARE ---
ASSETS_TO_ANALYZE = [
    # Criptovalute (derivati lineari da Bybit)
    {'symbol': 'BTCUSDT', 'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'ETHUSDT', 'source': 'Bybit-linear', 'type': 'crypto'},
    {'symbol': 'SOLUSDT', 'source': 'Bybit-linear', 'type': 'crypto'},
    
    # Azioni/ETF (da Yahoo Finance)
    {'symbol': 'SPY', 'source': 'Yahoo', 'type': 'stock'},
    {'symbol': 'QQQ', 'source': 'Yahoo', 'type': 'stock'},
    {'symbol': 'AAPL', 'source': 'Yahoo', 'type': 'stock'},
]

# --- 2. STRATEGIE DA APPLICARE ---
STRATEGIES = [
    "Trend Following",
    "Mean Reversion",
]

# --- 3. TIMEFRAME DA ANALIZZARE ---
# Dizionario di timeframe specifici per tipo di asset
# per gestire le differenze tra le API (es. Bybit vs Yahoo)
#
TIMEFRAMES_CONFIG = {
    'crypto': [
        "60",  # 60 minuti (1 ora)
        "240", # 240 minuti (4 ore)
    ],
    'stock': [
        "1h",  # 1 ora (formato Yahoo)
        "1d",  # 1 giorno (formato Yahoo)
    ]
}
