# phoenix_runner.py - v9.0 (Immediate Commit Patch)
# CORREZIONE CRITICA: Il salvataggio del segnale ora avviene
# immediatamente per evitare perdite dovute a rollback.

import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from datetime import datetime, timezone, timedelta

import database
import config
from api_clients.data_client import FinancialDataClient

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(asctime)s] %(message)s')

# (Le funzioni strategiche phoenix_signal_v91 e phoenix_momentum rimangono identiche)
def phoenix_signal_v91(df):
    out = []
    df = df.copy()
    rsi_col, atr_col, adx_col = f"RSI_{config.RSI_PERIOD}", f"ATRr_{config.ATR_PERIOD}", f"ADX_{config.ADX_PERIOD}"
    vol_ma = df["volume"].rolling(20).mean(); vol_std = df["volume"].rolling(20).std(ddof=0); df["vol_z"] = ((df["volume"] - vol_ma) / vol_std.replace(0, np.nan)).fillna(0.0)
    if len(df) < 5: return out
    T, T1 = df.iloc[-2], df.iloc[-1]
    if pd.isna(T[adx_col]) or pd.isna(T[rsi_col]): return out
    setup_rsi = T[rsi_col] <= config.RSI_LOW
    setup_vol = T["vol_z"] >= config.VOLUME_Z_SCORE_MIN
    if setup_rsi and setup_vol:
        confirm = (T1["close"] > T["close"] * 1.005)
        if confirm:
            entry = T1["close"]; sl = T["low"] - config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry + config.TP_ATR_MULTIPLIER * T[atr_col]
            out.append({"side": "Long", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": 88, "strategy": "MeanReversion"})
    setup_rsi_short = T[rsi_col] >= config.RSI_HIGH
    if setup_rsi_short and setup_vol:
        confirm_short = (T1["close"] < T["close"] * 0.995)
        if confirm_short:
            entry = T1["close"]; sl = T["high"] + config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry - config.TP_ATR_MULTIPLIER * T[atr_col]
            out.append({"side": "Short", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": 88, "strategy": "MeanReversion"})
    return out

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


def run_daily_operations():
    logging.info(f"--- Avvio Operazioni Phoenix (PATCH v9.0 IMMEDIATE COMMIT) ---")
    data_client = FinancialDataClient()
    database.init_db()

    # Apriamo la sessione una sola volta
    with database.session_scope() as session:
        # ... (logica pulizia e posizioni aperte) ...
        for asset in config.ASSET_UNIVERSE:
            try:
                # ... (logica skip asset) ...
                df = data_client.get_klines(asset, config.TIMEFRAME, config.DATA_SOURCE, limit=500)
                if df is None or df.empty or len(df) < 50: continue

                df.ta.adx(length=config.ADX_PERIOD, append=True); df.ta.rsi(length=config.RSI_PERIOD, append=True); df.ta.atr(length=config.ATR_PERIOD, append=True)
                df.sort_index(ascending=True, inplace=True)

                signals = phoenix_signal_v91(df)
                if not signals:
                    signals = phoenix_momentum(df)

                if signals:
                    signal = max(signals, key=lambda s: s.get("score", 0))
                    logging.info(f"!!! NUOVO SEGNALE TROVATO ({signal['strategy']}) !!!: {signal['side']} su {asset} | Score: {signal['score']}")
                    
                    new_intent = database.TradeIntent(
                        symbol=asset, direction=signal["side"], entry_price=signal["entry_price"],
                        take_profit=signal["tp"], stop_loss=signal["sl"],
                        score=signal["score"], status="SIMULATED"
                    )
                    session.add(new_intent)
                    
                    # ===== MODIFICA CRUCIALE =====
                    # Incidiamo il segnale nella pietra, ORA.
                    session.commit()
                    logging.info(f"--- SEGNALE {asset} SALVATO CORRETTAMENTE NEL DATABASE ---")

            except Exception as e:
                logging.error(f"Errore durante l'analisi di {asset}: {e}. Continuo con il prossimo asset.")
                session.rollback() # Annulla solo l'operazione fallita per questo asset
                continue # Passa all'asset successivo senza interrompere il ciclo

    logging.info("--- Fine Operazioni ---")

if __name__ == "__main__":
    run_daily_operations()
