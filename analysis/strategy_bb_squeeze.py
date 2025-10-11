# analysis/strategy_bb_squeeze.py
import pandas as pd
import pandas_ta as ta
import config

def bollinger_squeeze_breakout(df_trigger: pd.DataFrame, bias: str):
    """
    Strategia che cerca un breakout da una "compressione" delle Bande di Bollinger.
    Opera solo nella direzione del bias fornito dal contesto.
    """
    out = []
    if len(df_trigger) < config.BBANDS_PERIOD:
        return out

    df = df_trigger.copy()
    
    # Calcola le Bande di Bollinger e la loro ampiezza
    df.ta.bbands(length=config.BBANDS_PERIOD, std=config.BBANDS_STD, append=True)
    # Aggiungi anche l'ATR per il calcolo del TP/SL
    df.ta.atr(length=config.ATR_PERIOD, append=True)

    bbw_col = f"BBW_{config.BBANDS_PERIOD}_{config.BBANDS_STD:.1f}"
    bbl_col = f"BBL_{config.BBANDS_PERIOD}_{config.BBANDS_STD:.1f}"
    bbu_col = f"BBU_{config.BBANDS_PERIOD}_{config.BBANDS_STD:.1f}"

    if bbw_col not in df.columns:
        return out

    # Trova il punto di minima ampiezza delle bande nelle ultime N candele
    squeeze_window = 40
    df['squeeze_point'] = df[bbw_col].rolling(squeeze_window).min()
    
    df.dropna(inplace=True)
    if len(df) < 2:
        return out

    T = df.iloc[-2]  # Barra di setup
    T1 = df.iloc[-1] # Barra di trigger

    # Condizione di Squeeze: l'ampiezza attuale è vicina al minimo recente
    is_in_squeeze = T[bbw_col] <= T['squeeze_point'] * 1.1

    if is_in_squeeze:
        # SETUP LONG: Se il bias è rialzista e rompiamo sopra la banda superiore
        if bias == 'BULLISH' and T['close'] < T[bbu_col] and T1['close'] > T[bbu_col]:
            entry = float(T1['close'])
            sl = float(T1[bbl_col]) # Stop loss sulla banda inferiore
            atr = T1.get(f"ATRr_{config.ATR_PERIOD}", (entry - sl) * 0.5)
            tp = float(entry + 2.0 * atr)
            out.append({
                "side": "Long", "entry_price": entry, "sl": sl, "tp": tp,
                "score": 80, "strategy": "BB-Squeeze-Breakout"
            })

        # SETUP SHORT: Se il bias è ribassista e rompiamo sotto la banda inferiore
        if bias == 'BEARISH' and T['close'] > T[bbl_col] and T1['close'] < T[bbl_col]:
            entry = float(T1['close'])
            sl = float(T1[bbu_col]) # Stop loss sulla banda superiore
            atr = T1.get(f"ATRr_{config.ATR_PERIOD}", (sl - entry) * 0.5)
            tp = float(entry - 2.0 * atr)
            out.append({
                "side": "Short", "entry_price": entry, "sl": sl, "tp": tp,
                "score": 80, "strategy": "BB-Squeeze-Breakout"
            })
            
    return out
