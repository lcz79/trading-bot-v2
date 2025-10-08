# phoenix_backtester.py - Validazione Storica Finale
# ----------------------------------------------------------------
# - Esegue la strategia Dual-Engine v7.0 su un lungo periodo storico.
# - L'obiettivo è validare che la logica genera segnali e
#   capire la sua frequenza operativa reale.
# ----------------------------------------------------------------

import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from datetime import datetime, timezone

# Usa i file del nostro progetto
import config
from api_clients.data_client import FinancialDataClient

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(asctime)s] %(message)s')

# Le funzioni strategiche sono identiche al runner v7.0
# Le copiamo qui per rendere lo script autonomo.

def phoenix_signal_v91(df):
    out = []
    df = df.copy()
    df.ta.rsi(length=config.RSI_PERIOD, append=True); df.ta.atr(length=config.ATR_PERIOD, append=True); df.ta.adx(length=config.ADX_PERIOD, append=True)
    rsi_col, atr_col, adx_col = f"RSI_{config.RSI_PERIOD}", f"ATRr_{config.ATR_PERIOD}", f"ADX_{config.ADX_PERIOD}"
    vol_ma = df["volume"].rolling(20).mean(); vol_std = df["volume"].rolling(20).std(ddof=0); df["vol_z"] = ((df["volume"] - vol_ma) / vol_std.replace(0, np.nan)).fillna(0.0)
    if len(df) < 100: df["RSI_LOW_ADAPT"], df["RSI_HIGH_ADAPT"] = config.RSI_LOW, config.RSI_HIGH
    else:
        df["RSI_LOW_ADAPT"] = df[rsi_col].rolling(365, min_periods=100).quantile(0.10).fillna(config.RSI_LOW)
        df["RSI_HIGH_ADAPT"] = df[rsi_col].rolling(365, min_periods=100).quantile(0.90).fillna(config.RSI_HIGH)
    if len(df) < 5: return out
    T, T1 = df.iloc[-2], df.iloc[-1]
    if pd.isna(T[adx_col]) or pd.isna(T[rsi_col]): return out
    adx = T[adx_col]
    regime = "RANGE" if adx < 20 else "MIXED" if adx < 30 else "TREND"
    rsi_low_threshold = T["RSI_LOW_ADAPT"] if regime == "RANGE" else 25
    setup_rsi = T[rsi_col] <= rsi_low_threshold
    setup_vol = (T["vol_z"] >= 0.5) or (df["vol_z"].iloc[-4:-1].max() >= 0.8)
    if regime == "TREND": setup_rsi, setup_vol = T[rsi_col] <= 25, T["vol_z"] >= 1.0
    if setup_rsi and setup_vol:
        confirm = (T1["close"] > T["close"]) and (T1[rsi_col] > T[rsi_col])
        if confirm:
            entry = T1["close"]; sl = T["low"] - config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry + config.TP_ATR_MULTIPLIER * T[atr_col]
            score = int(min(100, (100 - abs(T[rsi_col]-50)) + T["vol_z"]*10))
            out.append({"side": "Long", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": score, "strategy": "MeanReversion", "date": T1.name})
    rsi_high_threshold = T["RSI_HIGH_ADAPT"] if regime == "RANGE" else 75
    setup_rsi_short = T[rsi_col] >= rsi_high_threshold
    if regime == "TREND": setup_rsi_short, setup_vol = T[rsi_col] >= 75, T["vol_z"] >= 1.0
    if setup_rsi_short and setup_vol:
        confirm_short = (T1["close"] < T["close"]) and (T1[rsi_col] < T[rsi_col])
        if confirm_short:
            entry = T1["close"]; sl = T["high"] + config.SL_ATR_MULTIPLIER * T[atr_col]; tp = entry - config.TP_ATR_MULTIPLIER * T[atr_col]
            score = int(min(100, (abs(T[rsi_col]-50)) + T["vol_z"]*10))
            out.append({"side": "Short", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": score, "strategy": "MeanReversion", "date": T1.name})
    return out

def phoenix_momentum(df):
    out = []
    df = df.copy()
    df.ta.adx(length=config.ADX_PERIOD, append=True); df.ta.rsi(length=config.RSI_PERIOD, append=True); df.ta.sma(length=50, append=True)
    adx_col, rsi_col, sma_col = f"ADX_{config.ADX_PERIOD}", f"RSI_{config.RSI_PERIOD}", "SMA_50"
    if len(df) < 51: return out
    T, T1 = df.iloc[-2], df.iloc[-1]
    if pd.isna(T1[adx_col]) or pd.isna(T1['close']) or pd.isna(T1[sma_col]): return out
    if T1[adx_col] > 25 and T1["close"] > T1[sma_col]:
        if T[rsi_col] < 45 and T1[rsi_col] > 55:
            entry = T1["close"]; sl = T1["low"] * 0.98; tp = entry * 1.08
            score = int(min(100, (T1[adx_col]) + (T1[rsi_col]-50)*2))
            out.append({"side": "Long", "entry_price": float(entry), "sl": float(sl), "tp": float(tp), "score": score, "strategy": "Momentum", "date": T1.name})
    return out


def run_backtest(asset_to_test, days_to_backtest=365):
    logging.info(f"--- AVVIO BACKTEST STORICO per {asset_to_test} su {days_to_backtest} giorni ---")
    data_client = FinancialDataClient()
    
    # Bybit fornisce max 1000 candele per chiamata. Per H4, 1000 candele sono ~166 giorni.
    # Per un anno, dobbiamo fare più chiamate o aumentare il limite se possibile.
    # Per ora, usiamo 1000 candele come rappresentazione.
    limit = 1000
    df_full = data_client.get_klines(asset_to_test, config.TIMEFRAME, config.DATA_SOURCE, limit=limit)
    
    if df_full is None or df_full.empty:
        logging.error(f"Impossibile scaricare dati storici per {asset_to_test}.")
        return

    df_full.sort_index(ascending=True, inplace=True)
    
    all_signals = []
    
    # Iteriamo su tutto lo storico, simulando il passaggio del tempo
    # Partiamo da un punto in cui abbiamo abbastanza dati per gli indicatori
    start_index = 100 
    for i in range(start_index, len(df_full)):
        # Creiamo una "vista" del dataframe che si ferma al punto 'i' nel tempo
        df_slice = df_full.iloc[:i]
        
        # Eseguiamo la logica del doppio motore
        df_slice.ta.adx(length=config.ADX_PERIOD, append=True)
        adx_col = f"ADX_{config.ADX_PERIOD}"
        adx_last = df_slice[adx_col].iloc[-1] if adx_col in df_slice.columns and not pd.isna(df_slice[adx_col].iloc[-1]) else 25

        signals = []
        if adx_last < config.ADX_THRESHOLD:
            signals = phoenix_signal_v91(df_slice)
            if not signals: signals = phoenix_momentum(df_slice)
        else:
            signals = phoenix_momentum(df_slice)
            if not signals: signals = phoenix_signal_v91(df_slice)
        
        if signals:
            for signal in signals:
                # Controlliamo di non aggiungere lo stesso segnale più volte
                if not any(s['date'] == signal['date'] for s in all_signals):
                    all_signals.append(signal)

    logging.info(f"--- RISULTATI BACKTEST per {asset_to_test} ---")
    if not all_signals:
        print("Nessun segnale trovato nel periodo storico analizzato.")
    else:
        print(f"Trovati {len(all_signals)} segnali in circa {limit*4/24:.0f} giorni:")
        for s in sorted(all_signals, key=lambda x: x['date']):
            print(f"  - Data: {s['date'].strftime('%Y-%m-%d %H:%M')}, Strategia: {s['strategy']}, Side: {s['side']}, Score: {s['score']}")
            
    print("-" * 40)


if __name__ == "__main__":
    assets_to_backtest = ['BTCUSDT', 'ETHUSDT']
    for asset in assets_to_backtest:
        run_backtest(asset)