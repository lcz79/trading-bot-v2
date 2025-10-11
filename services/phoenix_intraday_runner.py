# analysis/strategy_orb.py
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time
from analysis.session_clock import TZ, SESSION_START

def opening_range_breakout(df: pd.DataFrame, *, adx_len=14, vol_ma=20, or_minutes=30):
    out = []
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return out

    # Assicurati che l'indice sia localizzato correttamente
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert(TZ)
    else:
        df.index = df.index.tz_convert(TZ)

    df = df.copy()
    df.ta.adx(length=adx_len, append=True)
    adx_col = f"ADX_{adx_len}"
    df["vol_ma"] = df["volume"].rolling(vol_ma).mean()
    df.dropna(inplace=True)
    if len(df) < 1:
        return out

    # Determina l'Opening Range (OR) della giornata corrente
    today = datetime.now(TZ).date()
    or_start = datetime.combine(today, SESSION_START, TZ)
    or_end   = or_start.replace(minute=SESSION_START.minute + or_minutes)

    # Controlla se siamo dopo la finestra dell'OR
    T1 = df.iloc[-1]
    if T1.name < or_end:
        return out # Non è ancora ora di cercare breakout

    or_df = df.loc[(df.index >= or_start) & (df.index < or_end)]
    if or_df.empty:
        return out

    or_high = or_df["high"].max()
    or_low  = or_df["low"].min()
    or_range = or_high - or_low
    if or_range <= 0:
        return out

    # SETUP LONG BREAKOUT
    if (T1["close"] > or_high) and (T1[adx_col] >= 18) and (T1["volume"] > (T1["vol_ma"] or 0)):
        entry = float(T1["close"])
        sl    = float(or_high) # Stop loss sul massimo del range
        tp    = float(entry + 1.2 * or_range)
        out.append({
            "side":"Long", "entry_price":entry, "sl":sl, "tp":tp,
            "score": 76, "strategy":"OpeningRangeBreakout"
        })

    # SETUP SHORT BREAKOUT
    if (T1["close"] < or_low) and (T1[adx_col] >= 18) and (T1["volume"] > (T1["vol_ma"] or 0)):
        entry = float(T1["close"])
        sl    = float(or_low) # Stop loss sul minimo del range
        tp    = float(entry - 1.2 * or_range)
        out.append({
            "side":"Short", "entry_price":entry, "sl":sl, "tp":tp,
            "score": 76, "strategy":"OpeningRangeBreakout"
        })

    return out