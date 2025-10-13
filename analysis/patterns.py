# analysis/patterns.py - v4.0 (Arsenale Completo di Pattern Grafici e di Candele)
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

# --- PATTERN DI CANDELE ---

def analyze_candlestick_patterns(df: pd.DataFrame) -> dict:
    """Funzione aggregata che esegue tutti i check sui pattern di candele."""
    if len(df) < 3: return {"signal": "NEUTRAL", "score": 0}
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

    # Engulfing
    is_bullish_engulfing = c2['close'] < c2['open'] and c3['close'] > c3['open'] and c3['open'] < c2['close'] and c3['close'] > c2['open']
    if is_bullish_engulfing: return {"signal": "BULLISH", "score": 30, "details": "Bullish Engulfing"}
    is_bearish_engulfing = c2['close'] > c2['open'] and c3['close'] < c3['open'] and c3['open'] > c2['close'] and c3['close'] < c2['open']
    if is_bearish_engulfing: return {"signal": "BEARISH", "score": -30, "details": "Bearish Engulfing"}

    # Three White Soldiers / Three Black Crows
    is_three_soldiers = (c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] > c3['open'] and
                         c2['close'] > c1['close'] and c3['close'] > c2['close'] and
                         c2['open'] > c1['open'] and c2['open'] < c1['close'])
    if is_three_soldiers: return {"signal": "BULLISH", "score": 45, "details": "Three White Soldiers"}
    is_three_crows = (c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] < c3['open'] and
                      c2['close'] < c1['close'] and c3['close'] < c2['close'] and
                      c2['open'] < c1['open'] and c2['open'] > c1['close'])
    if is_three_crows: return {"signal": "BEARISH", "score": -45, "details": "Three Black Crows"}
    
    # Piercing Line / Dark Cloud Cover
    is_piercing = (c2['open'] > c2['close'] and c3['close'] > c3['open'] and 
                   c3['open'] < c2['low'] and c3['close'] > (c2['open'] + c2['close']) / 2)
    if is_piercing: return {"signal": "BULLISH", "score": 35, "details": "Piercing Line"}
    is_dark_cloud = (c2['open'] < c2['close'] and c3['close'] < c3['open'] and
                     c3['open'] > c2['high'] and c3['close'] < (c2['open'] + c2['close']) / 2)
    if is_dark_cloud: return {"signal": "BEARISH", "score": -35, "details": "Dark Cloud Cover"}
    
    return {"signal": "NEUTRAL", "score": 0}

# --- PATTERN GRAFICI ---

def analyze_double_top_bottom(df: pd.DataFrame) -> dict:
    lookback = 60
    if len(df) < lookback: return {"signal": "NEUTRAL", "score": 0}
    data = df.iloc[-lookback:]
    peaks, _ = find_peaks(data['high'], prominence=data['high'].std() / 2)
    troughs, _ = find_peaks(-data['low'], prominence=data['low'].std() / 2)

    if len(peaks) >= 2:
        p1_idx, p2_idx = peaks[-2], peaks[-1]
        p1_val, p2_val = data['high'].iloc[p1_idx], data['high'].iloc[p2_idx]
        if abs(p1_val - p2_val) / p1_val < 0.015:
            neckline_troughs = troughs[(troughs > p1_idx) & (troughs < p2_idx)]
            if len(neckline_troughs) > 0:
                neckline_val = data['low'].iloc[neckline_troughs[0]]
                if data['close'].iloc[-1] < neckline_val:
                    return {"signal": "BEARISH", "score": -50, "details": "Double Top Confirmed"}

    if len(troughs) >= 2:
        t1_idx, t2_idx = troughs[-2], troughs[-1]
        t1_val, t2_val = data['low'].iloc[t1_idx], data['low'].iloc[t2_idx]
        if abs(t1_val - t2_val) / t1_val < 0.015:
            neckline_peaks = peaks[(peaks > t1_idx) & (peaks < t2_idx)]
            if len(neckline_peaks) > 0:
                neckline_val = data['high'].iloc[neckline_peaks[0]]
                if data['close'].iloc[-1] > neckline_val:
                    return {"signal": "BULLISH", "score": 50, "details": "Double Bottom Confirmed"}

    return {"signal": "NEUTRAL", "score": 0}

def analyze_triangles(df: pd.DataFrame) -> dict:
    lookback = 90
    if len(df) < lookback: return {"signal": "NEUTRAL", "score": 0}
    data = df.iloc[-lookback:]
    peaks, _ = find_peaks(data['high'], prominence=data['high'].std() / 3, width=3)
    troughs, _ = find_peaks(-data['low'], prominence=data['low'].std() / 3, width=3)

    if len(peaks) >= 2 and len(troughs) >= 2:
        resistance_level = np.mean(data['high'].iloc[peaks[-2:]])
        is_flat_resistance = np.all(abs(data['high'].iloc[peaks[-2:]] - resistance_level) / resistance_level < 0.015)
        is_higher_lows = data['low'].iloc[troughs[-2:]].is_monotonic_increasing
        if is_flat_resistance and is_higher_lows and data['close'].iloc[-1] > resistance_level:
            return {"signal": "BULLISH", "score": 40, "details": "Ascending Triangle Breakout"}

    if len(peaks) >= 2 and len(troughs) >= 2:
        support_level = np.mean(data['low'].iloc[troughs[-2:]])
        is_flat_support = np.all(abs(data['low'].iloc[troughs[-2:]] - support_level) / support_level < 0.015)
        is_lower_highs = data['high'].iloc[peaks[-2:]].is_monotonic_decreasing
        if is_flat_support and is_lower_highs and data['close'].iloc[-1] < support_level:
            return {"signal": "BEARISH", "score": -40, "details": "Descending Triangle Breakdown"}
            
    return {"signal": "NEUTRAL", "score": 0}
