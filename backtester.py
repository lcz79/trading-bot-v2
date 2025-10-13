# backtester.py - v7.0 (Fabbrica di Backtest Multi-Simbolo)
import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, timezone
import time
import numpy as np

# Importiamo la lista dei simboli dal nostro servizio ETL
from etl_service import SYMBOLS, get_klines_as_df

# --- CONFIGURAZIONE STRATEGIA "PULLBACK" ---
START_DATE_STR = "2022-01-01"
END_DATE_STR = "2023-12-31"
INITIAL_CAPITAL = 10000
TRADE_RISK_PERCENT = 0.02

# Parametri della strategia
EMA_SLOW = 50
EMA_FAST = 20
RISK_REWARD_RATIO = 1.5

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def load_full_historical_data(symbol, interval, start_str, end_str):
    # ... (funzione identica) ...
    logging.info(f"Avvio download dati storici per {symbol}...")
    start_ts=int(datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()*1000)
    end_ts=int(datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()*1000)
    all_data=pd.DataFrame()
    while start_ts < end_ts:
        df=get_klines_as_df(symbol, interval, start_time=start_ts, limit=1000)
        if df.empty: break
        all_data=pd.concat([all_data, df])
        start_ts=int(df.index[-1].timestamp()*1000)+(int(interval)*60*1000)
        # Non logghiamo più qui per non intasare l'output
        time.sleep(0.5)
    all_data=all_data[~all_data.index.duplicated(keep='first')]
    return all_data.sort_index()

def perform_single_backtest(symbol: str):
    """Esegue il backtest della strategia Pullback per un singolo simbolo e restituisce i risultati."""
    logging.info(f"--- INIZIO TEST per {symbol} ---")
    
    full_df = load_full_historical_data(symbol, "60", "2021-11-01", END_DATE_STR)
    if full_df.empty:
        logging.error(f"Download dati per {symbol} fallito. Salto il test."); return None

    full_df.ta.ema(length=EMA_FAST, append=True)
    full_df.ta.ema(length=EMA_SLOW, append=True)
    test_df = full_df[START_DATE_STR:END_DATE_STR].copy()
    
    capital = INITIAL_CAPITAL
    trades = []
    active_trade = None

    for i in range(2, len(test_df)):
        prev_candle = test_df.iloc[i-1]
        current_candle = test_df.iloc[i]
        
        if active_trade:
            # ... (logica di uscita identica alla v6) ...
            exit_price = None
            if active_trade['type'] == 'LONG':
                if current_candle['low'] <= active_trade['stop_loss']: exit_price = active_trade['stop_loss']
                elif current_candle['high'] >= active_trade['take_profit']: exit_price = active_trade['take_profit']
            elif active_trade['type'] == 'SHORT':
                if current_candle['high'] >= active_trade['stop_loss']: exit_price = active_trade['stop_loss']
                elif current_candle['low'] <= active_trade['take_profit']: exit_price = active_trade['take_profit']
            if exit_price:
                pnl = (exit_price - active_trade['entry_price']) * active_trade['units']
                if active_trade['type'] == 'SHORT': pnl = -pnl
                capital += pnl
                active_trade.update({'pnl': pnl, 'exit_date': current_candle.name})
                trades.append(active_trade)
                active_trade = None
        
        if not active_trade:
            # ... (logica di ingresso identica alla v6) ...
            is_uptrend = prev_candle['close'] > prev_candle[f'EMA_{EMA_SLOW}']
            is_pullback_long = prev_candle['low'] < prev_candle[f'EMA_{EMA_FAST}']
            is_reversal_candle_long = current_candle['close'] > current_candle['open']
            if is_uptrend and is_pullback_long and is_reversal_candle_long:
                entry_price = current_candle['close']; stop_loss = prev_candle['low']
                take_profit = entry_price + ((entry_price - stop_loss) * RISK_REWARD_RATIO)
                risk_per_unit = entry_price - stop_loss
                risk_amount = capital * TRADE_RISK_PERCENT
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
                if position_size > 0:
                    active_trade = {'type': 'LONG', 'entry_date': current_candle.name, 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'units': position_size}
            is_downtrend = prev_candle['close'] < prev_candle[f'EMA_{EMA_SLOW}']
            is_pullback_short = prev_candle['high'] > prev_candle[f'EMA_{EMA_FAST}']
            is_reversal_candle_short = current_candle['close'] < current_candle['open']
            if is_downtrend and is_pullback_short and is_reversal_candle_short:
                entry_price = current_candle['close']; stop_loss = prev_candle['high']
                take_profit = entry_price - ((stop_loss - entry_price) * RISK_REWARD_RATIO)
                risk_per_unit = stop_loss - entry_price
                risk_amount = capital * TRADE_RISK_PERCENT
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
                if position_size > 0:
                    active_trade = {'type': 'SHORT', 'entry_date': current_candle.name, 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'units': position_size}
    
    if not trades:
        logging.warning(f"Nessun trade eseguito per {symbol}."); return None

    results_df = pd.DataFrame(trades)
    total_pnl = results_df['pnl'].sum()
    win_trades = results_df[results_df['pnl'] > 0]
    loss_trades = results_df[results_df['pnl'] <= 0]
    win_rate = (len(win_trades) / len(results_df)) * 100
    profit_factor = win_trades['pnl'].sum() / abs(loss_trades['pnl'].sum()) if not loss_trades.empty and loss_trades['pnl'].sum() != 0 else float('inf')
    results_df['capital'] = INITIAL_CAPITAL + results_df['pnl'].cumsum()
    results_df['peak'] = results_df['capital'].cummax()
    results_df['drawdown'] = (results_df['capital'] - results_df['peak']) / results_df['peak']
    max_drawdown = results_df['drawdown'].min() * 100
    
    return {
        "Symbol": symbol,
        "Performance %": (total_pnl / INITIAL_CAPITAL) * 100,
        "Profit Factor": profit_factor,
        "Win Rate %": win_rate,
        "N. Trade": len(results_df),
        "Max Drawdown %": max_drawdown
    }

def run_all_backtests():
    """Esegue il backtest su tutti i simboli e stampa un report riassuntivo."""
    all_results = []
    
    for symbol in SYMBOLS:
        result = perform_single_backtest(symbol)
        if result:
            all_results.append(result)
    
    if not all_results:
        logging.error("Nessun backtest completato con successo.")
        return

    summary_df = pd.DataFrame(all_results)
    summary_df = summary_df.round(2) # Arrotonda tutti i valori a 2 decimali
    summary_df = summary_df.sort_values(by="Profit Factor", ascending=False)
    
    print("\n" + "="*70)
    print(" " * 15 + "RIEPILOGO BACKTEST: OPERAZIONE PULLBACK")
    print("="*70)
    print(summary_df.to_markdown(index=False))
    print("="*70 + "\n")

if __name__ == "__main__":
    run_all_backtests()
