import argparse
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

from api_clients import financial_data_client
from analysis import market_analysis
from config import ASSETS_TO_ANALYZE

def run_backtest(symbol, timeframe_str, data_source):
    print("="*80)
    print(f"🚀 AVVIO BACKTEST 'MEAN REVERSION V3' per {symbol} | TF: {timeframe_str}")
    print("="*80)

    print("-> Caricamento dati storici...")
    df_full = financial_data_client.get_data(symbol, timeframe_str, limit=3000, source=data_source)
    if df_full is None or len(df_full) < 200:
        print("❌ ERRORE: Dati storici insufficienti.")
        return
    print(f"✅ Dati caricati: {len(df_full)} candele dal {df_full.index[0]} al {df_full.index[-1]}")

    print("-> Avvio simulazione...")
    trades, active_trade = [], None
    
    for i in range(200, len(df_full)):
        df_slice = df_full.iloc[:i]
        current_candle = df_slice.iloc[-1]
        
        if active_trade:
            pnl, close_reason = 0, None
            if active_trade['side'] == 'LONG':
                if current_candle['low'] <= active_trade['stop_loss']: close_reason, pnl = "Stop Loss", active_trade['stop_loss'] - active_trade['entry_price']
                elif current_candle['high'] >= active_trade['take_profit']: close_reason, pnl = "Take Profit", active_trade['take_profit'] - active_trade['entry_price']
            elif active_trade['side'] == 'SHORT':
                if current_candle['high'] >= active_trade['stop_loss']: close_reason, pnl = "Stop Loss", active_trade['entry_price'] - active_trade['stop_loss']
                elif current_candle['low'] <= active_trade['take_profit']: close_reason, pnl = "Take Profit", active_trade['entry_price'] - active_trade['take_profit']
            if close_reason:
                active_trade.update({
                    'exit_price': active_trade['entry_price'] + pnl, 'exit_date': current_candle.name,
                    'pnl': pnl, 'pnl_percent': (pnl / active_trade['entry_price']) * 100,
                    'closed_by': close_reason
                })
                trades.append(active_trade)
                active_trade = None
        
        if not active_trade:
            # ORA USIAMO LA NUOVA STRATEGIA "MEAN REVERSION"
            signal, confidence, details = market_analysis.analyze_mean_reversion_pro(df_slice)
            
            if signal != "NEUTRAL":
                entry_price = current_candle['close']
                stop_loss, take_profit = market_analysis.calculate_sl_tp(df_slice, signal, entry_price)

                if stop_loss and take_profit:
                    print(f"  -> {signal} Eseguito a {entry_price:.2f} in data {current_candle.name}")
                    active_trade = {
                        'entry_date': current_candle.name,
                        'entry_price': entry_price,
                        'side': 'LONG' if 'LONG' in signal else 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'details': details
                    }

    print("✅ Simulazione completata.")
    print("\n" + "="*80)
    print("📊 REPORT PERFORMANCE BACKTEST: 'MEAN REVERSION V3'")
    print("="*80)
    if not trades:
        print("Nessun trade eseguito.")
        return
    df_trades = pd.DataFrame(trades)
    total_trades, winning_trades = len(df_trades), df_trades[df_trades['pnl'] > 0]
    losing_trades = df_trades[df_trades['pnl'] <= 0]
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
    print(f"Asset: {symbol} | Timeframe: {timeframe_str}")
    print(f"Periodo Testato:\t\t{df_full.index[200].date()} -> {df_full.index[-1].date()}")
    print("-" * 50)
    print(f"Totale Trade:\t\t\t{total_trades}")
    print(f"Win Rate:\t\t\t{win_rate:.2f}%")
    print(f"Profit Factor:\t\t\t{profit_factor:.2f}")
    print(f"Profitto/Perdita Totale:\t{df_trades['pnl_percent'].sum():.2f}%")
    print("-" * 50)
    print("Dettaglio Trade:")
    print(df_trades[['entry_date', 'side', 'entry_price', 'exit_date', 'exit_price', 'pnl_percent', 'closed_by']])
    print("="*80)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backtest con strategia 'Mean Reversion V3'.")
    parser.add_argument('--symbol', required=True, help="Simbolo (es. BTCUSDT)")
    parser.add_argument('--timeframe', required=True, help="Timeframe (es. 60, 240, 1h, 1d)")
    args = parser.parse_args()
    asset_config = next((item for item in ASSETS_TO_ANALYZE if item["symbol"] == args.symbol), None)
    if not asset_config:
        print(f"❌ ERRORE: Asset '{args.symbol}' non trovato in config.py")
    else:
        run_backtest(args.symbol, args.timeframe, asset_config['source'])
