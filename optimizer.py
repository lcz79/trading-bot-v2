# optimizer.py - v3.0 (Randomized Search for Speed)
import pandas as pd
import logging
import json
import itertools
import random # Importiamo il modulo random
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

from data_sources import binance_client
from analysis.market_analysis import find_pullback_signal

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_single_backtest(df_full, params):
    """Backtester leggero, non modificato."""
    trades = []
    active_trade = None
    start_index = max(params.get('ema_slow', 200), params.get('atr_len', 14)) + 10
    
    equity_curve = [1.0] 
    current_equity = 1.0

    for i in range(start_index, len(df_full)):
        current_market_data = df_full.iloc[0:i]
        
        if active_trade:
            current_candle = current_market_data.iloc[-1]
            result, exit_price = None, None

            if active_trade['type'] == 'LONG':
                if current_candle['low'] <= active_trade['sl']: result, exit_price = 'SL', active_trade['sl']
                elif current_candle['high'] >= active_trade['tp']: result, exit_price = 'TP', active_trade['tp']
            elif active_trade['type'] == 'SHORT':
                if current_candle['high'] >= active_trade['sl']: result, exit_price = 'SL', active_trade['sl']
                elif current_candle['low'] <= active_trade['tp']: result, exit_price = 'TP', active_trade['tp']
            
            if result:
                pnl_percent = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                if active_trade['type'] == 'SHORT': pnl_percent = -pnl_percent
                current_equity *= (1 + pnl_percent)
                equity_curve.append(current_equity)
                active_trade['result'] = result
                trades.append(active_trade)
                active_trade = None

        if not active_trade:
            signal = find_pullback_signal("OPTIMIZER", current_market_data, params)
            if signal:
                active_trade = {
                    'type': signal['signal_type'], 'entry_price': signal['entry_price'],
                    'sl': signal['stop_loss'], 'tp': signal['take_profit']
                }

    if not trades:
        return {"profit_factor": 0, "max_drawdown": 100, "gross_pl": 0, "total_trades": 0}

    gross_profit = sum(abs(t['tp'] - t['entry_price']) for t in trades if t['result'] == 'TP')
    gross_loss = sum(abs(t['sl'] - t['entry_price']) for t in trades if t['result'] == 'SL')
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    peak = 1.0
    max_drawdown = 0
    for equity in equity_curve:
        if equity > peak: peak = equity
        drawdown = (peak - equity) / peak
        if drawdown > max_drawdown: max_drawdown = drawdown

    return {
        "profit_factor": round(profit_factor, 2), "max_drawdown": round(max_drawdown * 100, 2),
        "gross_pl": round(gross_profit - gross_loss, 4), "total_trades": len(trades)
    }

def optimize_asset(symbol, years, param_space, num_random_tests):
    """Usa una Randomized Search per trovare i parametri ottimali."""
    logging.info(f"--- OTTIMIZZAZIONE RANDOMIZED AVVIATA per {symbol} su {years} anni ---")
    start_date = f"{years} years ago UTC"
    try:
        klines = binance_client.get_historical_klines(symbol, "1h", start_date)
        if not klines: logging.warning(f"Nessun dato per {symbol}. Salto."); return None
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = pd.to_numeric(df[col])
        logging.info(f"Dati per {symbol} caricati ({len(df)} candele).")
    except Exception as e:
        logging.error(f"Errore download dati per {symbol}: {e}. Salto."); return None

    # --- MODIFICA CHIAVE: RANDOMIZED SEARCH ---
    keys, values = zip(*param_space.items())
    # Genera tutte le combinazioni possibili
    all_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    # Se il numero di test richiesti è maggiore di quelle possibili, testale tutte
    if num_random_tests >= len(all_combinations):
        param_combinations = all_combinations
    else:
        # Altrimenti, estrai un campione casuale
        param_combinations = random.sample(all_combinations, num_random_tests)
    
    total_combinations = len(param_combinations)
    logging.info(f"Verranno testate {total_combinations} combinazioni casuali di parametri.")

    best_profit_factor = -1
    best_params_package = None
    
    for i, params in enumerate(param_combinations):
        result = run_single_backtest(df.copy(), params)
        print(f"\r  Test {i+1:>4}/{total_combinations} | PF: {result['profit_factor']:>4.2f} | DD: {result['max_drawdown']:>5.2f}% | P/L: {result['gross_pl']:>9.2f} | Trades: {result['total_trades']:<4}", end="")

        if result['profit_factor'] > best_profit_factor and result['total_trades'] > 20:
            best_profit_factor = result['profit_factor']
            best_params_package = {'params': params, 'performance': result}
        elif result['profit_factor'] == best_profit_factor and best_params_package and result['total_trades'] < best_params_package['performance']['total_trades']:
             best_params_package = {'params': params, 'performance': result}

    print()
    logging.info(f"--- OTTIMIZZAZIONE COMPLETATA per {symbol} ---")
    return best_params_package

if __name__ == "__main__":
    with open('parameters_space.json', 'r') as f:
        param_space = json.load(f)

    # --- CONFIGURAZIONE DEL COMPROMESSO ---
    SYMBOLS_TO_OPTIMIZE = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", 
        "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT", "EURUSDT", "GBPUSDT", "XAUUSDT"
    ]
    YEARS_TO_OPTIMIZE = 2  # RIDOTTO DA 3 A 2 ANNI
    RANDOM_TESTS_PER_ASSET = 500 # NUMERO DI TEST CASUALI DA ESEGUIRE (invece di 3000+)
    
    final_strategies = {"defaults": {}, "groups": {}, "overrides": {}}

    for symbol in SYMBOLS_TO_OPTIMIZE:
        best_package = optimize_asset(symbol, YEARS_TO_OPTIMIZE, param_space, RANDOM_TESTS_PER_ASSET)
        if best_package:
            print(f"\nRISULTATO MIGLIORE per {symbol}:")
            full_results = best_package['params'].copy()
            full_results.update(best_package['performance'])
            print(json.dumps(full_results, indent=2))
            final_strategies["overrides"][symbol] = best_package['params']

    output_filename = f"generated_strategies_random_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_filename, 'w') as f:
        json.dump(final_strategies, f, indent=2)
    
    logging.info(f"\nFile di strategie ottimizzate generato: {output_filename}")
