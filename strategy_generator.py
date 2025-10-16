# strategy_generator_v2.2.py - Focused Multi-Asset Strategy Generator
# Esclude asset già analizzati per ottimizzare il tempo di ricerca.

import pandas as pd
import logging
import json
from datetime import datetime, timezone
import warnings
import os

from data_sources import binance_client
from analysis.market_analysis import (
    add_indicators, check_trend_condition, 
    check_pullback_entry_condition, calculate_sl_tp
)

warnings.simplefilter(action='ignore', category=FutureWarning)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def check_ema_cross_entry_condition(df, trend, params):
    prev_candle = df.iloc[-2]
    prev2_candle = df.iloc[-3]
    ema_fast_col = f"EMA_{params['ema_fast']}"
    ema_slow_col = f"EMA_{params['ema_slow']}"
    if trend == 'UP':
        return prev2_candle[ema_fast_col] < prev2_candle[ema_slow_col] and prev_candle[ema_fast_col] > prev_candle[ema_slow_col]
    if trend == 'DOWN':
        return prev2_candle[ema_fast_col] > prev2_candle[ema_slow_col] and prev_candle[ema_fast_col] < prev_candle[ema_slow_col]
    return False


def evaluate_strategy_extended(df_market_data, params, strategy_logic):
    df = add_indicators(df_market_data.copy(), params)
    trend = 'UP'
    if strategy_logic.get('trend_filter') == 'check_trend_condition':
        trend = check_trend_condition(df, params)
        if trend == 'NONE': return None
    entry_condition = strategy_logic.get('entry_condition')
    entry_signal = False
    if entry_condition == 'check_pullback_entry_condition':
        entry_signal = check_pullback_entry_condition(df, trend, params)
    elif entry_condition == 'check_ema_cross_entry_condition':
        entry_signal = check_ema_cross_entry_condition(df, trend, params)
    if not entry_signal: return None
    entry_price, stop_loss, take_profit = calculate_sl_tp(df, trend, params)
    if not all([entry_price, stop_loss, take_profit]): return None
    return {
        "timestamp": df.iloc[-1]['timestamp'], "type": "LONG" if trend == 'UP' else "SHORT",
        "entry": entry_price, "sl": stop_loss, "tp": take_profit
    }


def run_logic_backtest(df_full, params, strategy_logic):
    trades, active_trade = [], None
    start_index = max(params.get('ema_slow', 200), params.get('atr_len', 14)) + 10
    for i in range(start_index, len(df_full)):
        current_market_data = df_full.iloc[0:i]
        if active_trade:
            c = current_market_data.iloc[-1]
            result = None
            if active_trade['type'] == 'LONG' and c['low'] <= active_trade['sl']: result = 'SL'
            elif active_trade['type'] == 'LONG' and c['high'] >= active_trade['tp']: result = 'TP'
            elif active_trade['type'] == 'SHORT' and c['high'] >= active_trade['sl']: result = 'SL'
            elif active_trade['type'] == 'SHORT' and c['low'] <= active_trade['tp']: result = 'TP'
            if result:
                active_trade['result'] = result
                trades.append(active_trade)
                active_trade = None
        if not active_trade:
            signal = evaluate_strategy_extended(current_market_data, params, strategy_logic)
            if signal: active_trade = signal.copy()
    if not trades:
        return {"name": strategy_logic['name'], "profit_factor": 0, "total_trades": 0, "win_rate": 0, "avg_r_per_trade": 0}
    gross_profit = sum(abs(t['tp'] - t['entry']) for t in trades if t['result'] == 'TP')
    gross_loss = sum(abs(t['sl'] - t['entry']) for t in trades if t['result'] == 'SL')
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    win_trades = len([t for t in trades if t['result'] == 'TP'])
    win_rate = round((win_trades / len(trades)) * 100, 2) if trades else 0
    avg_r = round((gross_profit - gross_loss) / len(trades), 4) if trades else 0
    return {"name": strategy_logic['name'], "profit_factor": round(profit_factor, 2), "total_trades": len(trades), "win_rate": win_rate, "avg_r_per_trade": avg_r}


def prepare_dataframe(klines):
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
    return df


if __name__ == "__main__":
    STRATEGY_BLUEPRINTS = [
        {"name": "Pullback_v13_Original", "trend_filter": "check_trend_condition", "entry_condition": "check_pullback_entry_condition", "exit_logic": "calculate_sl_tp"},
        {"name": "EMA_Cross_v1_WithTrendFilter", "trend_filter": "check_trend_condition", "entry_condition": "check_ema_cross_entry_condition", "exit_logic": "calculate_sl_tp"},
        {"name": "EMA_Cross_v1_Pure", "trend_filter": None, "entry_condition": "check_ema_cross_entry_condition", "exit_logic": "calculate_sl_tp"}
    ]
    with open('hall_of_fame_strategies.json', 'r') as f:
        base_params = json.load(f)['BTCUSDT']['params']
    
    # --- MODIFICA CHIAVE: LISTA ASSET MIRATA ---
    ASSETS = [
        # "BTCUSDT", # Escluso: strategia già in hall_of_fame_strategies.json
        # "ETHUSDT", # Escluso: candidato già trovato, in attesa di ottimizzazione
        "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", 
        "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT", "EURUSDT", "GBPUSDT", 
        "XAUUSDT", # Oro (fallirà su Binance, ma lo lasciamo per completezza)
    ]

    YEARS_TO_TEST = 2
    start_date = f"{YEARS_TO_TEST} years ago UTC"
    
    # Carichiamo i risultati esistenti per non sovrascriverli
    try:
        with open('hall_of_fame_new.json', 'r') as f:
            top_strategies = json.load(f)
        logging.info("Caricato 'hall_of_fame_new.json' esistente. Verrà aggiornato.")
    except FileNotFoundError:
        top_strategies = {}
        logging.info("Nessun 'hall_of_fame_new.json' esistente. Verrà creato un nuovo file.")

    all_results = []
    for asset in ASSETS:
        # Controlla se l'asset è già stato analizzato
        if asset in top_strategies:
            logging.info(f"Asset {asset} già presente nel file dei risultati. Salto.")
            continue

        logging.info(f"--- ANALISI STRATEGICA PER {asset} ---")
        try:
            klines = binance_client.get_historical_klines(asset, "1h", start_date)
            if not klines:
                logging.warning(f"Nessun dato per {asset}. Salto.")
                continue
            df = prepare_dataframe(klines)
            logging.info(f"Dati per {asset} caricati ({len(df)} candele).")
        except Exception as e:
            logging.error(f"Errore download dati {asset}: {e}")
            continue
        
        asset_run_results = []
        for blueprint in STRATEGY_BLUEPRINTS:
            logging.info(f"Test: {blueprint['name']}...")
            result = run_logic_backtest(df.copy(), base_params, blueprint)
            result['asset'] = asset
            all_results.append(result)
            asset_run_results.append(result)
        
        # Aggiungiamo il miglior risultato per l'asset corrente, se supera la soglia di qualità
        best_for_asset = sorted(asset_run_results, key=lambda x: x['profit_factor'], reverse=True)[0]
        if best_for_asset['profit_factor'] > 1.0:
            top_strategies[asset] = best_for_asset
            
    # Stampa la classifica completa di tutti i test eseguiti in questo run
    if all_results:
        sorted_results = sorted(all_results, key=lambda x: x['profit_factor'], reverse=True)
        results_df = pd.DataFrame(sorted_results)
        print("\n" + "="*80)
        print(f" CLASSIFICA STRATEGIE (solo per i nuovi asset testati)")
        print("="*80)
        print(results_df.to_string(index=False))
        print("="*80)
    
    with open('hall_of_fame_new.json', 'w') as f:
        json.dump(top_strategies, f, indent=4)
    
    user_login = os.getlogin()
    current_utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"🏆 File 'hall_of_fame_new.json' aggiornato con i nuovi candidati | By {user_login} | {current_utc_time}")
