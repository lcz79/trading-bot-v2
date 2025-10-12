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
CONTEXT_TIMEFRAME = "4h"
OPERATIONAL_TIMEFRAME = "15m"

# === CONFIGURAZIONE TIMEFRAMES PER TIPO DI ASSET ===
TIMEFRAMES_CONFIG = {
    'crypto': ['1d', '4h', '1h', '15m']
}

# === REGOLE DI RISCHIO INTRADAY ===
MAX_LOSS_PERC_DAY = 0.02
MAX_TRADES_PER_DAY = 10
COOLDOWN_MIN_AFTER_LOSS = 15
MIN_MINUTES_BEFORE_CLOSE = 15
EOD_FLATTEN_WINDOW_MIN = 5
INTRADAY_SIGNAL_SCORE_THRESHOLD = 60

# === PARAMETRI INDICATORI E STRATEGIE ===
STRATEGY_PARAMS = {
    'context': { 'ema_period': 200, 'adx_period': 14, 'adx_threshold': 18 },
    'trigger': { 'atr_period': 14, 'rsi_period': 14, 'adx_period': 14 },
    'vwap_reversion': { 'atr_multiplier': 1, 'adx_threshold': 25 },
    'orb': { 'minutes': 30 },
    'bollinger_bands': { 'period': 20, 'std_dev': 2.0 }
}

# === ASSET & RUNNER ===
ASSETS_TO_ANALYZE = [
    {"symbol": "BTCUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "ETHUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "SOLUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "XRPUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "DOGEUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "ADAUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "AVAXUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "LINKUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "MATICUSDT", "type": "crypto", "source": "bybit"},
    {"symbol": "DOTUSDT", "type": "crypto", "source": "bybit"}
]
RUNNER_SLEEP_SECONDS = 60

# === IMPOSTAZIONI BACKTEST ===
BACKTEST_ASSET = "BTCUSDT"
BACKTEST_START_DATE = "2025-09-01"
BACKTEST_END_DATE = "2025-09-30"

# === TRAILING STOP ===
TRAILING_STOP_ENABLED = True
TRAILING_STOP_ATR_MULT = 3.0

# === PORTFOLIO GENETICO ===
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
