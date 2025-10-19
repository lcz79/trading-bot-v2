# mitragliere_intraday_v1.2.py — Intraday Research Engine
# Combina il fix per il path di importazione con il fix per il KeyError di pandas-ta.

import os
import sys
import json
import logging
import warnings
from datetime import datetime, timezone

import pandas as pd
import pandas_ta as ta

# --- Blocco correzione percorso (necessario per l'esecuzione in sottocartella) ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from data_sources import binance_client

warnings.simplefilter(action='ignore', category=FutureWarning)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def prepare_dataframe(klines):
    cols = ['timestamp','open','high','low','close','volume','close_time','quote_av','trades','tb_base_av','tb_quote_av','ignore']
    df = pd.DataFrame(klines, columns=cols)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for c in ['open','high','low','close','volume']:
        df[c] = pd.to_numeric(df[c])
    df = df[['timestamp','open','high','low','close','volume']].dropna().reset_index(drop=True)
    return df


def restrict_session(df, session_hours=None):
    if not session_hours: return df
    sh, eh = session_hours
    m = df['timestamp'].dt.hour.between(sh, eh - 1, inclusive='both')
    return df.loc[m].reset_index(drop=True)


def add_intraday_indicators(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    bb_len = params.get('bb_len', 20)
    bb_mult = params.get('bb_mult', 2.0)
    bb = ta.bbands(df['close'], length=bb_len, std=bb_mult)
    
    # --- IL TUO FIX: Assegnazione tramite indice, la soluzione più robusta ---
    df['BBL'] = bb.iloc[:, 0]
    df['BBM'] = bb.iloc[:, 1]
    df['BBU'] = bb.iloc[:, 2]

    rsi_len = params.get('rsi_len', 14)
    df['RSI'] = ta.rsi(df['close'], length=rsi_len)

    atr_len = params.get('atr_len', 14)
    # pandas-ta crea una colonna chiamata 'ATRr_14', non 'ATR_14'. Usiamo il nome corretto.
    df[f'ATRr_{atr_len}'] = ta.atr(df['high'], df['low'], df['close'], length=atr_len)

    dc_len = params.get('dc_len', 20)
    df['DC_HIGH'] = df['high'].rolling(dc_len).max()
    df['DC_LOW']  = df['low'].rolling(dc_len).min()
    df['DC_WIDTH'] = (df['DC_HIGH'] - df['DC_LOW']).fillna(0)

    v_len = params.get('vol_sma_len', 20)
    df['VOL_SMA'] = df['volume'].rolling(v_len).mean()

    return df


def signal_mean_reversion(df: pd.DataFrame, i: int, params: dict):
    rsi_buy = params.get('rsi_buy', 30)
    rsi_sell = params.get('rsi_sell', 70)
    use_rr = params.get('use_rr_mr', True)
    rr = params.get('rr_mr', 1.2)
    atr_len = params.get('atr_len', 14)
    col_atr = f'ATRr_{atr_len}'

    if i < 2: return None
    c_prev = df.iloc[i-1]
    c_now  = df.iloc[i]

    atr_val = c_prev[col_atr] if pd.notna(c_prev[col_atr]) else 0

    if (c_prev['low'] <= c_prev['BBL']) and (c_prev['RSI'] <= rsi_buy):
        entry = c_now['close']
        sl = min(c_prev['low'], c_prev['BBL']) - 0.1 * atr_val
        tp = entry + rr * (entry - sl) if use_rr else c_prev['BBM']
        return {"side": "LONG", "entry": entry, "sl": sl, "tp": tp}

    if (c_prev['high'] >= c_prev['BBU']) and (c_prev['RSI'] >= rsi_sell):
        entry = c_now['close']
        sl = max(c_prev['high'], c_prev['BBU']) + 0.1 * atr_val
        tp = entry - rr * (sl - entry) if use_rr else c_prev['BBM']
        return {"side": "SHORT", "entry": entry, "sl": sl, "tp": tp}
    return None


def signal_breakout(df: pd.DataFrame, i: int, params: dict):
    atr_len = params.get('atr_len', 14)
    col_atr = f'ATRr_{atr_len}'
    min_compr = params.get('min_compression_atr', 0.6)
    vol_mult = params.get('volume_multiplier', 1.2)
    rr = params.get('rr_brk', 1.6)
    if i < 2: return None
    prev = df.iloc[i-1]
    now  = df.iloc[i]
    atr = prev[col_atr] if pd.notna(prev[col_atr]) else 0
    if atr == 0: return None
    compressed = prev['DC_WIDTH'] < (min_compr * atr)
    vol_ok = now['volume'] > (vol_mult * (prev['VOL_SMA'] if pd.notna(prev['VOL_SMA']) else 0))
    if compressed and vol_ok and (now['high'] > prev['DC_HIGH']):
        entry = now['close']; sl = prev['DC_LOW']; tp = entry + rr * (entry - sl)
        return {"side": "LONG", "entry": entry, "sl": sl, "tp": tp}
    if compressed and vol_ok and (now['low'] < prev['DC_LOW']):
        entry = now['close']; sl = prev['DC_HIGH']; tp = entry - rr * (sl - entry)
        return {"side": "SHORT", "entry": entry, "sl": sl, "tp": tp}
    return None


def backtest_intraday(df: pd.DataFrame, params: dict, logic_name: str, session_hours=None):
    df = restrict_session(df, session_hours)
    df = add_intraday_indicators(df, params)
    trades, active = [], None
    start = max(params.get('bb_len',20), params.get('dc_len',20), params.get('atr_len',14)) + 5
    for i in range(start, len(df)):
        if active:
            c = df.iloc[i]; res = None
            if active['side'] == 'LONG':
                if c['low'] <= active['sl']: res = 'SL'
                elif c['high'] >= active['tp']: res = 'TP'
            else:
                if c['high'] >= active['sl']: res = 'SL'
                elif c['low'] <= active['tp']: res = 'TP'
            if res:
                active['exit_time'] = df.iloc[i]['timestamp']; active['result'] = res; trades.append(active); active = None
        if not active:
            if logic_name == 'MR_BB_RSI': sig = signal_mean_reversion(df, i, params)
            elif logic_name == 'BRK_COMP_VOL': sig = signal_breakout(df, i, params)
            else: sig = None
            if sig: sig['entry_time'] = df.iloc[i]['timestamp']; active = sig
            
    if not trades:
        return {"name": logic_name,"profit_factor":0,"total_trades":0,"win_rate":0,"avg_r_per_trade":0}
        
    gross_profit = sum(abs(t['tp']-t['entry']) for t in trades if t['result']=='TP')
    gross_loss = sum(abs(t['sl']-t['entry']) for t in trades if t['result']=='SL')
    profit_factor = gross_profit/gross_loss if gross_loss>1e-12 else float('inf')
    win_trades = len([t for t in trades if t['result']=='TP'])
    win_rate = round((win_trades/len(trades))*100,2) if trades else 0
    avg_r = round((gross_profit-gross_loss)/len(trades),6) if trades else 0
    return {"name":logic_name,"profit_factor":round(profit_factor,2),"total_trades":len(trades),"win_rate":win_rate,"avg_r_per_trade":avg_r}


def grid_search_intraday(df, logic_name, param_grid, session_hours=None):
    results = []
    for params in param_grid:
        res = backtest_intraday(df.copy(), params, logic_name, session_hours=session_hours)
        row = {**params, **res}
        results.append(row)
    results = sorted(results, key=lambda x: (x.get('profit_factor', 0), x.get('win_rate', 0), x.get('avg_r_per_trade', 0)), reverse=True)
    return results


if __name__ == '__main__':
    YEARS = 1; TF = '15m'; SESSION_HOURS = (7, 20)
    ASSETS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]
    start_date = f"{YEARS} years ago UTC"
    MR_GRID = [{"bb_len":20,"bb_mult":2.0,"rsi_len":14,"rsi_buy":30,"rsi_sell":70,"atr_len":14,"use_rr_mr":True,"rr_mr":1.2},
               {"bb_len":20,"bb_mult":2.2,"rsi_len":14,"rsi_buy":28,"rsi_sell":72,"atr_len":14,"use_rr_mr":False},
               {"bb_len":18,"bb_mult":2.0,"rsi_len":12,"rsi_buy":32,"rsi_sell":68,"atr_len":14,"use_rr_mr":True,"rr_mr":1.5}]
    BRK_GRID = [{"dc_len":20,"atr_len":14,"min_compression_atr":0.6,"vol_sma_len":20,"volume_multiplier":1.2,"rr_brk":1.6},
                {"dc_len":30,"atr_len":14,"min_compression_atr":0.5,"vol_sma_len":30,"volume_multiplier":1.3,"rr_brk":1.8},
                {"dc_len":14,"atr_len":14,"min_compression_atr":0.7,"vol_sma_len":20,"volume_multiplier":1.1,"rr_brk":1.4}]
    hof = {}
    try:
        with open('hall_of_fame_intraday.json','r') as f: hof=json.load(f); logging.info("Caricato hall_of_fame_intraday.json esistente (verrà aggiornato).")
    except FileNotFoundError: logging.info("Creerò un nuovo hall_of_fame_intraday.json.")
    all_rows = []
    for symbol in ASSETS:
        logging.info(f"=== INTRADAY RESEARCH su {symbol} ({TF}) ===")
        try:
            klines = binance_client.get_historical_klines(symbol, TF, start_date)
            if not klines: logging.warning(f"Nessun dato per {symbol}. Salto."); continue
            df = prepare_dataframe(klines); logging.info(f"Dati caricati: {len(df)} barre")
        except Exception as e:
            logging.error(f"Errore dati {symbol}: {e}"); continue
        mr_results = grid_search_intraday(df.copy(),'MR_BB_RSI',MR_GRID,session_hours=SESSION_HOURS); best_mr = mr_results[0] if mr_results else None
        brk_results = grid_search_intraday(df.copy(),'BRK_COMP_VOL',BRK_GRID,session_hours=SESSION_HOURS); best_brk = brk_results[0] if brk_results else None
        candidates = [x for x in [best_mr,best_brk] if x and x.get('total_trades', 0) > 20]
        if candidates:
            best = sorted(candidates,key=lambda x:(x.get('profit_factor', 0),x.get('win_rate', 0),x.get('avg_r_per_trade', 0)),reverse=True)[0]
            hof[symbol]=best; logging.info(f"🥇 Migliore su {symbol}: {best['name']} PF {best['profit_factor']} WR {best['win_rate']}% R {best['avg_r_per_trade']}")
            all_rows.append({**best,"asset":symbol})
        else: logging.info(f"Nessuna strategia valida (>20 trade) su {symbol} in questa run.")
    if all_rows:
        dfres=pd.DataFrame(sorted(all_rows,key=lambda x:(x.get('profit_factor', 0),x.get('win_rate', 0),x.get('avg_r_per_trade', 0)),reverse=True))
        print("\n"+"="*80); print("  CLASSIFICA INTRADAY (Mitragliere v1.2)"); print("="*80)
        print(dfres.to_string(index=False)); print("="*80)
    with open('hall_of_fame_intraday.json','w') as f: json.dump(hof,f,indent=4,sort_keys=True)
    user=os.getenv("USER") or os.getenv("USERNAME") or "unknown"
    now_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"🏆 hall_of_fame_intraday.json aggiornato | by {user} @ {now_utc} UTC")
