import pandas as pd
import pandas_ta as ta
from api_clients import bybit_client, yahoo_client, external_apis

# ... (le funzioni di analisi come analyze_trend_following etc. sono complesse, le ometto per brevità ma le includo nel blocco completo sotto)

def get_fundamental_quality_score(asset, crypto_bulk_data):
    symbol = asset['symbol']
    source = asset['source']
    try:
        if source == 'Binance':
            if not crypto_bulk_data or symbol not in crypto_bulk_data:
                return 0, {'Errore': 'Dati metriche crypto non disponibili'}
            metrics = crypto_bulk_data[symbol]
            market_cap_rank = metrics.get('market_cap_rank')
            volume_24h = metrics.get('total_volume', 0)
            if symbol in ["BTCUSDT", "ETHUSDT"]:
                return 100, {'Market Cap Rank': market_cap_rank, 'Progetto': 'Fondamentale (BTC/ETH)', 'Volume 24h': f"€{volume_24h:,.0f}"}
            if not market_cap_rank or not volume_24h:
                 return 0, {'Errore': 'Dati market cap o volume mancanti'}
            score = 0
            if market_cap_rank <= 10: score += 70
            elif market_cap_rank <= 50: score += 20
            if volume_24h > 1_000_000_000: score += 30
            elif volume_24h > 500_000_000: score += 10
            return min(score, 100), {'Market Cap Rank': market_cap_rank, 'Volume 24h': f"€{volume_24h:,.0f}"}
        elif source == 'Yahoo':
            if symbol in ['SPY', 'QQQ']:
                 return 80, {'Info': 'ETF principale, punteggio di alta qualità assegnato.'}
            return 75, {'Info': 'Azione USA. Punteggio di alta qualità di default.'}
    except Exception as e:
        return 0, {'Errore': str(e)}

def analyze_trend_following(df):
    if df.empty or len(df) < 50: return None, "Dati insufficienti"
    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=14, append=True)
    df.dropna(inplace=True)
    if df.empty: return None, "Dati insufficienti dopo calcolo indicatori"
    last_candle = df.iloc[-1]
    if last_candle['EMA_21'] > last_candle['EMA_50'] and last_candle['close'] > last_candle['EMA_21'] and last_candle['RSI_14'] > 55:
        signal = "STRONG LONG"
        stop_loss = last_candle['close'] - (last_candle['ATRr_14'] * 2)
        take_profit = last_candle['close'] + (last_candle['ATRr_14'] * 3)
        details = {'Strategia': 'Trend Following', 'Razionale': 'Allineamento rialzista EMA, prezzo sopra media veloce, RSI forte.'}
        return {"Segnale": signal, "Prezzo": f"{last_candle['close']:,.4f}", "Stop Loss": f"{stop_loss:,.4f}", "Take Profit": f"{take_profit:,.4f}", "Dettagli": str(details)}, None
    return None, "Nessun segnale Trend Following"

def analyze_mean_reversion(df):
    if df.empty or len(df) < 20: return None, "Dati insufficienti"
    df.ta.bbands(length=20, std=2, append=True)
    required_cols = ['BBL_20_2.0', 'BBU_20_2.0', 'BBM_20_2.0']
    if not all(col in df.columns for col in required_cols):
        return None, "Errore nel calcolo delle Bande di Bollinger."
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=14, append=True)
    df.dropna(subset=required_cols + ['RSI_14', 'ATRr_14'], inplace=True)
    if df.empty: return None, "Dati insufficienti dopo calcolo indicatori"
    last_candle = df.iloc[-1]
    if last_candle['close'] <= last_candle['BBL_20_2.0'] and last_candle['RSI_14'] < 35:
        signal = "MEAN REVERSION LONG"
        stop_loss = last_candle['close'] - (last_candle['ATRr_14'] * 2)
        take_profit = last_candle['BBM_20_2.0']
        details = {'Strategia': 'Mean Reversion', 'Razionale': f"Prezzo sotto banda inferiore Bollinger e RSI basso ({last_candle['RSI_14']:.2f}). Obiettivo: ritorno alla media."}
        return {"Segnale": signal, "Prezzo": f"{last_candle['close']:,.4f}", "Stop Loss": f"{stop_loss:,.4f}", "Take Profit": f"{take_profit:,.4f}", "Dettagli": str(details)}, None
    elif last_candle['close'] >= last_candle['BBU_20_2.0'] and last_candle['RSI_14'] > 65:
        signal = "MEAN REVERSION SHORT"
        stop_loss = last_candle['close'] + (last_candle['ATRr_14'] * 2)
        take_profit = last_candle['BBM_20_2.0']
        details = {'Strategia': 'Mean Reversion', 'Razionale': f"Prezzo sopra banda superiore Bollinger e RSI alto ({last_candle['RSI_14']:.2f}). Obiettivo: ritorno alla media."}
        return {"Segnale": signal, "Prezzo": f"{last_candle['close']:,.4f}", "Stop Loss": f"{stop_loss:,.4f}", "Take Profit": f"{take_profit:,.4f}", "Dettagli": str(details)}, None
    return None, "Nessun segnale Mean Reversion"


def run_full_market_scan(assets, timeframe, strategy):
    signals = []
    for asset in assets:
        symbol = asset['symbol']
        source = asset['source']
        data = None
        
        if source == 'Binance':
            data = bybit_client.get_klines(symbol, timeframe, limit=100)
            if data is None or data.empty:
                print(f"-> INFO: Fallback su Binance API per i dati di {symbol}")
                data = external_apis.get_binance_klines(symbol, timeframe, limit=100)

        elif source == 'Yahoo':
            period = "1y"
            interval = "1d"
            if timeframe == "1h": period, interval = "1mo", "60m"
            data = yahoo_client.get_daily_data(symbol, period=period, interval=interval)

        if data is None or data.empty:
            continue
        
        result, error = None, "Strategia non trovata"
        if strategy == "Trend Following": result, error = analyze_trend_following(data)
        elif strategy == "Mean Reversion": result, error = analyze_mean_reversion(data)
            
        if result:
            result['Asset'] = symbol
            signals.append(result)
            
    return signals
