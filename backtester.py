# backtester.py - v2.0 (Backtest su asset multipli con report finale)
import pandas as pd
import logging
from datetime import datetime

# Assicurati che questi import funzionino dalla root del progetto
from data_sources import binance_client
from etl_service import load_strategies, get_params_for_symbol
from analysis.market_analysis import find_pullback_signal

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_backtest(symbol, years, all_settings):
    """
    Esegue un backtest completo per un singolo simbolo.
    Restituisce un dizionario con i risultati, o None in caso di errore.
    """
    
    logging.info(f"--- INIZIO BACKTEST per {symbol} su {years} anni ---")
    
    # 1. Carica i dati storici
    start_date = f"{years} years ago UTC"
    try:
        klines = binance_client.get_historical_klines(symbol, "1h", start_date)
        if not klines:
            logging.warning(f"Nessun dato storico trovato per {symbol} su Binance. Potrebbe non essere disponibile. Salto.")
            return None
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        logging.info(f"Dati storici per {symbol} caricati: {len(df)} candele.")
    except Exception as e:
        logging.error(f"Impossibile scaricare i dati per {symbol}: {e}. Salto.")
        return None

    # 2. Prepara i parametri della strategia per questo simbolo
    params = get_params_for_symbol(symbol, all_settings)
    logging.info(f"Parametri strategia: {params}")

    # 3. Itera attraverso i dati e simula i trade
    trades = []
    active_trade = None
    start_index = max(params.get('ema_slow', 200), params.get('atr_len', 14)) + 10

    for i in range(start_index, len(df)):
        current_market_data = df.iloc[0:i]
        
        if active_trade:
            current_candle = current_market_data.iloc[-1]
            if active_trade['type'] == 'LONG':
                if current_candle['low'] <= active_trade['sl']: active_trade['result'] = 'SL'
                elif current_candle['high'] >= active_trade['tp']: active_trade['result'] = 'TP'
            elif active_trade['type'] == 'SHORT':
                if current_candle['high'] >= active_trade['sl']: active_trade['result'] = 'SL'
                elif current_candle['low'] <= active_trade['tp']: active_trade['result'] = 'TP'
            
            if 'result' in active_trade:
                trades.append(active_trade)
                active_trade = None

        if not active_trade:
            signal = find_pullback_signal(symbol, current_market_data, params)
            if signal:
                active_trade = {
                    'type': signal['signal_type'], 'entry_price': signal['entry_price'],
                    'sl': signal['stop_loss'], 'tp': signal['take_profit']
                }

    # 4. Calcola i risultati
    if not trades:
        logging.warning(f"Nessun trade eseguito per {symbol} durante il backtest.")
        return {
            "Symbol": symbol, "Total Trades": 0, "Wins": 0, "Losses": 0,
            "Win Rate (%)": 0, "Gross P/L": 0
        }

    wins = len([t for t in trades if t['result'] == 'TP'])
    losses = len(trades) - wins
    total_trades = len(trades)
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    total_profit = 0
    for trade in trades:
        profit_per_trade = 0
        if trade['result'] == 'TP':
            profit_per_trade = abs(trade['tp'] - trade['entry_price'])
        else: # SL
            profit_per_trade = -abs(trade['sl'] - trade['entry_price'])
        
        if trade['type'] == 'SHORT':
            profit_per_trade = -profit_per_trade
            
        total_profit += profit_per_trade

    return {
        "Symbol": symbol,
        "Total Trades": total_trades,
        "Wins": wins,
        "Losses": losses,
        "Win Rate (%)": round(win_rate, 2),
        "Gross P/L": round(total_profit, 4)
    }

if __name__ == "__main__":
    strategy_settings = load_strategies('optimal_strategies.json')
    if not strategy_settings:
        logging.error("Impossibile eseguire il backtest: file strategie non trovato.")
    else:
        # --- LISTA COMPLETA DEGLI ASSET DA TESTARE ---
        SYMBOLS_TO_TEST = [
            # Crypto
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", 
            "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT",
            # Forex (su Binance sono vs USDT/BUSD)
            "EURUSDT", "GBPUSDT", 
            # Materie Prime (Oro vs USDT)
            "XAUUSDT"
            # Nota: Indici (NAS100, SPX500) e alcune materie prime (WTIUSD) 
            # non sono tipicamente disponibili su Binance Spot/Futures con questi nomi.
            # Verranno scartati automaticamente se non trovati.
        ]
        YEARS_TO_TEST = 3
        
        all_results = []
        for symbol in SYMBOLS_TO_TEST:
            result = run_backtest(symbol, YEARS_TO_TEST, strategy_settings)
            if result:
                all_results.append(result)
        
        if all_results:
            # Creazione e stampa della tabella riassuntiva
            results_df = pd.DataFrame(all_results)
            print("\n\n" + "="*80)
            print(" " * 25 + "RISULTATI COMPLESSIVI DEL BACKTEST")
            print("="*80)
            print(f"Strategia: v13.0 | Periodo: {YEARS_TO_TEST} anni")
            print(results_df.to_string(index=False))
            print("="*80)
