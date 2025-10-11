# backtest_engine.py - Il motore di backtesting richiamabile
import pandas as pd
from datetime import datetime, timedelta, timezone

import config
from api_clients.data_client import FinancialDataClient
from analysis.session_clock import in_session, is_eod_window
from analysis.strategy_vwap_rev import vwap_reversion_intraday

def run_single_backtest(asset: str, start_date_str: str, end_date_str: str, vwap_params: dict):
    """Esegue un singolo backtest per una data combinazione di parametri."""
    
    data_client = FinancialDataClient()
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_ms, end_ms = int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

    df_trigger_hist = data_client.get_klines(asset, config.OPERATIONAL_TIMEFRAME, start_time=start_ms, end_time=end_ms)
    if df_trigger_hist is None or df_trigger_hist.empty: return None

    start_warmup_ms = int((start_dt - timedelta(days=20)).timestamp() * 1000)
    df_trigger_warmup = data_client.get_klines(asset, config.OPERATIONAL_TIMEFRAME, start_time=start_warmup_ms, end_time=start_ms)
    df_trigger_full = pd.concat([df_trigger_warmup, df_trigger_hist]) if df_trigger_warmup is not None else df_trigger_hist

    df_trigger_full.ta.atr(length=config.ATR_PERIOD, append=True)
    atr_col = f"ATRr_{config.ATR_PERIOD}"

    initial_equity, equity, trades, current_trade = 10000, 10000, [], None

    for timestamp, candle in df_trigger_hist.iterrows():
        now = timestamp.to_pydatetime()

        if current_trade:
            close_reason, exit_price = None, candle['close']
            if current_trade['side'] == 'Long':
                if candle['low'] <= current_trade['sl']: close_reason, exit_price = "Stop Loss", current_trade['sl']
                elif candle['high'] >= current_trade['tp']: close_reason, exit_price = "Take Profit", current_trade['tp']
            elif current_trade['side'] == 'Short':
                if candle['high'] >= current_trade['sl']: close_reason, exit_price = "Stop Loss", current_trade['sl']
                elif candle['low'] <= current_trade['tp']: close_reason, exit_price = "Take Profit", current_trade['tp']
            
            if is_eod_window(now) and not close_reason: close_reason = "EOD Flatten"
            
            if close_reason:
                pnl = (exit_price - current_trade['entry_price']) * (1 if current_trade['side'] == 'Long' else -1)
                equity += pnl
                current_trade.update({'exit_price': exit_price, 'exit_time': now, 'pnl': pnl, 'close_reason': close_reason})
                trades.append(current_trade)
                current_trade = None

        if not current_trade and in_session(now):
            df_slice = df_trigger_full.loc[:timestamp]
            
            signals = vwap_reversion_intraday(df_slice, asset=asset, **vwap_params) or []
            
            if signals:
                best_signal = signals[0]
                current_trade = {
                    'entry_time': now, 'entry_price': best_signal['entry_price'], 'side': best_signal['side'],
                    'sl': best_signal['sl'], 'tp': best_signal['tp']
                }

    if not trades:
        return {'pnl': 0, 'win_rate': 0, 'trades': 0, 'profit_factor': 0}
        
    report_df = pd.DataFrame(trades)
    total_pnl = report_df['pnl'].sum()
    win_rate = len(report_df[report_df['pnl'] > 0]) / len(report_df) * 100
    total_wins = report_df[report_df['pnl'] > 0]['pnl'].sum()
    total_losses = abs(report_df[report_df['pnl'] < 0]['pnl'].sum())
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

    return {
        'pnl': round(total_pnl, 2),
        'win_rate': round(win_rate, 2),
        'trades': len(trades),
        'profit_factor': round(profit_factor, 2)
    }
