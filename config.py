# config.py - v4.0 (Phoenix Patch v7.0 Applied)

# Timeframes attivi per l'analisi multi-frattale
ACTIVE_TIMEFRAMES = ["1d", "4h", "15m"]

# Soglia minima per accettare un segnale (dopo bonus di coerenza)
SIGNAL_SCORE_THRESHOLD = 70

# Parametri indicatori
RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14

# Soglie più permissive (per aumentare densità segnali)
ADX_THRESHOLD = 30
RSI_LOW = 35
RSI_HIGH = 65
VOLUME_Z_SCORE_MIN = 0.5

# Risk Management (default)
SL_ATR_MULTIPLIER = 1.5
TP_ATR_MULTIPLIER = 2.0

# Sorgente dati e universo asset (30 crypto)
DATA_SOURCE = "bybit"
TIMEFRAME = "1d"  # Default, ma ora è gestito da ACTIVE_TIMEFRAMES

ASSET_UNIVERSE = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "AVAXUSDT","LINKUSDT","MATICUSDT","LTCUSDT","ATOMUSDT","DOTUSDT",
    "UNIUSDT","AAVEUSDT","SANDUSDT","APEUSDT","NEARUSDT","FILUSDT",
    "ETCUSDT","OPUSDT","ARBUSDT","INJUSDT","RUNEUSDT","IMXUSDT",
    "SNXUSDT","SEIUSDT","XLMUSDT","RNDRUSDT","FTMUSDT","GALAUSDT"
]
# ... tutte le altre configurazioni ...

# --- BYBIT API CREDENTIALS ---
# Aggiungi qui le tue chiavi API di Bybit
BYBIT_API_KEY = "t2LFurNjKgTSNOL3z1"
BYBIT_API_SECRET = "dxGg8tJI9BMtIUWRjt5b8jEy5KnQ9Q8e1kun"
