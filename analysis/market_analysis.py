# analysis/market_analysis.py - v11.2 (Fix per nome colonna ATR)
import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, timezone
import json

import database as db

def run_pullback_analysis(symbol: str, data_1h: pd.DataFrame, params: dict):
    ema_slow     = params.get('ema_slow', 200)
    ema_fast     = params.get('ema_fast', 20)
    rr_ratio     = params.get('rr_ratio', 2.0)
    ema_slope_min= params.get('ema_slope_min', 0.0)
    atr_len      = params.get('atr_len', 14)
    atr_mult_sl  = params.get('atr_mult_sl', 1.2)
    atr_mult_tp  = params.get('atr_mult_tp', None)
    use_stop_entry = params.get('use_stop_entry', True)
    partial_take = params.get('partial_take', True)
    trail_type   = params.get('trail_type', 'atr')
    trail_atr_mult = params.get('trail_atr_mult', 1.0)
    setup_timeout_bars = params.get('setup_timeout_bars', 3)

    if len(data_1h) < max(ema_slow, atr_len) + 5:
        logging.info(f"Dati insufficienti per {symbol}.")
        return None

    df = data_1h.copy()
    df.ta.ema(length=ema_fast, append=True)
    df.ta.ema(length=ema_slow, append=True)
    
    # --- MODIFICA CHIAVE ---
    # Forziamo il nome della colonna per essere sicuri al 100%
    df.ta.atr(length=atr_len, col_names=f'ATR_{atr_len}', append=True)
    
    df['EMA_SLOW_SLOPE'] = df[f'EMA_{ema_slow}'].diff()

    current = df.iloc[-1]
    prev    = df.iloc[-2]
    prev2   = df.iloc[-3]

    is_uptrend   = (prev['close'] > prev[f'EMA_{ema_slow}']) and (df.iloc[-2]['EMA_SLOW_SLOPE'] > ema_slope_min)
    is_downtrend = (prev['close'] < prev[f'EMA_{ema_slow}']) and (df.iloc[-2]['EMA_SLOW_SLOPE'] < -ema_slope_min)

    # Ora siamo sicuri che la colonna si chiami esattamente 'ATR_14' (o qualsiasi sia atr_len)
    atr_col_name = f'ATR_{atr_len}'
    if atr_col_name not in prev.index:
        logging.error(f"La colonna ATR '{atr_col_name}' non è stata creata per {symbol}.")
        return None
        
    atr_prev = prev[atr_col_name]
    if pd.isna(atr_prev) or atr_prev == 0:
        logging.info(f"ATR non disponibile per {symbol}.")
        return None

    is_pullback_to_buy  = (prev['low'] <= prev[f'EMA_{ema_fast}']) and ((prev['high'] - prev['low']) >= 0.6 * atr_prev)
    is_pullback_to_sell = (prev['high'] >= prev[f'EMA_{ema_fast}']) and ((prev['high'] - prev['low']) >= 0.6 * atr_prev)

    long_trigger  = prev['high']
    short_trigger = prev['low']

    swing_low  = min(prev['low'], prev2['low'])
    swing_high = max(prev['high'], prev2['high'])
    long_sl_candidate  = min(swing_low, prev['low'])
    short_sl_candidate = max(swing_high, prev['high'])

    long_sl  = long_sl_candidate  - atr_mult_sl * atr_prev
    short_sl = short_sl_candidate + atr_mult_sl * atr_prev

    final_signal = None
    entry_price  = None
    stop_loss    = None
    take_profit  = None
    details      = []

    if is_uptrend and is_pullback_to_buy:
        if use_stop_entry:
            entry_price = float(long_trigger)
            if long_sl >= entry_price:
                long_sl = entry_price - max(atr_prev, (entry_price - swing_low) * 0.5)
            if long_sl >= entry_price:
                logging.info(f"LONG {symbol} scartato: SL non valido.")
                entry_price = None
            else:
                final_signal = "LONG"
        else:
            if current['close'] > current['open']:
                entry_price = float(current['close'])
                if long_sl >= entry_price:
                    logging.info(f"LONG {symbol} scartato: SL non valido.")
                    entry_price = None
                else:
                    final_signal = "LONG"

        if final_signal == "LONG":
            risk = entry_price - long_sl
            if atr_mult_tp is not None:
                tp_distance = atr_mult_tp * atr_prev
                take_profit = entry_price + max(tp_distance, 0.8 * risk)
                details.append(f"TP=entry+{atr_mult_tp}*ATR")
            else:
                take_profit = entry_price + rr_ratio * risk
                details.append(f"TP=RR*{rr_ratio:.2f}")
            stop_loss = float(long_sl)

    elif is_downtrend and is_pullback_to_sell:
        if use_stop_entry:
            entry_price = float(short_trigger)
            if short_sl <= entry_price:
                short_sl = entry_price + max(atr_prev, (swing_high - entry_price) * 0.5)
            if short_sl <= entry_price:
                logging.info(f"SHORT {symbol} scartato: SL non valido.")
                entry_price = None
            else:
                final_signal = "SHORT"
        else:
            if current['close'] < current['open']:
                entry_price = float(current['close'])
                if short_sl <= entry_price:
                    logging.info(f"SHORT {symbol} scartato: SL non valido.")
                    entry_price = None
                else:
                    final_signal = "SHORT"

        if final_signal == "SHORT":
            risk = short_sl - entry_price
            if atr_mult_tp is not None:
                tp_distance = atr_mult_tp * atr_prev
                take_profit = entry_price - max(tp_distance, 0.8 * risk)
                details.append(f"TP=entry-{atr_mult_tp}*ATR")
            else:
                take_profit = entry_price - rr_ratio * risk
                details.append(f"TP=RR*{rr_ratio:.2f}")
            stop_loss = float(short_sl)

    if final_signal and entry_price and stop_loss and take_profit:
        mgmt_data = {
            "partial_take": partial_take, "partial_at_R": 1.0, "move_to_be_at_R": 1.0,
            "trail_type": trail_type, "trail_atr_mult": trail_atr_mult,
            "setup_timeout_bars": setup_timeout_bars
        }
        info = {
            "timestamp": datetime.now(timezone.utc), "symbol": symbol, "signal_type": final_signal,
            "timeframe": f"PULLBACK {ema_slow}/{ema_fast}", "strategy": "Optimized Pullback v11",
            "score": params.get('profit_factor', 0),
            "details": f"ATR:{atr_len} SLx{atr_mult_sl} {'; '.join(details)}; slope>{ema_slope_min}; stop_entry:{use_stop_entry}; timeout:{setup_timeout_bars}",
            "entry_price": round(entry_price, 6), "stop_loss": round(stop_loss, 6), "take_profit": round(take_profit, 6),
            "mgmt_details": json.dumps(mgmt_data)
        }

        if db.check_recent_signal(symbol, final_signal):
            logging.info(f"Segnale per {symbol} ({final_signal}) già registrato. Salto.")
            return None

        db.save_signal(info)
        logging.info(f"✅ SEGNALE {final_signal} {symbol} a {entry_price} | SL {stop_loss} | TP {take_profit}")
        return info
    
    logging.info(f"Nessuna opportunità valida (filtri/validazioni) per {symbol}.")
    return None
