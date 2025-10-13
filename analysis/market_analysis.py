# analysis/market_analysis.py - v9.0 (Motore Dinamico basato su Parametri Ottimali)
import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, timezone

# Importiamo solo il database, perché la logica ora è autonoma
import database as db

def run_pullback_analysis(symbol: str, data_1h: pd.DataFrame, params: dict):
    """
    Esegue l'analisi della strategia Pullback usando i parametri specifici
    forniti per un determinato simbolo.
    """
    try:
        ema_slow = params['ema_slow']
        ema_fast = params['ema_fast']
        rr_ratio = params['rr_ratio']
    except KeyError:
        logging.error(f"Parametri mancanti per {symbol}. Salto l'analisi.")
        return

    logging.info(f"--- Avvio Analisi Pullback per {symbol} con parametri {ema_slow}/{ema_fast}, RR {rr_ratio} ---")
    
    df = data_1h.copy()
    df.ta.ema(length=ema_fast, append=True)
    df.ta.ema(length=ema_slow, append=True)
    
    # Abbiamo bisogno di almeno 3 candele per avere prev_prev, prev, e current
    if len(df) < 3:
        return

    # Usiamo la penultima candela per le condizioni e l'ultima per l'ingresso
    prev_candle = df.iloc[-2]
    current_candle = df.iloc[-1]
    
    final_signal = None
    
    # CONDIZIONI PER UN PULLBACK LONG
    is_uptrend = prev_candle['close'] > prev_candle[f'EMA_{ema_slow}']
    is_pullback_long = prev_candle['low'] < prev_candle[f'EMA_{ema_fast}']
    is_reversal_candle_long = current_candle['close'] > current_candle['open']

    if is_uptrend and is_pullback_long and is_reversal_candle_long:
        final_signal = "LONG"
        entry_price = current_candle['close']
        stop_loss = df.iloc[-3]['low'] # Usiamo il minimo di 2 candele fa per più sicurezza
        take_profit = entry_price + ((entry_price - stop_loss) * rr_ratio)

    # CONDIZIONI PER UN PULLBACK SHORT
    is_downtrend = prev_candle['close'] < prev_candle[f'EMA_{ema_slow}']
    is_pullback_short = prev_candle['high'] > prev_candle[f'EMA_{ema_fast}']
    is_reversal_candle_short = current_candle['close'] < current_candle['open']

    if not final_signal and is_downtrend and is_pullback_short and is_reversal_candle_short:
        final_signal = "SHORT"
        entry_price = current_candle['close']
        stop_loss = df.iloc[-3]['high'] # Usiamo il massimo di 2 candele fa
        take_profit = entry_price - ((stop_loss - entry_price) * rr_ratio)

    if final_signal:
        logging.info(f"✅ SEGNALE TROVATO per {symbol}: {final_signal}")
        
        # Controlla se un segnale simile è già stato salvato di recente
        if db.check_recent_signal(symbol, final_signal):
            logging.info(f"Segnale per {symbol} ({final_signal}) già registrato di recente. Salto.")
            return

        # Salva il segnale nel database
        db.save_signal({
            "timestamp": datetime.now(timezone.utc),
            "symbol": symbol,
            "signal_type": final_signal,
            "timeframe": f"PULLBACK {ema_slow}/{ema_fast}",
            "strategy": "Optimized Pullback",
            "score": params.get('profit_factor', 0), # Usiamo il PF come 'score'
            "details": f"RR: {rr_ratio}, PF: {params.get('profit_factor', 0)}",
            "entry_price": round(entry_price, 4),
            "stop_loss": round(stop_loss, 4),
            "take_profit": round(take_profit, 4)
        })
    else:
        logging.info(f"Nessuna opportunità di pullback trovata per {symbol}.")
