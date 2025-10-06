import pandas as pd
import pandas_ta as ta # Importiamo la nuova libreria
from datetime import datetime, timedelta

# --- CONFIGURAZIONI STRATEGIA ---
ATR_MULTIPLIER = 2.0  # Moltiplicatore per lo Stop Loss
RISK_REWARD_RATIO = 1.5 # Rapporto Rischio/Rendimento per il Take Profit

def get_fundamental_quality_score(asset_info, crypto_bulk_data):
    symbol = asset_info['symbol']
    source = asset_info['source']
    
    if source == 'Yahoo':
        return 80, {"Info": "ETF principale, punteggio di alta qualità assegnato."}
    
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        return 100, {"Info": "Asset fondamentale, punteggio massimo."}

    if symbol in crypto_bulk_data:
        data = crypto_bulk_data[symbol]
        market_cap = data.get('market_cap', 0)
        volume_24h = data.get('total_volume', 0)
        
        score = 0
        if market_cap > 1_000_000_000: score += 40
        elif market_cap > 500_000_000: score += 20
        
        if volume_24h > 100_000_000: score += 40
        elif volume_24h > 50_000_000: score += 20
            
        return score, {"Market Cap": f"${market_cap:,.0f}", "Volume 24h": f"${volume_24h:,.0f}"}

    return 0, {"Errore": "Dati non disponibili."}


def calculate_sl_tp(df, signal, entry_price):
    """
    Calcola Stop Loss e Take Profit basati su ATR e swing points.
    """
    if df.empty or len(df) < 20:
        return None, None

    # Calcola ATR
    df.ta.atr(length=14, append=True)
    last_atr = df['ATRr_14'].iloc[-1]
    
    if pd.isna(last_atr):
        return None, None

    if "LONG" in signal:
        # Per un LONG, lo Stop Loss va sotto un recente minimo (supporto)
        recent_lows = df['low'].tail(10).min()
        stop_loss = recent_lows - (last_atr * ATR_MULTIPLIER)
        
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * RISK_REWARD_RATIO)
        
    elif "SHORT" in signal:
        # Per uno SHORT, lo Stop Loss va sopra un recente massimo (resistenza)
        recent_highs = df['high'].tail(10).max()
        stop_loss = recent_highs + (last_atr * ATR_MULTIPLIER)
        
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * RISK_REWARD_RATIO)
        
    else:
        return None, None

    return round(stop_loss, 4), round(take_profit, 4)


def analyze_trend_following(df):
    """
    Analisi Trend Following con EMA.
    Restituisce un segnale e un livello di confidenza.
    """
    if df.empty or len(df) < 50:
        return "NEUTRAL", 0, {}

    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    
    last_close = df['close'].iloc[-1]
    ema21 = df['EMA_21'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]

    if pd.isna(ema21) or pd.isna(ema50):
        return "NEUTRAL", 0, {}

    details = {'Prezzo': last_close, 'EMA21': round(ema21, 2), 'EMA50': round(ema50, 2)}
    
    if last_close > ema21 > ema50:
        return "STRONG LONG", 90, details
    if last_close < ema21 < ema50:
        return "STRONG SHORT", 90, details
    if last_close > ema21 and last_close > ema50:
        return "LONG", 60, details
    if last_close < ema21 and last_close < ema50:
        return "SHORT", 60, details
        
    return "NEUTRAL", 10, details

def analyze_mean_reversion(df):
    """
    Analisi Mean Reversion con RSI e Bande di Bollinger.
    """
    if df.empty or len(df) < 20:
        return "NEUTRAL", 0, {}

    df.ta.bbands(length=20, append=True)
    df.ta.rsi(length=14, append=True)

    last_close = df['close'].iloc[-1]
    rsi = df['RSI_14'].iloc[-1]
    bollinger_low = df['BBL_20_2.0'].iloc[-1]
    bollinger_high = df['BBH_20_2.0'].iloc[-1]

    if pd.isna(rsi) or pd.isna(bollinger_low):
        return "NEUTRAL", 0, {}
        
    details = {'Prezzo': last_close, 'RSI': round(rsi, 2), 'Bollinger Low': round(bollinger_low, 2)}
    
    if last_close < bollinger_low and rsi < 30:
        return "STRONG LONG", 85, details
    if last_close > bollinger_high and rsi > 70:
        return "STRONG SHORT", 85, details
        
    return "NEUTRAL", 10, details

# --- FUNZIONE PRINCIPALE DI SCANSIONE ---
STRATEGY_MAP = {
    "Trend Following": analyze_trend_following,
    "Mean Reversion": analyze_mean_reversion
}

def run_full_market_scan(data_client, assets, timeframe, strategy_name):
    signals = []
    strategy_func = STRATEGY_MAP.get(strategy_name)
    if not strategy_func: return signals

    for asset in assets:
        symbol = asset['symbol']
        source = asset['source']
        
        df = data_client.get_data(symbol, timeframe, limit=200, source=source)
        if df is None or df.empty:
            continue
            
        signal, confidence, details = strategy_func(df)
        
        if confidence > 80: # Solo per segnali forti
            entry_price = df['close'].iloc[-1]
            stop_loss, take_profit = calculate_sl_tp(df, signal, entry_price)

            details['Stop Loss'] = stop_loss
            details['Take Profit'] = take_profit
            
            signals.append({
                'Asset': symbol,
                'Segnale': signal,
                'Prezzo': round(entry_price, 4),
                'Stop Loss': stop_loss,
                'Take Profit': take_profit,
                'Dettagli': str(details),
                'Strategia': strategy_name,
                'Timeframe': timeframe
            })
            
    return signals
