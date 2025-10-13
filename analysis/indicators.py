# analysis/indicators.py - v3.2 (Punteggi Breakout Potenziati)
import pandas as pd
import pandas_ta as ta
import logging

# --- LOGICHE DI TRADING CON PUNTEGGI RICALIBRATI ---

def analyze_price_channel_tf(df: pd.DataFrame, period: int = 20) -> dict:
    """Logica Trend Following (TF) con punteggio aumentato."""
    try:
        if len(df) < period: return {"signal": "NEUTRAL", "score": 0}
        lookback_df = df.iloc[-(period+1):-1]
        upper_band, lower_band = lookback_df['high'].max(), lookback_df['low'].min()
        last_close = df['close'].iloc[-1]
        # PUNTEGGIO AUMENTATO DA 40 a 50
        if last_close > upper_band:
            return {"signal": "BULLISH", "score": 50, "details": f"TF Breakout Long (Canale {period}gg)"}
        if last_close < lower_band:
            return {"signal": "BEARISH", "score": -50, "details": f"TF Breakout Short (Canale {period}gg)"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e:
        logging.warning(f"Errore analisi Price Channel TF: {e}"); return {"signal": "NEUTRAL", "score": 0}

def analyze_mean_reverting_mr(df: pd.DataFrame, session_bars: int = 24) -> dict:
    """Logica Mean Reverting (MR)."""
    try:
        if len(df) < session_bars: return {"signal": "NEUTRAL", "score": 0}
        prev_session = df.iloc[-(session_bars+1):-1]
        prev_high, prev_low = prev_session['high'].max(), prev_session['low'].min()
        last_close = df['close'].iloc[-1]
        tolerance = (prev_high - prev_low) * 0.1
        if abs(last_close - prev_low) < tolerance:
            return {"signal": "BULLISH", "score": 25, "details": "MR Buy (vicino minimo sessione prec.)"}
        if abs(last_close - prev_high) < tolerance:
            return {"signal": "BEARISH", "score": -25, "details": "MR Sell (vicino massimo sessione prec.)"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e:
        logging.warning(f"Errore analisi Mean Reverting MR: {e}"); return {"signal": "NEUTRAL", "score": 0}

def analyze_breakout_brk(df: pd.DataFrame, session_bars: int = 24) -> dict:
    """Logica Breakout (BRK) con punteggio aumentato."""
    try:
        if len(df) < session_bars: return {"signal": "NEUTRAL", "score": 0}
        prev_session = df.iloc[-(session_bars+1):-1]
        prev_high, prev_low = prev_session['high'].max(), prev_session['low'].min()
        last_close = df['close'].iloc[-1]
        # PUNTEGGIO AUMENTATO DA 45 a 55
        if last_close > prev_high:
            return {"signal": "BULLISH", "score": 55, "details": "BRK Long (Rottura massimo sessione prec.)"}
        if last_close < prev_low:
            return {"signal": "BEARISH", "score": -55, "details": "BRK Short (Rottura minimo sessione prec.)"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e:
        logging.warning(f"Errore analisi Breakout BRK: {e}"); return {"signal": "NEUTRAL", "score": 0}

# --- INDICATORI STANDARD (con FIX per ICHIMOKU) ---
# ... (il resto del file rimane identico) ...
def analyze_ma_cross(df: pd.DataFrame) -> dict:
    try:
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        if 'SMA_50' not in df.columns or 'SMA_200' not in df.columns or len(df) < 201: return {"signal": "NEUTRAL", "score": 0}
        last, prev = df.iloc[-1], df.iloc[-2]
        if prev['SMA_50'] < prev['SMA_200'] and last['SMA_50'] > last['SMA_200']:
            return {"signal": "BULLISH", "score": 50, "details": "Golden Cross (SMA 50/200)"}
        if prev['SMA_50'] > prev['SMA_200'] and last['SMA_50'] < last['SMA_200']:
            return {"signal": "BEARISH", "score": -50, "details": "Death Cross (SMA 50/200)"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e: logging.warning(f"Errore MA Cross: {e}"); return {"signal": "NEUTRAL", "score": 0}

def analyze_ichimoku(df: pd.DataFrame) -> dict:
    try:
        df.ta.ichimoku(append=True)
        required_cols = ['ISA_9', 'ISB_26', 'ITS_9', 'IKS_26']
        if not all(col in df.columns for col in required_cols) or len(df) < 2:
            return {"signal": "NEUTRAL", "score": 0}
        score, details = 0, []
        last, prev = df.iloc[-1], df.iloc[-2]
        if prev['ITS_9'] < prev['IKS_26'] and last['ITS_9'] > last['IKS_26']:
            score += 15; details.append("Incrocio T/K Bullish")
        elif prev['ITS_9'] > prev['IKS_26'] and last['ITS_9'] < last['IKS_26']:
            score -= 15; details.append("Incrocio T/K Bearish")
        if last['close'] > last['ISA_9'] and last['close'] > last['ISB_26']:
            score += 25; details.append("Prezzo > Nuvola")
        elif last['close'] < last['ISA_9'] and last['close'] < last['ISB_26']:
            score -= 25; details.append("Prezzo < Nuvola")
        if not details: return {"signal": "NEUTRAL", "score": 0}
        return {"signal": "BULLISH" if score > 0 else "BEARISH", "score": score, "details": " | ".join(details)}
    except Exception as e:
        logging.warning(f"Errore Ichimoku: {e}"); return {"signal": "NEUTRAL", "score": 0}

def analyze_macd(df: pd.DataFrame) -> dict:
    try:
        macd = df.ta.macd(fast=12, slow=26, signal=9, append=True)
        if macd is None or len(macd) < 2: return {"signal": "NEUTRAL", "score": 0}
        last, prev = macd.iloc[-1], macd.iloc[-2]
        if prev['MACD_12_26_9'] < prev['MACDs_12_26_9'] and last['MACD_12_26_9'] > last['MACDs_12_26_9']:
            return {"signal": "BULLISH", "score": 20, "details": "MACD Crossover Bullish"}
        elif prev['MACD_12_26_9'] > prev['MACDs_12_26_9'] and last['MACD_12_26_9'] < last['MACDs_12_26_9']:
            return {"signal": "BEARISH", "score": -20, "details": "MACD Crossover Bearish"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e: logging.warning(f"Errore MACD: {e}"); return {"signal": "NEUTRAL", "score": 0}

def analyze_rsi(df: pd.DataFrame) -> dict:
    try:
        df.ta.rsi(length=14, append=True)
        if 'RSI_14' not in df.columns: return {"signal": "NEUTRAL", "score": 0}
        last_rsi = df['RSI_14'].iloc[-1]
        if last_rsi > 75: return {"signal": "BEARISH", "score": -15, "details": f"RSI Ipercomprato ({last_rsi:.1f})"}
        if last_rsi < 25: return {"signal": "BULLISH", "score": 15, "details": f"RSI Ipervenduto ({last_rsi:.1f})"}
        return {"signal": "NEUTRAL", "score": 0}
    except Exception as e: logging.warning(f"Errore RSI: {e}"); return {"signal": "NEUTRAL", "score": 0}
