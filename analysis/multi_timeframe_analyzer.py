# analysis/multi_timeframe_analyzer.py (Patch 1)
import pandas as pd
import pandas_ta as ta
from analysis.phoenix_signal_v91 import phoenix_signal_v91
from analysis.phoenix_momentum import phoenix_momentum

def _prepare_indicators(df, adx_len=14, rsi_len=14, atr_len=14):
    df.ta.adx(length=adx_len, append=True)
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.atr(length=atr_len, append=True)
    df.dropna(inplace=True)
    return df

def analyze_single_timeframe(symbol, timeframe, data_client, config):
    df = data_client.get_klines(symbol, timeframe, config.DATA_SOURCE, limit=500)
    if df is None or df.empty or len(df) < 50: return None
    df = _prepare_indicators(df, config.ADX_PERIOD, config.RSI_PERIOD, config.ATR_PERIOD)
    signals = phoenix_signal_v91(df)
    if not signals: signals = phoenix_momentum(df)
    if not signals: return None
    best = max(signals, key=lambda s: s.get("score", 0))
    best["timeframe"] = timeframe
    return best

def analyze_multi_timeframes(symbol, data_client, config):
    labels = {"1d": "Daily", "4h": "4H", "15m": "15m"}
    results = {}
    for tf in config.ACTIVE_TIMEFRAMES:
        best = analyze_single_timeframe(symbol, tf, data_client, config)
        if best: results[labels[tf]] = best
    coherence = None
    if "Daily" in results and "4H" in results:
        if results["Daily"]["side"] == results["4H"]["side"]: coherence = "HIGH"
    elif "4H" in results and "15m" in results:
        if results["4H"]["side"] == results["15m"]["side"]: coherence = "MEDIUM"
    return {"symbol": symbol, "signals": results, "coherence": coherence}