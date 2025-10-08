# analysis/market_analysis.py - v4.0.0 (Smarter Signal Logic)
# ----------------------------------------------------------------
# - Logica Trend Following migliorata: ora cerca non solo l'incrocio
#   esatto, ma anche i pullback post-incrocio, aumentando le opportunità.
# - Aggiunge più controlli e commenti per una maggiore chiarezza.
# - Questa è la versione finale e stabile della logica di analisi.
# ----------------------------------------------------------------

import pandas as pd
import pandas_ta as ta
from config import STRATEGY_PARAMS

def get_fundamental_quality_score(asset: dict, crypto_bulk_data: list) -> (int, dict):
    # ... (invariato)
    symbol_base = asset.get('symbol', '').replace('USDT', '').replace('1000', '')
    asset_data = next((item for item in crypto_bulk_data if item.get("symbol", "").upper() == symbol_base.upper()), None)
    if not asset_data: return 0, {"reason": "Dati non trovati"}
    market_cap = asset_data.get('market_cap', 0); volume_24h = asset_data.get('total_volume', 0)
    score = 0
    if market_cap > 1_000_000_000: score += 40
    elif market_cap > 500_000_000: score += 20
    if volume_24h > 100_000_000: score += 40
    elif volume_24h > 50_000_000: score += 20
    if asset_data.get('market_cap_rank', 999) <= 100: score += 20
    return score, {"market_cap": market_cap, "volume_24h": volume_24h}

def get_higher_timeframe_trend(daily_data: pd.DataFrame) -> (str, dict):
    """Determina il trend usando i dati giornalieri, in modo thread-safe."""
    try:
        df = daily_data.copy()
        slow_ema_name = f"EMA_{STRATEGY_PARAMS['trend_following']['slow_ema_period']}"
        fast_ema_name = f"EMA_{STRATEGY_PARAMS['trend_following']['fast_ema_period']}"
        df.ta.ema(length=STRATEGY_PARAMS['trend_following']['slow_ema_period'], append=True)
        df.ta.ema(length=STRATEGY_PARAMS['trend_following']['fast_ema_period'], append=True)
        
        if fast_ema_name not in df.columns or slow_ema_name not in df.columns:
            return "NEUTRAL", {"reason": "Impossibile calcolare EMA per HTF."}
        last_candle = df.iloc[0]
        return ("UPTREND", {}) if last_candle[fast_ema_name] > last_candle[slow_ema_name] else ("DOWNTREND", {})
    except Exception as e:
        return "NEUTRAL", {"reason": f"Errore analisi HTF: {e}"}

def run_single_scan(original_df: pd.DataFrame, symbol: str, timeframe: str, htf_trend: str) -> list:
    """Esegue le strategie usando i dati, in modo thread-safe e con logica migliorata."""
    df = original_df.copy()
    signals, params_mr, params_tf = [], STRATEGY_PARAMS['mean_reversion'], STRATEGY_PARAMS['trend_following']
    if len(df) < max(params_mr['rsi_period'], params_tf['slow_ema_period']) + 5: return []

    # 1. Analisi Mean Reversion (RSI) - Logica invariata
    rsi_col = f'RSI_{params_mr["rsi_period"]}'
    df.ta.rsi(length=params_mr['rsi_period'], append=True)
    if rsi_col in df.columns and len(df) > 1:
        last, prev = df.iloc[0], df.iloc[1]
        if prev[rsi_col] < params_mr['rsi_oversold'] and last[rsi_col] > params_mr['rsi_oversold'] and htf_trend == 'UPTREND':
            signals.append({'Asset': symbol, 'Timeframe': timeframe, 'Segnale': 'RSI Long', 'Prezzo': last['close'], 'Stop Loss': last['low'] * 0.99, 'Take Profit': last['close'] * 1.05, 'Score': 60, 'Strategia': 'Mean Reversion'})
        if prev[rsi_col] > params_mr['rsi_overbought'] and last[rsi_col] < params_mr['rsi_overbought'] and htf_trend == 'DOWNTREND':
            signals.append({'Asset': symbol, 'Timeframe': timeframe, 'Segnale': 'RSI Short', 'Prezzo': last['close'], 'Stop Loss': last['high'] * 1.01, 'Take Profit': last['close'] * 0.95, 'Score': 60, 'Strategia': 'Mean Reversion'})

    # 2. Analisi Trend Following (EMA) - LOGICA MIGLIORATA
    fast_ema = f'EMA_{params_tf["fast_ema_period"]}'; slow_ema = f'EMA_{params_tf["slow_ema_period"]}'
    df.ta.ema(length=params_tf['fast_ema_period'], append=True); df.ta.ema(length=params_tf['slow_ema_period'], append=True)
    if fast_ema in df.columns and slow_ema in df.columns and len(df) > 3:
        last, prev, third = df.iloc[0], df.iloc[1], df.iloc[2]
        
        # Condizione 1: Incrocio rialzista appena avvenuto (nelle ultime 3 candele)
        bullish_cross_happened = (prev[fast_ema] > prev[slow_ema] and third[fast_ema] < third[slow_ema]) or \
                                 (last[fast_ema] > last[slow_ema] and prev[fast_ema] < prev[slow_ema])
        
        # Condizione 2: Pullback verso le medie (prezzo chiude sotto la media veloce)
        is_pullback_long = last['close'] < last[fast_ema]

        if bullish_cross_happened and is_pullback_long and htf_trend == 'UPTREND':
            signals.append({'Asset': symbol, 'Timeframe': timeframe, 'Segnale': 'EMA Pullback Long', 'Prezzo': last['close'], 'Stop Loss': last['low'] * 0.98, 'Take Profit': last['close'] * 1.06, 'Score': 85, 'Strategia': 'Trend Following'})

        # Condizione 1: Incrocio ribassista appena avvenuto (nelle ultime 3 candele)
        bearish_cross_happened = (prev[fast_ema] < prev[slow_ema] and third[fast_ema] > third[slow_ema]) or \
                                 (last[fast_ema] < last[slow_ema] and prev[fast_ema] > prev[slow_ema])
        
        # Condizione 2: Pullback verso le medie (prezzo chiude sopra la media veloce)
        is_pullback_short = last['close'] > last[fast_ema]

        if bearish_cross_happened and is_pullback_short and htf_trend == 'DOWNTREND':
            signals.append({'Asset': symbol, 'Timeframe': timeframe, 'Segnale': 'EMA Pullback Short', 'Prezzo': last['close'], 'Stop Loss': last['high'] * 1.02, 'Take Profit': last['close'] * 0.94, 'Score': 85, 'Strategia': 'Trend Following'})
            
    return signals
