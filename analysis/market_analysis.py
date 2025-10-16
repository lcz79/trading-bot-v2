# analysis/market_analysis.py - v14.0 (Strategy Building Blocks)
import pandas as pd
import pandas_ta as ta
import logging
import json

import database as db

# ==============================================================================
# --- LIBRERIA DI BLOCCHI LOGICI (I nostri "LEGO") ---
# ==============================================================================

def add_indicators(df, params):
    """Aggiunge al DataFrame tutti gli indicatori necessari per una strategia."""
    df.ta.ema(length=params['ema_fast'], append=True, col_names=f"EMA_{params['ema_fast']}")
    df.ta.ema(length=params['ema_slow'], append=True, col_names=f"EMA_{params['ema_slow']}")
    df.ta.atr(length=params['atr_len'], append=True, col_names=f"ATR_{params['atr_len']}")
    df['EMA_SLOW_SLOPE'] = df[f"EMA_{params['ema_slow']}"].diff()
    return df

def check_trend_condition(df, params):
    """
    Controlla la condizione del trend basandosi sulla pendenza della EMA lenta.
    Restituisce: 'UP', 'DOWN', o 'NONE'.
    """
    setup_candle = df.iloc[-3]
    ema_slope_min = params.get('ema_slope_min', 0.0)

    is_uptrend = (setup_candle[f"EMA_{params['ema_slow']}"] > df.iloc[-10][f"EMA_{params['ema_slow']}"]) and \
                 (setup_candle['EMA_SLOW_SLOPE'] > ema_slope_min)
    is_downtrend = (setup_candle[f"EMA_{params['ema_slow']}"] < df.iloc[-10][f"EMA_{params['ema_slow']}"]) and \
                   (setup_candle['EMA_SLOW_SLOPE'] < -ema_slope_min)

    if is_uptrend: return 'UP'
    if is_downtrend: return 'DOWN'
    return 'NONE'

def check_pullback_entry_condition(df, trend, params):
    """
    Controlla la condizione di entrata specifica della strategia "Pullback v13".
    Restituisce: True se la condizione è soddisfatta, altrimenti False.
    """
    setup_candle = df.iloc[-3]
    confirmation_candle = df.iloc[-2]

    if trend == 'UP':
        is_qualified_pullback = setup_candle['close'] < setup_candle[f"EMA_{params['ema_fast']}"]
        is_momentum_confirmed = confirmation_candle['close'] > confirmation_candle['open'] and \
                                confirmation_candle['high'] > setup_candle['high']
        return is_qualified_pullback and is_momentum_confirmed
    
    if trend == 'DOWN':
        is_qualified_pullback = setup_candle['close'] > setup_candle[f"EMA_{params['ema_fast']}"]
        is_momentum_confirmed = confirmation_candle['close'] < confirmation_candle['open'] and \
                                confirmation_candle['low'] < setup_candle['low']
        return is_qualified_pullback and is_momentum_confirmed
    
    return False

def calculate_sl_tp(df, direction, params):
    """Calcola entry, stop loss e take profit basati sulla logica della strategia."""
    confirmation_candle = df.iloc[-2]
    setup_candle = df.iloc[-3]
    atr_col_name = f"ATR_{params['atr_len']}"
    rr_ratio = params.get('rr_ratio', 3.0) # Default più aggressivo
    atr_mult_sl = params.get('atr_mult_sl', 2.5) # Default più ampio

    if direction == 'LONG':
        entry_price = confirmation_candle['high']
        stop_loss = setup_candle['low'] - (confirmation_candle[atr_col_name] * (atr_mult_sl - 1.0))
        if stop_loss >= entry_price: return None, None, None
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * rr_ratio)
        return entry_price, stop_loss, take_profit
    
    if direction == 'DOWN': # Corretto da 'SHORT' a 'DOWN' per coerenza
        entry_price = confirmation_candle['low']
        stop_loss = setup_candle['high'] + (confirmation_candle[atr_col_name] * (atr_mult_sl - 1.0))
        if stop_loss <= entry_price: return None, None, None
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * rr_ratio)
        return entry_price, stop_loss, take_profit

    return None, None, None

# ... (Le altre funzioni wrapper non sono necessarie qui perché il tuo generatore è autonomo)
