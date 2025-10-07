import pandas as pd
import pandas_ta as ta

# --- Costanti di Strategia ---
ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 1.5
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
HTF_TREND_PERIOD = 200  # EMA su timeframe più alto (Daily)
ATR_FILTER_PERIOD = 50
ATR_MIN_MULTIPLIER = 0.8
ATR_MAX_MULTIPLIER = 2.5


# --- Funzioni di Analisi ---

def get_fundamental_quality_score(asset_info, crypto_bulk_data):
    """Calcola un punteggio di qualità basato su capitalizzazione di mercato e volume."""
    symbol = asset_info['symbol']
    
    if symbol.startswith('1000'):
        base_symbol = symbol[4:]
    else:
        base_symbol = symbol

    if base_symbol in ["BTCUSDT", "ETHUSDT"]:
        return 100, {"Info": "Asset fondamentale"}
    
    if base_symbol in crypto_bulk_data:
        data = crypto_bulk_data.get(base_symbol)
        if data:
            market_cap = data.get('market_cap', 0) or 0
            volume_24h = data.get('total_volume', 0) or 0
            score = 0
            if market_cap > 1_000_000_000: score += 40
            elif market_cap > 500_000_000: score += 20
            if volume_24h > 100_000_000: score += 40
            elif volume_24h > 50_000_000: score += 20
            return score, {"Market Cap": f"${market_cap:,.0f}", "Volume 24h": f"${volume_24h:,.0f}"}
            
    return 0, {"Errore": f"Dati fondamentali non disponibili per {symbol}."}


def calculate_sl_tp(entry_price, atr, direction):
    """Calcola Stop Loss e Take Profit basati sull'ATR."""
    if direction == 'Long':
        stop_loss = entry_price - (atr * ATR_MULTIPLIER)
        take_profit = entry_price + (atr * ATR_MULTIPLIER * RISK_REWARD_RATIO)
    elif direction == 'Short':
        stop_loss = entry_price + (atr * ATR_MULTIPLIER)
        take_profit = entry_price - (atr * ATR_MULTIPLIER * RISK_REWARD_RATIO)
    else:
        return None, None
    return stop_loss, take_profit


def get_higher_timeframe_trend(data_client, symbol, source, timeframe='D', period=HTF_TREND_PERIOD):
    """Determina il trend di fondo usando un timeframe più alto (default: Daily)."""
    df = data_client.get_data(symbol, timeframe, limit=period + 50, source=source)
    if df is None or df.empty:
        return 'NEUTRAL', {}
    
    df[f'EMA_{period}'] = ta.ema(df['close'], length=period)
    
    last_close = df['close'].iloc[-1]
    last_ema = df[f'EMA_{period}'].iloc[-1]
    
    if last_close > last_ema:
        trend = 'UPTREND'
    elif last_close < last_ema:
        trend = 'DOWNTREND'
    else:
        trend = 'NEUTRAL'
        
    return trend, {'last_close': last_close, f'ema_{period}': last_ema}


def run_single_scan(data_client, asset, timeframe, htf_trend, htf_details):
    """Esegue l'analisi completa per un singolo asset e timeframe."""
    df = data_client.get_data(asset['symbol'], timeframe, limit=200, source=asset['source'])
    if df is None or df.empty or len(df) < 50:
        return []

    # Calcolo indicatori
    df['EMA_20'] = ta.ema(df['close'], length=20)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    last_row = df.iloc[-1]
    signals = []

    # Strategia 1: Trend Following
    is_bullish_cross = last_row['EMA_20'] > last_row['EMA_50'] and df['EMA_20'].iloc[-2] <= df['EMA_50'].iloc[-2]
    is_bearish_cross = last_row['EMA_20'] < last_row['EMA_50'] and df['EMA_20'].iloc[-2] >= df['EMA_50'].iloc[-2]

    if htf_trend == 'UPTREND' and is_bullish_cross:
        sl, tp = calculate_sl_tp(last_row['close'], last_row['ATR'], 'Long')
        signals.append({
            'Asset': asset['symbol'], 'Timeframe': timeframe, 'Strategia': 'Trend Following',
            'Segnale': 'Buy Long', 'Prezzo': last_row['close'], 'Stop Loss': sl, 'Take Profit': tp
        })

    if htf_trend == 'DOWNTREND' and is_bearish_cross:
        sl, tp = calculate_sl_tp(last_row['close'], last_row['ATR'], 'Short')
        signals.append({
            'Asset': asset['symbol'], 'Timeframe': timeframe, 'Strategia': 'Trend Following',
            'Segnale': 'Sell Short', 'Prezzo': last_row['close'], 'Stop Loss': sl, 'Take Profit': tp
        })

    # Strategia 2: Mean Reversion
    is_oversold = last_row['RSI'] < RSI_OVERSOLD
    is_overbought = last_row['RSI'] > RSI_OVERBOUGHT

    if htf_trend == 'UPTREND' and is_oversold:
        sl, tp = calculate_sl_tp(last_row['close'], last_row['ATR'], 'Long')
        signals.append({
            'Asset': asset['symbol'], 'Timeframe': timeframe, 'Strategia': 'Mean Reversion',
            'Segnale': 'Buy Long', 'Prezzo': last_row['close'], 'Stop Loss': sl, 'Take Profit': tp
        })

    if htf_trend == 'DOWNTREND' and is_overbought:
        sl, tp = calculate_sl_tp(last_row['close'], last_row['ATR'], 'Short')
        signals.append({
            'Asset': asset['symbol'], 'Timeframe': timeframe, 'Strategia': 'Mean Reversion',
            'Segnale': 'Sell Short', 'Prezzo': last_row['close'], 'Stop Loss': sl, 'Take Profit': tp
        })
        
    return signals
