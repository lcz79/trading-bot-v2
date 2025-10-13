# optimizer.py - v1.0 (Trova la strategia ottimale per ogni asset)
import pandas as pd
import pandas_ta as ta
import logging
import time
import json
from itertools import product

# Importiamo la lista dei simboli e la funzione di download
from etl_service import SYMBOLS, get_klines_as_df

# --- CONFIGURAZIONE OTTIMIZZATORE ---
START_DATE_STR = "2022-01-01"
END_DATE_STR = "2023-12-31"
INITIAL_CAPITAL = 10000
TRADE_RISK_PERCENT = 0.02
OUTPUT_FILE = "optimal_strategies.json"

# --- POOL GENETICO (PARAMETRI DA TESTARE) ---
EMA_SLOW_OPTIONS = [50, 100, 200]
EMA_FAST_OPTIONS = [10, 20] # Ridotto per velocizzare i test
RR_RATIO_OPTIONS = [1.5, 2.0, 2.5]

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def run_single_optimization(symbol: str, data: pd.DataFrame, params: dict):
    """Esegue un singolo backtest con un set di parametri specifico."""
    ema_slow, ema_fast, rr_ratio = params['ema_slow'], params['ema_fast'], params['rr_ratio']
    
    df = data.copy()
    df.ta.ema(length=ema_fast, append=True)
    df.ta.ema(length=ema_slow, append=True)
    
    capital = INITIAL_CAPITAL
    trades = []
    active_trade = None

    for i in range(2, len(df)):
        prev_candle = df.iloc[i-1]
        current_candle = df.iloc[i]
        
        if active_trade:
            # ... (logica di uscita identica ai backtest precedenti) ...
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
                active_trade.update({'pnl': pnl})
                trades.append(active_trade)
                active_trade = None
        
        if not active_trade:
            # ... (logica di ingresso identica ai backtest precedenti) ...
            is_uptrend = prev_candle['close'] > prev_candle[f'EMA_{ema_slow}']
            is_pullback_long = prev_candle['low'] < prev_candle[f'EMA_{ema_fast}']
            is_reversal_candle_long = current_candle['close'] > current_candle['open']
            if is_uptrend and is_pullback_long and is_reversal_candle_long:
                entry_price = current_candle['close']; stop_loss = prev_candle['low']
                take_profit = entry_price + ((entry_price - stop_loss) * rr_ratio)
                risk_per_unit = entry_price - stop_loss
                position_size = (capital * TRADE_RISK_PERCENT) / risk_per_unit if risk_per_unit > 0 else 0
                if position_size > 0: active_trade = {'type': 'LONG', 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'units': position_size}
            
            is_downtrend = prev_candle['close'] < prev_candle[f'EMA_{ema_slow}']
            is_pullback_short = prev_candle['high'] > prev_candle[f'EMA_{ema_fast}']
            is_reversal_candle_short = current_candle['close'] < current_candle['open']
            if is_downtrend and is_pullback_short and is_reversal_candle_short:
                entry_price = current_candle['close']; stop_loss = prev_candle['high']
                take_profit = entry_price - ((stop_loss - entry_price) * rr_ratio)
                risk_per_unit = stop_loss - entry_price
                position_size = (capital * TRADE_RISK_PERCENT) / risk_per_unit if risk_per_unit > 0 else 0
                if position_size > 0: active_trade = {'type': 'SHORT', 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'units': position_size}

    if not trades: return 0.0

    results_df = pd.DataFrame(trades)
    win_trades = results_df[results_df['pnl'] > 0]
    loss_trades = results_df[results_df['pnl'] <= 0]
    profit_factor = win_trades['pnl'].sum() / abs(loss_trades['pnl'].sum()) if not loss_trades.empty and loss_trades['pnl'].sum() != 0 else 0.0
    return profit_factor

def main():
    logging.info("--- AVVIO OTTIMIZZATORE DI STRATEGIE ---")
    
    # Crea tutte le combinazioni di parametri
    param_combinations = list(product(EMA_SLOW_OPTIONS, EMA_FAST_OPTIONS, RR_RATIO_OPTIONS))
    logging.info(f"Test per {len(param_combinations)} combinazioni di parametri per ogni simbolo.")
    
    optimal_strategies = {}

    for symbol in SYMBOLS:
        logging.info(f"--- Ottimizzazione per {symbol} ---")
        
        # Scarica i dati una sola volta per ogni simbolo
        data = get_klines_as_df(symbol, "60", limit=1000) # Usiamo dati recenti per l'ottimizzazione
        # In un sistema reale, scaricheremmo l'intero storico come nel backtester
        if data.empty:
            logging.warning(f"Dati per {symbol} non trovati. Salto.")
            continue

        best_profit_factor = -1
        best_params = None
        
        for i, (ema_slow, ema_fast, rr_ratio) in enumerate(param_combinations):
            # Filtro logico: l'EMA veloce deve essere più veloce della lenta
            if ema_fast >= ema_slow:
                continue

            params = {'ema_slow': ema_slow, 'ema_fast': ema_fast, 'rr_ratio': rr_ratio}
            logging.info(f"Test {i+1}/{len(param_combinations)}: {params}")
            
            profit_factor = run_single_optimization(symbol, data, params)
            
            if profit_factor > best_profit_factor:
                best_profit_factor = profit_factor
                best_params = params
                logging.info(f"*** Nuovo miglior Profit Factor per {symbol}: {profit_factor:.2f} con parametri {params} ***")

        if best_params:
            optimal_strategies[symbol] = {
                "ema_slow": best_params['ema_slow'],
                "ema_fast": best_params['ema_fast'],
                "rr_ratio": best_params['rr_ratio'],
                "profit_factor": round(best_profit_factor, 2)
            }

    logging.info("--- OTTIMIZZAZIONE COMPLETATA ---")
    
    if optimal_strategies:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(optimal_strategies, f, indent=4)
        logging.info(f"Strategie ottimali salvate nel file: {OUTPUT_FILE}")
        print(json.dumps(optimal_strategies, indent=4))
    else:
        logging.warning("Nessuna strategia ottimale trovata.")

if __name__ == "__main__":
    main()
