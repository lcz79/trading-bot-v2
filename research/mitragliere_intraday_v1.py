# mitragliere_intraday_v1.2.py — Intraday Research Engine (Trend-Filtered + Dynamic RR)

import os
import sys
import json
import logging
import warnings
from datetime import datetime, timezone

import pandas as pd
import pandas_ta as ta

# --- Blocco correzione percorso ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from data_sources import binance_client

warnings.simplefilter(action='ignore', category=FutureWarning)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


# ----------------------------------
# Utils
# ----------------------------------
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
    mask = df['timestamp'].dt.hour.between(sh, eh - 1, inclusive='both')
    return df.loc[mask].reset_index(drop=True)


def estimate_vol_regime(df, atr_col):
    atr_pct = (df[atr_col] / df['close']).rolling(96).mean() * 100
    last = float(atr_pct.iloc[-1]) if not pd.isna(atr_pct.iloc[-1]) else 0.0
    if last >= 0.3: return f"High ({last:.2f}%)"    # Soglie per 15m
    if last >= 0.15: return f"Medium ({last:.2f}%)"
    return f"Low ({last:.2f}%)"


# ----------------------------------
# Indicatori Intraday
# ----------------------------------
def add_intraday_indicators(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    bb_len = params.get('bb_len', 20); bb_mult = params.get('bb_mult', 2.0)
    bb = ta.bbands(df['close'], length=bb_len, std=bb_mult)
    df['BBL'] = bb.iloc[:, 0]; df['BBM'] = bb.iloc[:, 1]; df['BBU'] = bb.iloc[:, 2]

    rsi_len = params.get('rsi_len', 14)
    df['RSI'] = ta.rsi(df['close'], length=rsi_len)

    atr_len = params.get('atr_len', 14)
    df[f'ATR_{atr_len}'] = ta.atr(df['high'], df['low'], df['close'], length=atr_len)

    dc_len = params.get('dc_len', 20)
    df['DC_HIGH'] = df['high'].rolling(dc_len).max()
    df['DC_LOW']  = df['low'].rolling(dc_len).min()
    df['DC_WIDTH'] = (df['DC_HIGH'] - df['DC_LOW']).fillna(0)

    v_len = params.get('vol_sma_len', 20)
    df['VOL_SMA'] = df['volume'].rolling(v_len).mean()

    ema_tf = params.get('ema_trend_len', 100)
    df[f'EMA_{ema_tf}'] = ta.ema(df['close'], length=ema_tf)
    return df


# ----------------------------------
# Logiche di Segnale
# ----------------------------------
def dynamic_rr_from_atr(entry, sl, atr, min_rr=1.2, max_rr=2.5):
    base_r = abs(entry - sl)
    if base_r <= 1e-9: return min_rr
    factor = 1.0 + 0.5 * (atr / base_r)
    return max(min_rr, min(max_rr, factor))


def signal_mean_reversion(df: pd.DataFrame, i: int, params: dict):
    rsi_buy = params.get('rsi_buy', 30); rsi_sell = params.get('rsi_sell', 70)
    use_rr = params.get('use_rr_mr', True)
    atr_len = params.get('atr_len', 14); ema_tf = params.get('ema_trend_len', 100)

    if i < 2: return None
    prev = df.iloc[i-1]; now  = df.iloc[i]
    atr = prev[f'ATR_{atr_len}'] if not pd.isna(prev[f'ATR_{atr_len}']) else 0.0
    ema = prev[f'EMA_{ema_tf}'] if not pd.isna(prev[f'EMA_{ema_tf}']) else prev['close']

    if (prev['close'] > ema) and (prev['low'] <= prev['BBL']) and (prev['RSI'] <= rsi_buy):
        entry = now['close']; sl = min(prev['low'], prev['BBL']) - 0.1 * atr
        if use_rr:
            rr_dyn = dynamic_rr_from_atr(entry, sl, atr); tp = entry + rr_dyn * (entry - sl)
        else: tp = prev['BBM']
        return {"side": "LONG", "entry": entry, "sl": sl, "tp": tp}

    if (prev['close'] < ema) and (prev['high'] >= prev['BBU']) and (prev['RSI'] >= rsi_sell):
        entry = now['close']; sl = max(prev['high'], prev['BBU']) + 0.1 * atr
        if use_rr:
            rr_dyn = dynamic_rr_from_atr(entry, sl, atr); tp = entry - rr_dyn * (sl - entry)
        else: tp = prev['BBM']
        return {"side": "SHORT", "entry": entry, "sl": sl, "tp": tp}
    return None


def signal_breakout(df: pd.DataFrame, i: int, params: dict):
    atr_len = params.get('atr_len', 14); min_compr = params.get('min_compression_atr', 1.0)
    vol_mult = params.get('volume_multiplier', 1.05); rr = params.get('rr_brk', 1.8)
    ema_tf = params.get('ema_trend_len', 100)

    if i < 2: return None
    prev = df.iloc[i-1]; now  = df.iloc[i]
    atr = prev[f'ATR_{atr_len}'] if not pd.isna(prev[f'ATR_{atr_len}']) else 0.0
    if atr <= 0: return None
    ema = prev[f'EMA_{ema_tf}'] if not pd.isna(prev[f'EMA_{ema_tf}']) else prev['close']

    compressed = prev['DC_WIDTH'] < (min_compr * atr)
    vol_ok = now['volume'] > (vol_mult * (prev['VOL_SMA'] if not pd.isna(prev['VOL_SMA']) else 0))

    if compressed and vol_ok and (now['high'] > prev['DC_HIGH']) and (prev['close'] > ema):
        entry = now['close']; sl = prev['DC_LOW']; tp = entry + rr * (entry - sl)
        return {"side": "LONG", "entry": entry, "sl": sl, "tp": tp}

    if compressed and vol_ok and (now['low'] < prev['DC_LOW']) and (prev['close'] < ema):
        entry = now['close']; sl = prev['DC_HIGH']; tp = entry - rr * (sl - entry)
        return {"side": "SHORT", "entry": entry, "sl": sl, "tp": tp}
    return None


# ----------------------------------
# Backtest
# ----------------------------------
def backtest_intraday(df: pd.DataFrame, params: dict, logic_name: str, session_hours=None):
    df = restrict_session(df, session_hours)
    df = add_intraday_indicators(df, params)
    trades, active = [], None
    start = max(params.get(k, 20) for k in ['bb_len', 'dc_len', 'atr_len', 'ema_trend_len']) + 5

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
            sig = signal_mean_reversion(df, i, params) if logic_name == 'MR_BB_RSI' else signal_breakout(df, i, params)
            if sig: sig['entry_time'] = df.iloc[i]['timestamp']; active = sig

    if not trades: return {"name": logic_name, "profit_factor": 0, "total_trades": 0, "win_rate": 0, "avg_r_per_trade": 0}
    atr_col = f"ATR_{params.get('atr_len', 14)}"
    regime = estimate_vol_regime(df, atr_col)
    gross_profit = sum(abs(t['tp'] - t['entry']) for t in trades if t['result'] == 'TP')
    gross_loss   = sum(abs(t['sl'] - t['entry']) for t in trades if t['result'] == 'SL')
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else float('inf')
    win_trades = len([t for t in trades if t['result'] == 'TP'])
    win_rate = round((win_trades / len(trades)) * 100, 2)
    avg_r = round((gross_profit - gross_loss) / len(trades), 6)
    return {"name": logic_name, "profit_factor": round(profit_factor, 2), "total_trades": len(trades), "win_rate": win_rate, "avg_r_per_trade": avg_r, "vol_regime": regime}


def grid_search_intraday(df, logic_name, param_grid, session_hours=None):
    results = []
    for params in param_grid:
        res = backtest_intraday(df.copy(), params, logic_name, session_hours=session_hours)
        row = {**params, **res}; results.append(row)
    return sorted(results, key=lambda x: (x.get('profit_factor', 0), x.get('win_rate', 0)), reverse=True)


# ----------------------------------
# Main
# ----------------------------------
if __name__ == '__main__':
    YEARS = 1; TF = '15m'; SESSION_HOURS = (8, 18)
    ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    start_date = f"{YEARS} years ago UTC"
    MR_GRID = [{"bb_len": 20, "bb_mult": 2.0, "rsi_len": 14, "rsi_buy": 30, "rsi_sell": 70, "atr_len": 14, "use_rr_mr": True, "ema_trend_len": 100},
               {"bb_len": 20, "bb_mult": 2.2, "rsi_len": 14, "rsi_buy": 28, "rsi_sell": 72, "atr_len": 14, "use_rr_mr": True, "ema_trend_len": 100},
               {"bb_len": 18, "bb_mult": 2.0, "rsi_len": 12, "rsi_buy": 32, "rsi_sell": 68, "atr_len": 14, "use_rr_mr": True, "ema_trend_len": 100},
               {"bb_len": 20, "bb_mult": 2.0, "rsi_len": 14, "rsi_buy": 30, "rsi_sell": 70, "atr_len": 14, "use_rr_mr": False, "ema_trend_len": 100}]
    BRK_GRID = [{"dc_len": 20, "atr_len": 14, "min_compression_atr": 1.0, "vol_sma_len": 20, "volume_multiplier": 1.05, "rr_brk": 1.8, "ema_trend_len": 100},
                {"dc_len": 30, "atr_len": 14, "min_compression_atr": 1.0, "vol_sma_len": 30, "volume_multiplier": 1.10, "rr_brk": 2.0, "ema_trend_len": 100},
                {"dc_len": 14, "atr_len": 14, "min_compression_atr": 0.9, "vol_sma_len": 20, "volume_multiplier": 1.05, "rr_brk": 1.6, "ema_trend_len": 100}]
    hof = {}; all_rows = []
    try:
        with open('hall_of_fame_intraday.json', 'r') as f: hof = json.load(f); logging.info("Caricato HOF intraday.")
    except FileNotFoundError: logging.info("Creerò un nuovo HOF intraday.")
    for symbol in ASSETS:
        logging.info(f"=== INTRADAY RESEARCH v1.2 su {symbol} ({TF}) ===")
        try:
            klines = binance_client.get_historical_klines(symbol, TF, start_date)
            if not klines: logging.warning(f"No data for {symbol}. Skip."); continue
            df = prepare_dataframe(klines); logging.info(f"Dati: {len(df)} barre")
        except Exception as e: logging.error(f"Errore dati {symbol}: {e}"); continue
        mr_results = grid_search_intraday(df.copy(), 'MR_BB_RSI', MR_GRID, session_hours=SESSION_HOURS)
        brk_results = grid_search_intraday(df.copy(), 'BRK_COMP_VOL', BRK_GRID, session_hours=SESSION_HOURS)
        candidates = [x for x in (mr_results[0], brk_results[0]) if x and x.get('total_trades', 0) > 20]
        if candidates:
            best = sorted(candidates, key=lambda x: x.get('profit_factor', 0), reverse=True)[0]
            best['asset'] = symbol
            hof[symbol] = best; all_rows.append(best)
            logging.info(f"🥇 Best {symbol}: {best['name']} | PF {best['profit_factor']} | WR {best['win_rate']}% | Trades {best['total_trades']} | Regime {best['vol_regime']}")
        else: logging.info(f"Nessuna strategia valida (>20 trade) su {symbol}.")
    if all_rows:
        dfres = pd.DataFrame(sorted(all_rows, key=lambda x: x.get('profit_factor', 0), reverse=True))
        print("\n" + "="*90); print("  CLASSIFICA GLOBALE INTRADAY (Mitragliere v1.2)"); print("="*90)
        print(dfres[['asset','name','profit_factor','win_rate','total_trades','vol_regime']].to_string(index=False)); print("="*90)
    with open('hall_of_fame_intraday.json', 'w') as f: json.dump(hof, f, indent=4, sort_keys=True)
    user = os.getenv("USER") or os.getenv("USERNAME") or "unknown"
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"🏆 hall_of_fame_intraday.json aggiornato | by {user} @ {now_utc} UTC")
