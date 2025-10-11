# analysis/strategy_vwap_rev.py (v4.0 - "Genetic-Aware")
import pandas as pd
import numpy as np
import pandas_ta as ta
from analysis.session_clock import TZ, SESSION_START
import config

def vwap_reversion_intraday(df: pd.DataFrame, asset: str, **kwargs):
    out = []
    
    # Logic to decide where to get params from (optimizer or config file)
    if 'k_atr' in kwargs: # Called from optimizer
        k_atr = kwargs['k_atr']
        rsi_len = kwargs['rsi_len']
        adx_threshold = kwargs['adx_threshold']
    elif asset in config.OPTIMIZED_PARAMS: # Called from backtester
        asset_params = config.OPTIMIZED_PARAMS[asset]
        k_atr = asset_params['k_atr']
        rsi_len = asset_params['rsi_len']
        adx_threshold = asset_params['adx_threshold']
    else: # Asset not in our genetic portfolio
        return out

    adx_len = 14
    if len(df) < 100: return out
    
    df = df.copy()
    if df.index.tz is None: df.index = df.index.tz_localize('UTC').tz_convert(TZ)
    else: df.index = df.index.tz_convert(TZ)

    df['date'] = df.index.date
    df['is_new_day'] = df['date'] != df['date'].shift(1)
    df['session_start_marker'] = (df.index.time >= SESSION_START) & (df.index.time < (pd.to_datetime(SESSION_START, format='%H:%M:%S') + pd.Timedelta(minutes=15)).time())
    df['is_session_start'] = df['is_new_day'] & df['session_start_marker']
    df['session_group'] = df['is_session_start'].cumsum()
    
    def session_vwap(group):
        tp = (group["high"] + group["low"] + group["close"]) / 3.0
        volume = group["volume"].replace(0, np.nan); vwap = (tp * volume).cumsum() / volume.cumsum()
        group['VWAP'] = vwap; return group
    
    df = df.groupby('session_group').apply(session_vwap, include_groups=False)
    
    df.ta.adx(length=adx_len, append=True)
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.atr(length=config.ATR_PERIOD, append=True)
    
    df.dropna(inplace=True);
    if len(df) < 2: return out

    adx_col = f"ADX_{adx_len}"; rsi_col = f"RSI_{rsi_len}"; atr_col = f"ATRr_{config.ATR_PERIOD}"
    T = df.iloc[-2]; T1 = df.iloc[-1]

    if 'VWAP' not in T1 or pd.isna(T1['VWAP']): return out
    if T1[adx_col] >= adx_threshold: return out

    dist_atr = abs(T1["close"] - T1["VWAP"]) / max(1e-9, T1[atr_col])

    if (T1["close"] < T1["VWAP"]) and (dist_atr >= k_atr) and (T1[rsi_col] <= 40) and (T1["close"] > T["close"]):
        entry = float(T1["close"]); sl = float(T1["low"] - 1.2 * T1[atr_col]); tp = float(T1["VWAP"])
        out.append({"side": "Long", "entry_price": entry, "sl": sl, "tp": tp, "score": 75, "strategy": "VWAP-Reversion"})

    if (T1["close"] > T1["VWAP"]) and (dist_atr >= k_atr) and (T1[rsi_col] >= 60) and (T1["close"] < T["close"]):
        entry = float(T1["close"]); sl = float(T1["high"] + 1.2 * T1[atr_col]); tp = float(T1["VWAP"])
        out.append({"side": "Short", "entry_price": entry, "sl": sl, "tp": tp, "score": 75, "strategy": "VWAP-Reversion"})

    return out
