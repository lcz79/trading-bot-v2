# analysis/market_analysis.py - v12.0 (Refactoring per Backtesting)
import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, timezone
import json

import database as db

def find_pullback_signal(symbol: str, data_1h: pd.DataFrame, params: dict):
    """
    Funzione core che analizza i dati e restituisce un dizionario con i dettagli del segnale,
    o None se non viene trovata alcuna opportunità. NON ha effetti collaterali (non salva su DB).
    """
    ema_slow = params.get('ema_slow', 200)
    ema_fast = params.get('ema_fast', 20)
    rr_ratio = params.get('rr_ratio', 2.0)
    ema_slope_min= params.get('ema_slope_min', 0.0)
    atr_len = params.get('atr_len', 14)
    atr_mult_sl = params.get('atr_mult_sl', 1.2)
    atr_mult_tp = params.get('atr_mult_tp', None)
    use_stop_entry = params.get('use_stop_entry', True)
    partial_take = params.get('partial_take', True)
    trail_type = params.get('trail_type', 'atr')
    trail_atr_mult = params.get('trail_atr_mult', 1.0)
    setup_timeout_bars = params.get('setup_timeout_bars', 3)
    
    atr_col_name = f'ATR_{atr_len}'

    if len(data_1h) < max(ema_slow, atr_len) + 5:
        return None

    df = data_1h.copy()
    df.ta.ema(length=ema_fast, append=True)
    df.ta.ema(length=ema_slow, append=True)
    df.ta.atr(length=atr_len, col_names=atr_col_name, append=True)
    df['EMA_SLOW_SLOPE'] = df[f'EMA_{ema_slow}'].diff()

    current = df.iloc[-1]
    prev    = df.iloc[-2]
    prev2   = df.iloc[-3]

    is_uptrend   = (prev['close'] > prev[f'EMA_{ema_slow}']) and (prev['EMA_SLOW_SLOPE'] > ema_slope_min)
    is_downtrend = (prev['close'] < prev[f'EMA_{ema_slow}']) and (prev['EMA_SLOW_SLOPE'] < -ema_slope_min)

    if atr_col_name not in prev.index or pd.isna(prev[atr_col_name]) or prev[atr_col_name] == 0:
        return None
        
    atr_prev = prev[atr_col_name]
    is_pullback_to_buy  = (prev['low'] <= prev[f'EMA_{ema_fast}']) and ((prev['high'] - prev['low']) >= 0.6 * atr_prev)
    is_pullback_to_sell = (prev['high'] >= prev[f'EMA_{ema_fast}']) and ((prev['high'] - prev['low']) >= 0.6 * atr_prev)

    final_signal, entry_price, stop_loss, take_profit = None, None, None, None
    details = []

    if is_uptrend and is_pullback_to_buy:
        entry_price, stop_loss, take_profit = calculate_long_trade(current, prev, prev2, atr_prev, params)
        if entry_price: final_signal = "LONG"

    elif is_downtrend and is_pullback_to_sell:
        entry_price, stop_loss, take_profit = calculate_short_trade(current, prev, prev2, atr_prev, params)
        if entry_price: final_signal = "SHORT"

    if final_signal:
        mgmt_data = {
            "partial_take": partial_take, "partial_at_R": 1.0, "move_to_be_at_R": 1.0,
            "trail_type": trail_type, "trail_atr_mult": trail_atr_mult, "setup_timeout_bars": setup_timeout_bars
        }
        return {
            "timestamp": current['timestamp'], "symbol": symbol, "signal_type": final_signal,
            "entry_price": round(entry_price, 6), "stop_loss": round(stop_loss, 6), "take_profit": round(take_profit, 6),
            "mgmt_details": json.dumps(mgmt_data),
            "strategy": "Optimized Pullback v11"
        }
    return None

def calculate_long_trade(current, prev, prev2, atr_prev, params):
    use_stop_entry = params.get('use_stop_entry', True)
    rr_ratio = params.get('rr_ratio', 2.0)
    atr_mult_sl = params.get('atr_mult_sl', 1.2)
    atr_mult_tp = params.get('atr_mult_tp', None)

    entry_price = None
    if use_stop_entry:
        entry_price = float(prev['high'])
    elif current['close'] > current['open']:
        entry_price = float(current['close'])
    
    if not entry_price: return None, None, None

    long_sl_candidate = min(prev['low'], prev2['low'])
    stop_loss = long_sl_candidate - atr_mult_sl * atr_prev
    if stop_loss >= entry_price: return None, None, None

    risk = entry_price - stop_loss
    if atr_mult_tp is not None:
        take_profit = entry_price + atr_mult_tp * atr_prev
    else:
        take_profit = entry_price + rr_ratio * risk
        
    return entry_price, stop_loss, take_profit

def calculate_short_trade(current, prev, prev2, atr_prev, params):
    use_stop_entry = params.get('use_stop_entry', True)
    rr_ratio = params.get('rr_ratio', 2.0)
    atr_mult_sl = params.get('atr_mult_sl', 1.2)
    atr_mult_tp = params.get('atr_mult_tp', None)

    entry_price = None
    if use_stop_entry:
        entry_price = float(prev['low'])
    elif current['close'] < current['open']:
        entry_price = float(current['close'])

    if not entry_price: return None, None, None

    short_sl_candidate = max(prev['high'], prev2['high'])
    stop_loss = short_sl_candidate + atr_mult_sl * atr_prev
    if stop_loss <= entry_price: return None, None, None

    risk = stop_loss - entry_price
    if atr_mult_tp is not None:
        take_profit = entry_price - atr_mult_tp * atr_prev
    else:
        take_profit = entry_price - rr_ratio * risk
        
    return entry_price, stop_loss, take_profit


def run_pullback_analysis(symbol: str, data_1h: pd.DataFrame, params: dict):
    """
    Wrapper che usa find_pullback_signal e salva il risultato sul DB.
    Usato dal bot live (etl_service).
    """
    info = find_pullback_signal(symbol, data_1h, params)
    
    if info:
        if db.check_recent_signal(symbol, info['signal_type']):
            logging.info(f"Segnale per {symbol} ({info['signal_type']}) già registrato di recente. Salto.")
            return None

        db.save_signal(info)
        logging.info(f"✅ SEGNALE {info['signal_type']} {info['symbol']} a {info['entry_price']} | SL {info['stop_loss']} | TP {info['take_profit']}")
        return info
    
    logging.info(f"Nessuna opportunità valida (filtri/validazioni) per {symbol}.")
    return None
