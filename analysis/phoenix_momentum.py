# analysis/phoenix_momentum.py
# Motore Trend Following, ora in un modulo separato.
import pandas as pd
import pandas_ta as ta
import config

def phoenix_momentum(df):
    out = []
    df = df.copy()
    adx_col, rsi_col, sma_col = f"ADX_{config.ADX_PERIOD}", f"RSI_{config.RSI_PERIOD}", "SMA_50"
    df.ta.sma(length=50, append=True)
    if len(df) < 51: return out
    T, T1 = df.iloc[-2], df.iloc[-1]
    if pd.isna(T1[adx_col]) or pd.isna(T1[sma_col]): return out
    if T1[adx_col] > 20:
        if T1['close'] > T1[sma_col]:
            if (T[rsi_col] < 50 and T1[rsi_col] > 50) or (T[rsi_col] < 45 and T1[rsi_col] > 55):
                entry = T1['close']; atr = T1[f"ATRr_{config.ATR_PERIOD}"]; sl = T1['low'] - 1.5 * atr; tp = entry + 2.5 * atr
                out.append({"side": "Long", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": 75, "strategy": "Momentum"})
    return out