# config.py - Modello di configurazione per PHOENIX v9.0 "High-Density Scanner"
import os
from dotenv import load_dotenv
from datetime import time

# Carica le variabili dal file .env
load_dotenv()

# --- BYBIT API CREDENTIALS (Caricate in modo sicuro dall'ambiente) ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# === IMPOSTAZIONI DI SESSIONE ===
TIMEZONE = "Europe/Rome"
SESSION_START_TIME = time(8, 0)
SESSION_END_TIME   = time(22, 0)

# === TIMEFRAMES ===
CONTEXT_TIMEFRAME = "4h"             # Timeframe per decidere il trend (BIAS)
OPERATIONAL_TIMEFRAME = "15m"        # Timeframe per trovare i segnali di ingresso

# === REGOLE DI RISCHIO INTRADAY ===
MAX_LOSS_PERC_DAY = 0.02
MAX_TRADES_PER_DAY = 10              # Aumentato leggermente
COOLDOWN_MIN_AFTER_LOSS = 15       # Ridotto leggermente
MIN_MINUTES_BEFORE_CLOSE = 15
EOD_FLATTEN_WINDOW_MIN = 5
INTRADAY_SIGNAL_SCORE_THRESHOLD = 60 # Leggermente abbassato per più segnali

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
VWAP_ATR_MULTIPLIER = 1            # Leggermente più sensibile
VWAP_ADX_THRESHOLD = 25    # OTTIMIZZATO!

# Opening Range Breakout
ORB_MINUTES = 30

# Bollinger Bands Squeeze
BBANDS_PERIOD = 20
BBANDS_STD = 2.0

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

# === TRAILING STOP ===
TRAILING_STOP_ENABLED = True
TRAILING_STOP_ATR_MULT = 3.0 # Distanza dal prezzo a cui il trailing stop seguirà

# In config.py

# ... tutte le altre tue configurazioni ...

# === PORTFOLIO GENETICO (DA INCOLLARE QUI SOTTO) ===
# Incolla qui il blocco 'OPTIMIZED_PARAMS' generato da optimizer.py

# In config.py
OPTIMIZED_PARAMS = {
    "BTCUSDT": {'k_atr': 0.8, 'rsi_len': 14, 'adx_threshold': 25},
    "ETHUSDT": {'k_atr': 0.8, 'rsi_len': 16, 'adx_threshold': 28},
    "SOLUSDT": {'k_atr': 1.8, 'rsi_len': 16, 'adx_threshold': 32},
    "XRPUSDT": {'k_atr': 1.5, 'rsi_len': 12, 'adx_threshold': 25},
    "DOGEUSDT": {'k_atr': 0.8, 'rsi_len': 16, 'adx_threshold': 30},
    "ADAUSDT": {'k_atr': 0.8, 'rsi_len': 12, 'adx_threshold': 30},
    "AVAXUSDT": {'k_atr': 0.8, 'rsi_len': 14, 'adx_threshold': 32},
    "LINKUSDT": {'k_atr': 0.8, 'rsi_len': 12, 'adx_threshold': 25},
}
