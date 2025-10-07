import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# --- CONFIGURAZIONI STRATEGIA ---
ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 1.5

# ==============================================================================
# FUNZIONI DI ANALISI E CALCOLO
# (Devono essere definite PRIMA di essere usate nella STRATEGY_MAP)
# ==============================================================================

def get_fundamental_quality_score(asset_info, crypto_bulk_data):
    """
    Calcola un punteggio di qualità per un asset.
    """
    symbol = asset_info['symbol']
    source = asset_info.get('source', '')
    asset_type = asset_info.get('type', '')
    
    # Assegna punteggi fissi per asset noti e tipi specifici
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        return 100, {"Info": "Asset fondamentale, punteggio massimo."}
    if asset_type == 'stock':
        return 80, {"Info": "ETF/Azione principale, punteggio di alta qualità assegnato."}

    # Calcola punteggio per altre crypto basandosi sui dati di CoinGecko
    if symbol in crypto_bulk_data:
        data = crypto_bulk_data.get(symbol)
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


def calculate_sl_tp(df, signal, entry_price):
    """
    Calcola Stop Loss e Take Profit basati su ATR e swing points.
    """
    if df.empty or len(df) < 20:
        return None, None

    df.ta.atr(length=14, append=True)
    atr_col = next((col for col in df.columns if col.startswith('ATRr_')), None)
    if not atr_col or pd.isna(df[atr_col].iloc[-1]) or df[atr_col].iloc[-1] == 0:
        return None, None
        
    last_atr = float(df[atr_col].iloc[-1])  # Converti a float
    
    if "LONG" in signal:
        stop_loss = df['low'].tail(10).min() - (last_atr * ATR_MULTIPLIER)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * RISK_REWARD_RATIO)
    elif "SHORT" in signal:
        stop_loss = df['high'].tail(10).max() + (last_atr * ATR_MULTIPLIER)
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * RISK_REWARD_RATIO)
    else:
        return None, None

    return float(stop_loss), float(take_profit)  # Converti a float


def analyze_trend_following(df):
    """
    Analisi Trend Following con EMA.
    """
    if df.empty or len(df) < 50:
        return "NEUTRAL", 0, {}

    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    
    last_close = float(df['close'].iloc[-1])  # Converti
    ema21 = float(df['EMA_21'].iloc[-1])
    ema50 = float(df['EMA_50'].iloc[-1])

    if pd.isna(ema21) or pd.isna(ema50):
        return "NEUTRAL", 0, {}

    details = {'Prezzo': last_close, 'EMA21': ema21, 'EMA50': ema50}
    
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

    df.ta.bbands(length=20, std=2, append=True)
    df.ta.rsi(length=14, append=True)

    rsi_col = next((col for col in df.columns if col.startswith('RSI_')), None)
    bbl_col = next((col for col in df.columns if col.startswith('BBL_')), None)
    bbu_col = next((col for col in df.columns if col.startswith('BBU_')), None)

    if not all([rsi_col, bbl_col, bbu_col]):
        return "NEUTRAL", 0, {}

    last_close = float(df['close'].iloc[-1])
    rsi = float(df[rsi_col].iloc[-1])
    bollinger_low = float(df[bbl_col].iloc[-1])
    bollinger_high = float(df[bbu_col].iloc[-1])

    if pd.isna(rsi) or pd.isna(bollinger_low) or pd.isna(bollinger_high):
        return "NEUTRAL", 0, {}
        
    details = {'Prezzo': last_close, 'RSI': rsi, 'Bollinger Low': bollinger_low, 'Bollinger High': bollinger_high}
    
    if last_close < bollinger_low and rsi < 30:
        return "STRONG LONG", 85, details
    if last_close > bollinger_high and rsi > 70:
        return "STRONG SHORT", 85, details
        
    return "NEUTRAL", 10, details

# ==============================================================================
# DEFINIZIONE DELLA MAPPA DELLE STRATEGIE E DELLA FUNZIONE DI SCANSIONE
# (Deve essere DOPO la definizione delle funzioni di analisi)
# ==============================================================================

STRATEGY_MAP = {
    "Trend Following": analyze_trend_following,
    "Mean Reversion": analyze_mean_reversion
}

def run_single_scan(data_client, asset, timeframe, strategy_name):
    """
    Esegue l'analisi per un singolo asset, timeframe e strategia.
    """
    signals = []
    strategy_func = STRATEGY_MAP.get(strategy_name)
    if not strategy_func:
        return signals

    symbol = asset['symbol']
    source = asset['source']
    
    df = data_client.get_data(symbol, timeframe, limit=200, source=source)
    if df is None or df.empty:
        return signals
        
    signal, confidence, details = strategy_func(df)
    
    if confidence > 80:
        entry_price = float(df['close'].iloc[-1])  # Converti a float
        stop_loss, take_profit = calculate_sl_tp(df, signal, entry_price)

        details['Stop Loss'] = stop_loss
        details['Take Profit'] = take_profit
        
        signals.append({
            'Asset': symbol,
            'Segnale': signal,
            'Prezzo': entry_price,
            'Stop Loss': stop_loss,
            'Take Profit': take_profit,
            'Dettagli': str(details),
            'Strategia': strategy_name,
            'Timeframe': timeframe
        })
            
    return signals
