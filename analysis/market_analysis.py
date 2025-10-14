# analysis/market_analysis.py - v13.0 (Filtri di Qualità per i Segnali)
import pandas as pd
import pandas_ta as ta
import logging
import json

import database as db

def find_pullback_signal(symbol: str, data_1h: pd.DataFrame, params: dict):
    """
    Funzione core v13.0. Analizza i dati con filtri di qualità migliorati.
    1. Cerca un pullback "qualificato" (rottura della EMA veloce).
    2. Attende una candela di "conferma" del momentum.
    """
    ema_slow = params.get('ema_slow', 200)
    ema_fast = params.get('ema_fast', 20)
    atr_len = params.get('atr_len', 14)
    ema_slope_min = params.get('ema_slope_min', 0.0)
    
    atr_col_name = f'ATR_{atr_len}'

    if len(data_1h) < max(ema_slow, atr_len) + 10:
        return None

    df = data_1h.copy()
    df.ta.ema(length=ema_fast, append=True, col_names=f'EMA_{ema_fast}')
    df.ta.ema(length=ema_slow, append=True, col_names=f'EMA_{ema_slow}')
    df.ta.atr(length=atr_len, col_names=atr_col_name, append=True)
    df['EMA_SLOW_SLOPE'] = df[f'EMA_{ema_slow}'].diff()

    # Usiamo le ultime 3 candele per la nostra logica
    # setup_candle: la candela che fa il pullback
    # confirmation_candle: la candela che conferma la ripartenza
    # current_candle: la candela attuale, non la usiamo per l'analisi ma per il timestamp
    setup_candle = df.iloc[-3]
    confirmation_candle = df.iloc[-2]
    current_candle = df.iloc[-1]

    # --- Controlli di base ---
    if any(pd.isna(c[atr_col_name]) for c in [setup_candle, confirmation_candle]): return None
    if any(c[atr_col_name] == 0 for c in [setup_candle, confirmation_candle]): return None

    # --- Definizione del Trend ---
    is_uptrend = (setup_candle[f'EMA_{ema_slow}'] > df.iloc[-10][f'EMA_{ema_slow}']) and (setup_candle['EMA_SLOW_SLOPE'] > ema_slope_min)
    is_downtrend = (setup_candle[f'EMA_{ema_slow}'] < df.iloc[-10][f'EMA_{ema_slow}']) and (setup_candle['EMA_SLOW_SLOPE'] < -ema_slope_min)

    final_signal, entry_price, stop_loss, take_profit = None, None, None, None

    # --- Logica per Segnale LONG ---
    if is_uptrend:
        # 1. Filtro Pullback Qualificato: la candela di setup deve chiudere sotto la EMA veloce
        is_qualified_pullback = setup_candle['close'] < setup_candle[f'EMA_{ema_fast}']
        # 2. Filtro Conferma Momentum: la candela successiva deve essere verde e rompere il massimo del pullback
        is_momentum_confirmed = confirmation_candle['close'] > confirmation_candle['open'] and \
                                confirmation_candle['high'] > setup_candle['high']

        if is_qualified_pullback and is_momentum_confirmed:
            entry_price, stop_loss, take_profit = calculate_long_trade(confirmation_candle, setup_candle, params)
            if entry_price: final_signal = "LONG"

    # --- Logica per Segnale SHORT ---
    elif is_downtrend:
        # 1. Filtro Pullback Qualificato: la candela di setup deve chiudere sopra la EMA veloce
        is_qualified_pullback = setup_candle['close'] > setup_candle[f'EMA_{ema_fast}']
        # 2. Filtro Conferma Momentum: la candela successiva deve essere rossa e rompere il minimo del pullback
        is_momentum_confirmed = confirmation_candle['close'] < confirmation_candle['open'] and \
                                confirmation_candle['low'] < setup_candle['low']

        if is_qualified_pullback and is_momentum_confirmed:
            entry_price, stop_loss, take_profit = calculate_short_trade(confirmation_candle, setup_candle, params)
            if entry_price: final_signal = "SHORT"

    if final_signal:
        mgmt_data = { "partial_take": params.get('partial_take', True), "trail_type": params.get('trail_type', 'atr') }
        return {
            "timestamp": current_candle['timestamp'], "symbol": symbol, "signal_type": final_signal,
            "entry_price": round(entry_price, 6), "stop_loss": round(stop_loss, 6), "take_profit": round(take_profit, 6),
            "mgmt_details": json.dumps(mgmt_data), "strategy": "Optimized Pullback v13"
        }
    return None

def calculate_long_trade(confirmation_candle, setup_candle, params):
    atr_mult_sl = params.get('atr_mult_sl', 1.5) # Aumentiamo un po' lo spazio per respirare
    rr_ratio = params.get('rr_ratio', 2.0)
    atr_len = params.get('atr_len', 14)
    atr_col_name = f'ATR_{atr_len}'

    entry_price = confirmation_candle['high']
    stop_loss = setup_candle['low'] - (confirmation_candle[atr_col_name] * (atr_mult_sl - 1.0))
    
    if stop_loss >= entry_price: return None, None, None
    
    risk = entry_price - stop_loss
    take_profit = entry_price + (risk * rr_ratio)
        
    return entry_price, stop_loss, take_profit

def calculate_short_trade(confirmation_candle, setup_candle, params):
    atr_mult_sl = params.get('atr_mult_sl', 1.5)
    rr_ratio = params.get('rr_ratio', 2.0)
    atr_len = params.get('atr_len', 14)
    atr_col_name = f'ATR_{atr_len}'

    entry_price = confirmation_candle['low']
    stop_loss = setup_candle['high'] + (confirmation_candle[atr_col_name] * (atr_mult_sl - 1.0))
    
    if stop_loss <= entry_price: return None, None, None

    risk = stop_loss - entry_price
    take_profit = entry_price - (risk * rr_ratio)
        
    return entry_price, stop_loss, take_profit

def run_pullback_analysis(symbol: str, data_1h: pd.DataFrame, params: dict):
    """ Wrapper per il bot live. """
    info = find_pullback_signal(symbol, data_1h, params)
    if info:
        if db.check_recent_signal(symbol, info['signal_type']):
            logging.info(f"Segnale per {symbol} ({info['signal_type']}) già registrato. Salto.")
            return None
        db.save_signal(info)
        logging.info(f"✅ SEGNALE {info['signal_type']} {info['symbol']} a {info['entry_price']} | SL {info['stop_loss']} | TP {info['take_profit']}")
        return info
    logging.info(f"Nessuna opportunità valida (filtri/validazioni) per {symbol}.")
    return None
