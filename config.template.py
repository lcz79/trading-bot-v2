# config.template.py - Modello di configurazione
# Copia questo file in config.py e inserisci i tuoi valori.

# --- BYBIT API CREDENTIALS ---
# Aggiungi qui le tue chiavi API di Bybit
BYBIT_API_KEY = "INSERISCI_QUI_LA_TUA_API_KEY"
BYBIT_API_SECRET = "INSERISCI_QUI_IL_TUO_API_SECRET"

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
TIMEFRAME = "1d"

ASSET_UNIVERSE = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "AVAXUSDT","LINKUSDT","MATICUSDT","LTCUSDT","ATOMUSDT","DOTUSDT",
    "UNIUSDT","AAVEUSDT","SANDUSDT","APEUSDT","NEARUSDT","FILUSDT",
    "ETCUSDT","OPUSDT","ARBUSDT","INJUSDT","RUNEUSDT","IMXUSDT",
    "SNXUSDT","SEIUSDT","XLMUSDT","RNDRUSDT","FTMUSDT","GALAUSDT"
]
