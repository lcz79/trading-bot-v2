# backtester.py - v11.0.0 (The Regime-Aware Engine)
# ----------------------------------------------------------------
# - IMPLEMENTAZIONE DIRETTIVA CONSIGLIO #8:
#   Introdotto il "Market Regime Detector" basato sull'indicatore ADX.
# - La strategia Mean Reversion ora si attiva SOLO se il mercato è
#   in un regime di "RANGE" (ADX < 25), come suggerito dal Consiglio.
# - Questo aggiunge un filtro di contesto strategico per evitare di
#   operare contro trend troppo forti.
# ----------------------------------------------------------------

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from tqdm import tqdm

from api_clients.data_client import FinancialDataClient

# --- Configurazione ---
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

ASSETS_TO_BACKTEST = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT']
TIMEFRAME_TO_TEST = 'D'
DATA_SOURCE = 'bybit'
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 0.02

# --- MOTORE STRATEGICO v9.0 con FILTRO DI REGIME ---
def find_regime_filtered_signals(df, rsi_len=14, rsi_low=30, rsi_high=70,
                                 vol_ma_len=20, vol_z_min=0.8,
                                 atr_len=14, sl_atr=1.5, tp_atr=2.0,
                                 adx_len=14, adx_threshold=25):
    out = []
    if df is None or len(df) < 100: return out

    # Indicatori
    df.ta.rsi(length=rsi_len, append=True)
    df.ta.atr(length=atr_len, append=True)
    df.ta.adx(length=adx_len, append=True) # Calcolo ADX

    rsi_col = f'RSI_{rsi_len}'
    atr_col = f'ATRr_{atr_len}'
    adx_col = f'ADX_{adx_len}'

    # Z-score del Volume
    vol_ma = df['volume'].rolling(vol_ma_len).mean()
    vol_std = df['volume'].rolling(vol_ma_len).std(ddof=0)
    df['vol_z'] = ((df['volume'] - vol_ma) / vol_std.replace(0, np.nan)).fillna(0.0)

    # Loop sui dati
    for i in range(len(df) - 2):
        T = df.iloc[i]
        T_plus_1 = df.iloc[i+1]
        
        # --- FILTRO DI REGIME ---
        # Se l'ADX è sopra la soglia, il mercato è in trend. Saltiamo.
        if T[adx_col] >= adx_threshold:
            continue

        # Se siamo qui, ADX < 25, quindi il mercato è in RANGE. Procediamo.
        
        # Setup LONG
        if T[rsi_col] <= rsi_low and T['vol_z'] >= vol_z_min:
            if T_plus_1['close'] > T['high']:
                entry_price = df.iloc[i+2]['open']; sl = T['low'] - (sl_atr * T[atr_col]); tp = entry_price + (tp_atr * T[atr_col])
                out.append({'side': 'LONG', 'entry_date': df.index[i+2], 'entry_price': entry_price, 'sl': sl, 'tp': tp})

        # Setup SHORT
        if T[rsi_col] >= rsi_high and T['vol_z'] >= vol_z_min:
            if T_plus_1['close'] < T['low']:
                entry_price = df.iloc[i+2]['open']; sl = T['high'] + (sl_atr * T[atr_col]); tp = entry_price - (tp_atr * T[atr_col])
                out.append({'side': 'SHORT', 'entry_date': df.index[i+2], 'entry_price': entry_price, 'sl': sl, 'tp': tp})
    return out

# (Le funzioni di backtest e main rimangono quasi identiche, ma chiamano la nuova funzione di scan)
def run_backtest_with_reporting(asset_symbol: str) -> (dict, list):
    data_client = FinancialDataClient()
    df = data_client.get_klines(asset_symbol, TIMEFRAME_TO_TEST, DATA_SOURCE, limit=1500)
    if df is None or df.empty: return (None, [])
    df.sort_index(ascending=True, inplace=True)
    
    signals = find_regime_filtered_signals(df) # <-- Chiamata alla nuova funzione
    
    if not signals:
        summary = {'asset': asset_symbol, 'total_trades': 0, 'winning_trades': 0, 'win_rate': 0, 'total_pnl': 0, 'pnl_perc': 0}
        return (summary, [])

    executed_trades = []; capital = INITIAL_CAPITAL
    for signal in signals:
        trade_risk = capital * RISK_PER_TRADE
        stop_loss_points = abs(signal['entry_price'] - signal['sl'])
        size = trade_risk / stop_loss_points if stop_loss_points > 0 else 0
        if size == 0: continue
        trade_outcome = {'status': 'OPEN', 'exit_date': None, 'pnl': 0}
        trade_df = df[df.index > signal['entry_date']]
        for index, candle in trade_df.iterrows():
            if signal['side'] == 'LONG':
                if candle['high'] >= signal['tp']: trade_outcome = {'status': 'TP', 'pnl': (signal['tp'] - signal['entry_price']) * size, 'exit_date': index}; break
                elif candle['low'] <= signal['sl']: trade_outcome = {'status': 'SL', 'pnl': (signal['sl'] - signal['entry_price']) * size, 'exit_date': index}; break
            elif signal['side'] == 'SHORT':
                if candle['low'] <= signal['tp']: trade_outcome = {'status': 'TP', 'pnl': (signal['entry_price'] - signal['tp']) * size, 'exit_date': index}; break
                elif candle['high'] >= signal['sl']: trade_outcome = {'status': 'SL', 'pnl': (signal['entry_price'] - signal['sl']) * size, 'exit_date': index}; break
        if trade_outcome['status'] != 'OPEN':
            capital += trade_outcome['pnl']; trade_details = {'asset': asset_symbol, 'entry_date': signal['entry_date'], 'side': signal['side'], 'entry_price': signal['entry_price'], 'sl': signal['sl'], 'tp': signal['tp'], 'exit_date': trade_outcome['exit_date'], 'status': trade_outcome['status'], 'pnl': trade_outcome['pnl']}; executed_trades.append(trade_details)

    total_pnl, win_rate, winning_trades = 0, 0, 0
    if executed_trades:
        report_df = pd.DataFrame(executed_trades); total_pnl = report_df['pnl'].sum(); winning_trades = len(report_df[report_df['pnl'] > 0]); win_rate = (winning_trades / len(executed_trades)) * 100 if executed_trades else 0
    summary = {'asset': asset_symbol, 'total_trades': len(executed_trades), 'winning_trades': winning_trades, 'win_rate': win_rate, 'total_pnl': total_pnl, 'pnl_perc': total_pnl / INITIAL_CAPITAL}
    return (summary, executed_trades)

def main():
    logging.info(f"--- Avvio Backtest di Portafoglio (Direttiva Consiglio #8: The Regime-Aware Engine) ---")
    all_summaries = []; all_trades = []
    for asset in tqdm(ASSETS_TO_BACKTEST, desc="Analisi Regime-Aware"):
        summary, trades = run_backtest_with_reporting(asset)
        if summary: all_summaries.append(summary)
        if trades: all_trades.extend(trades)
            
    summary_df = pd.DataFrame(all_summaries)
    print("\n" + "="*80); print("--- REPORT DI RIEPILOGO DEL PORTAFOGLIO (DIRETTIVA CONSIGLIO #8) ---"); print(f"Timeframe: {TIMEFRAME_TO_TEST} | Strategia: Mean Reversion con Filtro di Regime (ADX < 25)"); print("="*80)
    if not summary_df.empty:
        summary_df['pnl_perc'] = summary_df['pnl_perc'].map('{:.2%}'.format)
        summary_df['win_rate'] = summary_df['win_rate'].map('{:.2f}%'.format)
        summary_df['total_pnl'] = summary_df['total_pnl'].map('${:,.2f}'.format)
        print(summary_df[['asset', 'total_trades', 'winning_trades', 'win_rate', 'total_pnl', 'pnl_perc']].to_string(index=False))
    else: print("Nessun riepilogo da visualizzare.")
    print("="*80)

    if all_trades:
        trades_df = pd.DataFrame(all_trades); trades_df.to_csv("regime_filtered_trades_report.csv", index=False)
        logging.info("Report dettagliato dei trade (filtrato per regime) salvato in 'regime_filtered_trades_report.csv'.")
    else: logging.info("Nessun trade eseguito con il filtro di regime. Il report dettagliato non è stato creato.")

if __name__ == "__main__":
    main()
