# config.template.py - Modello di configurazione per PHOENIX v10.0 "Sinergia"
from datetime import time

# --- BYBIT API CREDENTIALS ---
BYBIT_API_KEY = "INSERISCI_QUI_LA_TUA_API_KEY"
BYBIT_API_SECRET = "INSERISCI_QUI_IL_TUO_API_SECRET"

# === IMPOSTAZIONI DI SESSIONE ===
TIMEZONE = "Europe/Rome"
SESSION_START_TIME = time(8, 0)
SESSION_END_TIME   = time(22, 0)

# === TIMEFRAMES ===
CONTEXT_TIMEFRAME = "4h"
OPERATIONAL_TIMEFRAME = "15m"

# === REGOLE DI RISCHIO INTRADAY ===
MAX_LOSS_PERC_DAY = 0.02
MAX_TRADES_PER_DAY = 10
COOLDOWN_MIN_AFTER_LOSS = 15
MIN_MINUTES_BEFORE_CLOSE = 15
EOD_FLATTEN_WINDOW_MIN = 5
INTRADAY_SIGNAL_SCORE_THRESHOLD = 60

# === PARAMETRI INDICATORI E STRATEGIE ===
# Contesto (4h)
EMA_CONTEXT_PERIOD = 200
ADX_CONTEXT_PERIOD = 14
ADX_CONTEXT_THRESHOLD = 18

# Trigger (15m)
ATR_PERIOD = 14
RSI_PERIOD = 14
ADX_PERIOD = 14

# VWAP Reversion
VWAP_ATR_MULTIPLIER = 0.6

# Opening Range Breakout
ORB_MINUTES = 30

# Bollinger Bands Squeeze
BBANDS_PERIOD = 20
BBANDS_STD = 2.0

# === TRAILING STOP ===
TRAILING_STOP_ENABLED = True
TRAILING_STOP_ATR_MULT = 2.5 # Distanza dal prezzo a cui il trailing stop seguirà

# === ASSET & RUNNER ===
ASSET_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT"
]
RUNNER_SLEEP_SECONDS = 60

# === IMPOSTAZIONI BACKTEST ===
BACKTEST_ASSET = "BTCUSDT"
BACKTEST_START_DATE = "2025-09-01"
BACKTEST_END_DATE = "2025-09-30"
# ... (tutto il contenuto precedente) ...

# === PORTFOLIO GENETICO ===
# Questo blocco viene generato da optimizer.py.
# Eseguire l'ottimizzatore per ottenere i parametri specifici per ogni asset.
OPTIMIZED_PARAMS = {
    # Esempio:
    # "BTCUSDT": {'k_atr': 0.8, 'rsi_len': 14, 'adx_threshold': 25},
    # "ETHUSDT": {'k_atr': 0.8, 'rsi_len': 16, 'adx_threshold': 28},
}
