# intraday_backtester.py (v12.0 - "Polymorphic" Edition)
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone

import config
from api_clients.data_client import FinancialDataClient
from analysis.session_clock import in_session, is_eod_window
from analysis.intraday_rules import IntradayState, IntradayRules
from analysis.contextual_analyzer import get_market_bias
from analysis.strategy_vwap_rev import vwap_reversion_intraday
from analysis.strategy_orb import opening_range_breakout
from analysis.strategy_bb_squeeze import bollinger_squeeze_breakout

logging.basicConfig(level=logging.INFO, format='[BACKTEST V12] [%(levelname)s] %(message)s')

def run_backtest(asset: str, start_date_str: str, end_date_str: str):
    # Se l'asset non ha parametri ottimizzati, lo saltiamo
    if asset not in config.OPTIMIZED_PARAMS:
        logging.warning(f"Nessun parametro ottimizzato trovato per {asset}. Backtest saltato.")
        return

    logging.info(f"--- 🚀 INIZIO BACKTEST per {asset} (con DNA ottimizzato) 🚀 ---")
    
    data_client = FinancialDataClient()
    rules = IntradayRules()
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_ms, end_ms = int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

    df_trigger_hist = data_client.get_klines(asset, config.OPERATIONAL_TIMEFRAME, start_time=start_ms, end_time=end_ms)
    if df_trigger_hist is None or df_trigger_hist.empty: logging.error(f"Dati trigger non trovati per {asset}."); return
    df_context_hist = data_client.get_klines(asset, config.CONTEXT_TIMEFRAME, start_time=start_ms, end_time=end_ms)
    if df_context_hist is None or df_context_hist.empty: logging.error(f"Dati di contesto non trovati per {asset}."); return

    start_warmup_ms = int((start_dt - timedelta(days=40)).timestamp() * 1000)
    df_trigger_warmup = data_client.get_klines(asset, config.OPERATIONAL_TIMEFRAME, start_time=start_warmup_ms, end_time=start_ms)
    df_context_warmup = data_client.get_klines(asset, config.CONTEXT_TIMEFRAME, start_time=start_warmup_ms, end_time=start_ms)
    
    df_trigger_full = pd.concat([df_trigger_warmup, df_trigger_hist]) if df_trigger_warmup is not None else df_trigger_hist
    df_context_full = pd.concat([df_context_warmup, df_context_hist]) if df_context_warmup is not None else df_context_hist

    df_trigger_full.ta.atr(length=config.ATR_PERIOD, append=True)
    atr_col = f"ATRr_{config.ATR_PERIOD}"

    state, initial_equity, equity, trades, current_trade = IntradayState(), 10000, 10000, [], None
    market_bias, last_bias_check_day = 'SIDEWAYS', None

    for timestamp, candle in df_trigger_hist.iterrows():
        now = timestamp.to_pydatetime()
        current_day = now.date()
        if last_bias_check_day != current_day:
            df_context_slice = df_context_full.loc[:timestamp]
            market_bias = get_market_bias(df_context_slice)
            last_bias_check_day = current_day
        state.reset_if_new_day(now)

        if current_trade:
            # ... (logica di chiusura identica a prima) ...
            if config.TRAILING_STOP_ENABLED:
                atr_value = candle.get(atr_col, current_trade['initial_atr'])
                if current_trade['side'] == 'Long' and atr_value > 0:
                    new_sl = candle['high'] - atr_value * config.TRAILING_STOP_ATR_MULT;
                    if new_sl > current_trade['sl']: current_trade['sl'] = new_sl
                elif current_trade['side'] == 'Short' and atr_value > 0:
                    new_sl = candle['low'] + atr_value * config.TRAILING_STOP_ATR_MULT;
                    if new_sl < current_trade['sl']: current_trade['sl'] = new_sl
            close_reason, exit_price = None, candle['close']
            if current_trade['side'] == 'Long':
                if candle['low'] <= current_trade['sl']: close_reason, exit_price = "Trailing Stop", current_trade['sl']
                elif candle['high'] >= current_trade['tp']: close_reason, exit_price = "Take Profit", current_trade['tp']
            elif current_trade['side'] == 'Short':
                if candle['high'] >= current_trade['sl']: close_reason, exit_price = "Trailing Stop", current_trade['sl']
                elif candle['low'] <= current_trade['tp']: close_reason, exit_price = "Take Profit", current_trade['tp']
            if is_eod_window(now) and not close_reason: close_reason = "EOD Flatten"
            if close_reason:
                pnl = (exit_price - current_trade['entry_price']) * (1 if current_trade['side'] == 'Long' else -1)
                equity += pnl; rules.on_closed_trade(state, pnl, now)
                current_trade.update({'exit_price': exit_price, 'exit_time': now, 'pnl': pnl, 'close_reason': close_reason})
                trades.append(current_trade); current_trade = None

        if not current_trade:
            df_slice = df_trigger_full.loc[:timestamp]
            all_signals = []
            vwap_signals = vwap_reversion_intraday(df_slice, asset=asset) or []
            bb_signals = bollinger_squeeze_breakout(df_slice, bias=market_bias) or []
            orb_signals = opening_range_breakout(df_slice) or []
            all_signals.extend(vwap_signals); all_signals.extend(bb_signals); all_signals.extend(orb_signals)

            if all_signals:
                # ... (logica di scoring identica a prima) ...
                for signal in all_signals:
                    is_aligned = (market_bias == 'BULLISH' and signal['side'] == 'Long') or \
                                 (market_bias == 'BEARISH' and signal['side'] == 'Short')
                    if market_bias != 'SIDEWAYS':
                        if is_aligned: signal['score'] += 10
                        elif signal['strategy'] == 'VWAP-Reversion': signal['score'] -= 15
                valid_signals = [s for s in all_signals if s['score'] >= config.INTRADAY_SIGNAL_SCORE_THRESHOLD]
                if valid_signals:
                    best_signal = max(valid_signals, key=lambda s: s.get("score", 0))
                    is_allowed, reason = rules.allow_new_trade(now=now, equity=equity, state=state, signal_score=best_signal.get("score", 0))
                    if is_allowed:
                        rules.on_filled(state)
                        current_trade = {'entry_time': now, 'entry_price': best_signal['entry_price'], 'side': best_signal['side'], 'sl': best_signal['sl'], 'tp': best_signal['tp'], 'strategy': best_signal['strategy'], 'initial_atr': df_slice.iloc[-1].get(atr_col, 0)}

    print("\n" + "="*60); print(f"--- 📊 REPORT FINALE per {asset} 📊 ---")
    if not trades: print("Nessun trade eseguito."); print("="*60 + "\n"); return
    report_df = pd.DataFrame(trades); total_pnl = report_df['pnl'].sum()
    win_rate = len(report_df[report_df['pnl'] > 0]) / len(report_df) * 100
    profit_factor = report_df[report_df['pnl'] > 0]['pnl'].sum() / abs(report_df[report_df['pnl'] < 0]['pnl'].sum()) if abs(report_df[report_df['pnl'] < 0]['pnl'].sum()) > 0 else float('inf')
    print(f"Equity Iniziale: ${initial_equity:.2f}, Equity Finale: ${equity:.2f}"); print(f"PNL Totale: ${total_pnl:.2f} ({total_pnl / initial_equity * 100:.2f}%)")
    print(f"Numero Totale Trade: {len(report_df)}, Win Rate: {win_rate:.2f}%"); print(f"Profit Factor: {profit_factor:.2f}")
    print("--- DETTAGLIO TRADE ---"); print(report_df[['entry_time', 'side', 'strategy', 'pnl', 'close_reason']].round(2)); print("="*60 + "\n")

if __name__ == "__main__":
    for crypto_asset in config.ASSET_UNIVERSE:
        run_backtest(asset=crypto_asset, start_date_str=config.BACKTEST_START_DATE, end_date_str=config.BACKTEST_END_DATE)
    print("✅ TUTTI I BACKTEST POLIMORFICI SONO STATI COMPLETATI. ✅")
