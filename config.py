# ==============================================================================
# CONFIGURAZIONE DEGLI ASSET DA ANALIZZARE
# ==============================================================================
# Ogni dizionario rappresenta un asset da monitorare.
# 'symbol': Il ticker usato dall'exchange (es. 'BTCUSDT').
# 'source': Il client da usare per i dati ('Bybit-linear', 'Bybit-inverse', 'YahooFinance').
# 'type': La categoria dell'asset ('crypto', 'stock', 'etf').

ASSETS_TO_ANALYZE = [
    # --- COMBINAZIONI VALIDATE E PROFITTEVOLI ---
    {
        "symbol": "BTCUSDT", 
        "source": "Bybit-linear", 
        "type": "crypto",
        "comment": "Strategia 'Mean Reversion Pro' validata con backtest. Profit Factor: 2.00"
    },
    
    # --- COMBINAZIONI SPERIMENTALI O NON ANCORA VALIDATE ---
    {
        "symbol": "ETHUSDT", 
        "source": "Bybit-linear", 
        "type": "crypto",
        "comment": "Backtest ha mostrato una perdita con la strategia attuale. Da monitorare o ri-ottimizzare."
    },
    {
        "symbol": "SOLUSDT", 
        "source": "Bybit-linear", 
        "type": "crypto",
        "comment": "Non ancora testato."
    },
    
    # --- ESEMPI DI ASSET TRADIZIONALI (azioni/ETF) ---
    # {
    #     "symbol": "SPY", 
    #     "source": "YahooFinance", 
    #     "type": "etf",
    #     "comment": "Esempio ETF S&P 500. Richiede una strategia diversa (es. trend-following)."
    # },
    # {
    #     "symbol": "AAPL", 
    #     "source": "YahooFinance", 
    #     "type": "stock",
    #     "comment": "Esempio azione Apple."
    # },
]

# ==============================================================================
# CONFIGURAZIONE DEI TIMEFRAME PER TIPO DI ASSET
# ==============================================================================
# Qui specifichiamo quali timeframe analizzare per ogni 'type' di asset.
# Questo permette di usare timeframe più lunghi per le azioni e più corti per le crypto.
#
# Formati timeframe:
# - Per Bybit: '1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'
# - Per Yahoo Finance: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'

TIMEFRAMES_CONFIG = {
    "crypto": [
        "240",  # Timeframe 4 ore (validato per BTCUSDT)
        "60",   # Timeframe 1 ora (sperimentale)
        "D"     # Timeframe giornaliero
    ],
    "stock": ["D"], # Per le azioni, analizziamo solo il giornaliero
    "etf": ["D"],   # Anche per gli ETF, solo il giornaliero
}
