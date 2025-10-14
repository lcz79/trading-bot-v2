# backtester.py - v1.0
import pandas as pd
import logging
from datetime import datetime

from data_sources import binance_client
from etl_service import load_strategies, get_params_for_symbol
from analysis.market_analysis import find_pullback_signal

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_backtest(symbol, years, all_settings):
    """Esegue un backtest completo per un singolo simbolo."""
    
    logging.info(f"--- INIZIO BACKTEST per {symbol} su {years} anni ---")
    
    # 1. Carica i dati storici
    start_date = f"{years} years ago UTC"
    try:
        klines = binance_client.get_historical_klines(symbol, "1h", start_date)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        logging.info(f"Dati storici per {symbol} caricati: {len(df)} candele.")
    except Exception as e:
        logging.error(f"Impossibile scaricare i dati per {symbol}: {e}")
        return

    # 2. Prepara i parametri della strategia per questo simbolo
    params = get_params_for_symbol(symbol, all_settings)
    logging.info(f"Parametri strategia: {params}")

    # 3. Itera attraverso i dati e simula i trade
    trades = []
    active_trade = None
    
    # Iniziamo dal primo indice possibile per avere abbastanza dati per gli indicatori
    start_index = max(params.get('ema_slow', 200), params.get('atr_len', 14)) + 5

    for i in range(start_index, len(df)):
        # Simula il passare del tempo: il nostro "presente" è la candela 'i'
        current_market_data = df.iloc[0:i]
        
        # Gestione trade attivo
        if active_trade:
            current_candle = current_market_data.iloc[-1]
            if active_trade['type'] == 'LONG':
                if current_candle['low'] <= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['result'] = 'SL'
                elif current_candle['high'] >= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['result'] = 'TP'
            elif active_trade['type'] == 'SHORT':
                if current_candle['high'] >= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['result'] = 'SL'
                elif current_candle['low'] <= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['result'] = 'TP'
            
            if 'result' in active_trade:
                trades.append(active_trade)
                active_trade = None

        # Cerca nuovi segnali solo se non c'è un trade attivo
        if not active_trade:
            signal = find_pullback_signal(symbol, current_market_data, params)
            if signal:
                logging.info(f"Segnale trovato il {signal['timestamp']}: {signal['signal_type']}")
                active_trade = {
                    'type': signal['signal_type'],
                    'entry_price': signal['entry_price'],
                    'sl': signal['stop_loss'],
                    'tp': signal['take_profit'],
                    'entry_time': signal['timestamp']
                }

    # 4. Calcola e stampa i risultati
    if not trades:
        logging.warning("Nessun trade eseguito durante il backtest.")
        return

    wins = [t for t in trades if t['result'] == 'TP']
    losses = [t for t in trades if t['result'] == 'SL']
    
    total_trades = len(trades)
    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
    
    total_profit = 0
    for trade in trades:
        if trade['type'] == 'LONG':
            total_profit += (trade['exit_price'] - trade['entry_price'])
        else:
            total_profit += (trade['entry_price'] - trade['exit_price'])

    logging.info(f"\n--- RISULTATI BACKTEST per {symbol} ---")
    print(f"Periodo:                {years} anni")
    print(f"Trade totali:           {total_trades}")
    print(f"Vittorie (TP):          {len(wins)}")
    print(f"Sconfitte (SL):         {len(losses)}")
    print(f"Win Rate:               {win_rate:.2f}%")
    # Nota: il profitto è solo un'indicazione, non tiene conto di size, commissioni, ecc.
    print(f"Profitto/Perdita lordo: {total_profit:.4f} (in punti/dollari dell'asset)")
    print("---------------------------------------\n")


if __name__ == "__main__":
    # Carica le configurazioni delle strategie
    strategy_settings = load_strategies('optimal_strategies.json')
    if not strategy_settings:
        logging.error("Impossibile eseguire il backtest: file strategie non trovato.")
    else:
        # --- CONFIGURA QUI IL TUO BACKTEST ---
        SYMBOLS_TO_TEST = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        YEARS_TO_TEST = 3
        
        for symbol in SYMBOLS_TO_TEST:
            run_backtest(symbol, YEARS_TO_TEST, strategy_settings)
