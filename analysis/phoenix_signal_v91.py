# analysis/phoenix_signal_v91.py
# Motore Mean Reversion, ora in un modulo separato.
import pandas as pd
import pandas_ta as ta
import numpy as np  # <--- CORREZIONE: Aggiunto l'import mancante
import config

def phoenix_signal_v91(df):
    out = []
    df = df.copy()
    rsi_col, atr_col = f"RSI_{config.RSI_PERIOD}", f"ATRr_{config.ATR_PERIOD}"
    
    # Calcolo Z-Score del volume
    vol_ma = df["volume"].rolling(20).mean()
    vol_std = df["volume"].rolling(20).std(ddof=0)
    # Questa riga usa np.nan, che causava l'errore
    df["vol_z"] = ((df["volume"] - vol_ma) / vol_std.replace(0, np.nan)).fillna(0.0)
    
    if len(df) < 5: return out
    T, T1 = df.iloc[-2], df.iloc[-1]
    
    if pd.isna(T[rsi_col]): return out
    
    # SETUP LONG
    setup_rsi = T[rsi_col] <= config.RSI_LOW
    setup_vol = T["vol_z"] >= config.VOLUME_Z_SCORE_MIN
    if setup_rsi and setup_vol:
        confirm = (T1["close"] > T["close"] * 1.005)
        if confirm:
            entry = T1["close"]; sl = T["low"] - config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry + config.TP_ATR_MULTIPLIER * T[atr_col]
            out.append({"side": "Long", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": 88, "strategy": "MeanReversion"})
            
    # SETUP SHORT
    setup_rsi_short = T[rsi_col] >= config.RSI_HIGH
    if setup_rsi_short and setup_vol:
        confirm_short = (T1["close"] < T["close"] * 0.995)
        if confirm_short:
            entry = T1["close"]; sl = T["high"] + config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry - config.TP_ATR_MULTIPLIER * T[atr_col]
            out.append({"side": "Short", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": 88, "strategy": "MeanReversion"})
    return out
