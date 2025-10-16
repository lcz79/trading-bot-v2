# optimizer.py - v4.0 (Multi-Logic Optimizer)
import pandas as pd
import logging
import json
import itertools
import random
from datetime import datetime, timezone
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# Assicuriamoci di importare dal posto giusto, che ora è strategy_generator
from strategy_generator import evaluate_strategy_extended
from data_sources import binance_client


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_single_backtest(df_full, params, strategy_logic):
    """Backtester leggero che ora accetta una logica di strategia variabile."""
    trades, active_trade = [], None
    start_index = max(params.get('ema_slow', 200), params.get('atr_len', 14)) + 10
    equity_curve, current_equity = [1.0], 1.0

    for i in range(start_index, len(df_full)):
        current_market_data = df_full.iloc[0:i]
        if active_trade:
            c = current_market_data.iloc[-1]
            result, exit_price = None, None
            if active_trade['type'] == 'LONG' and c['low'] <= active_trade['sl']: result, exit_price = 'SL', active_trade['sl']
            elif active_trade['type'] == 'LONG' and c['high'] >= active_trade['tp']: result, exit_price = 'TP', active_trade['tp']
            elif active_trade['type'] == 'SHORT' and c['high'] >= active_trade['sl']: result, exit_price = 'SL', active_trade['sl']
            elif active_trade['type'] == 'SHORT' and c['low'] <= active_trade['tp']: result, exit_price = 'TP', active_trade['tp']
            if result:
                pnl = (exit_price - active_trade['entry']) / active_trade['entry']
                if active_trade['type'] == 'SHORT': pnl = -pnl
                current_equity *= (1 + pnl)
                equity_curve.append(current_equity)
                active_trade['result'] = result
                trades.append(active_trade)
                active_trade = None
        if not active_trade:
            signal = evaluate_strategy_extended(current_market_data, params, strategy_logic)
            if signal: active_trade = signal.copy()

    if not trades: return {"profit_factor": 0, "max_drawdown": 100, "total_trades": 0, "gross_pl": 0}

    gross_profit = sum(abs(t['tp'] - t['entry']) for t in trades if t['result'] == 'TP')
    gross_loss = sum(abs(t['sl'] - t['entry']) for t in trades if t['result'] == 'SL')
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    peak = max(equity_curve) if equity_curve else 1.0
    max_drawdown = max([(peak - val) / peak for val in equity_curve]) * 100 if equity_curve else 100

    return {
        "profit_factor": round(profit_factor, 2), 
        "max_drawdown": round(max_drawdown, 2), 
        "total_trades": len(trades),
        "gross_pl": round(gross_profit - gross_loss, 4)
    }

def optimize_asset_logic(symbol, years, param_space, num_tests, strategy_logic):
    """Funzione core che ottimizza i parametri per una data logica di strategia."""
    logging.info(f"--- OTTIMIZZAZIONE per {symbol} sulla logica '{strategy_logic['name']}' ---")
    start_date = f"{years} years ago UTC"
    try:
        klines = binance_client.get_historical_klines(symbol, "1h", start_date)
        if not klines: logging.warning(f"Nessun dato per {symbol}."); return None
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = pd.to_numeric(df[col])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    except Exception as e:
        logging.error(f"Errore dati per {symbol}: {e}"); return None

    keys, values = zip(*param_space.items())
    all_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    param_combinations = random.sample(all_combinations, min(num_tests, len(all_combinations)))
    
    logging.info(f"Test di {len(param_combinations)} combinazioni di parametri...")
    best_pf, best_package = -1, None
    
    for i, params in enumerate(param_combinations):
        result = run_single_backtest(df.copy(), params, strategy_logic)
        print(f"\r  Test {i+1:>4}/{len(param_combinations)} | PF: {result['profit_factor']:>4.2f} | DD: {result['max_drawdown']:>5.2f}% | P/L: {result['gross_pl']:>9.2f} | Trades: {result['total_trades']:<4}", end="")
        if result['profit_factor'] > best_pf and result['total_trades'] > 20: # Minimo 20 trade per validità statistica
            best_pf = result['profit_factor']
            best_package = {'params': params, 'performance': result, 'logic_name': strategy_logic['name']}

    print()
    return best_package

if __name__ == "__main__":
    try:
        with open('hall_of_fame_new.json', 'r') as f:
            candidate_logics = json.load(f)
    except FileNotFoundError:
        logging.error("File 'hall_of_fame_new.json' non trovato. Esegui prima strategy_generator.py.")
        exit()

    with open('parameters_space.json', 'r') as f:
        param_space = json.load(f)

    STRATEGY_BLUEPRINTS = {
        "Pullback_v13_Original": {"name": "Pullback_v13_Original", "trend_filter": "check_trend_condition", "entry_condition": "check_pullback_entry_condition", "exit_logic": "calculate_sl_tp"},
        "EMA_Cross_v1_WithTrendFilter": {"name": "EMA_Cross_v1_WithTrendFilter", "trend_filter": "check_trend_condition", "entry_condition": "check_ema_cross_entry_condition", "exit_logic": "calculate_sl_tp"},
        "EMA_Cross_v1_Pure": {"name": "EMA_Cross_v1_Pure", "trend_filter": None, "entry_condition": "check_ema_cross_entry_condition", "exit_logic": "calculate_sl_tp"}
    }

    YEARS_TO_OPTIMIZE = 2
    RANDOM_TESTS_PER_ASSET = 300

    production_strategies = {}
    
    with open('hall_of_fame_strategies.json', 'r') as f:
        btc_strategy = json.load(f)
        production_strategies.update(btc_strategy)
        logging.info("Caricata la strategia BTC pre-approvata da 'hall_of_fame_strategies.json'")

    for asset, candidate in candidate_logics.items():
        logic_name = candidate['name']
        if logic_name in STRATEGY_BLUEPRINTS:
            strategy_logic_to_optimize = STRATEGY_BLUEPRINTS[logic_name]
            
            best_package = optimize_asset_logic(asset, YEARS_TO_OPTIMIZE, param_space, RANDOM_TESTS_PER_ASSET, strategy_logic_to_optimize)
            
            if best_package and best_package['performance']['profit_factor'] > 1.15: # Soglia di qualità finale
                logging.info(f"✅ Strategia profittevole trovata e ottimizzata per {asset}!")
                print(json.dumps(best_package, indent=4))
                production_strategies[asset] = best_package
            else:
                logging.warning(f"❌ Nessuna strategia robusta trovata per {asset} dopo l'ottimizzazione.")

    output_filename = f"production_strategies_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.json"
    with open(output_filename, 'w') as f:
        json.dump(production_strategies, f, indent=4)
    
    logging.info(f"\n🚀 File finale con strategie di produzione salvato in: {output_filename}")
