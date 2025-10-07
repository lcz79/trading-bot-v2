import pandas as pd
import pandas_ta as ta

# --- CONFIGURAZIONI STRATEGIA ---
ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 1.5 
RSI_OVERBOUGHT = 70 # Usiamo valori più standard
RSI_OVERSOLD = 30

# ==============================================================================
# FUNZIONI DI SERVIZIO E ANALISI
# ==============================================================================

def get_fundamental_quality_score(asset_info, crypto_bulk_data):
    """Calcola un punteggio di qualità per un asset."""
    symbol = asset_info['symbol']
    asset_type = asset_info.get('type', '')
    
    # Asset di alto livello hanno punteggio massimo di default
    if symbol in ["BTCUSDT", "ETHUSDT"]: 
        return 100, {"Info": "Asset fondamentale"}
    if asset_type == 'stock': 
        return 80, {"Info": "ETF/Azione principale"}
        
    # Per le altre crypto, usa i dati di CoinGecko
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
            
    return 0, {"Errore": f"Dati non disponibili per {symbol}."}

def calculate_sl_tp(df, signal, entry_price):
    if df.empty or len(df) < 20: return None, None
    df.ta.atr(length=14, append=True)
    atr_col = next((col for col in df.columns if col.startswith('ATRr_')), None)
    if not atr_col or pd.isna(df[atr_col].iloc[-1]) or df[atr_col].iloc[-1] == 0: return None, None
    last_atr = float(df[atr_col].iloc[-1])
    if "LONG" in signal:
        stop_loss = entry_price - (last_atr * ATR_MULTIPLIER)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * RISK_REWARD_RATIO)
    elif "SHORT" in signal:
        stop_loss = entry_price + (last_atr * ATR_MULTIPLIER)
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * RISK_REWARD_RATIO)
    else: return None, None
    return float(stop_loss), float(take_profit)

def analyze_mean_reversion_pro(df):
    """
    Strategia Mean Reversion classica: entra quando il prezzo chiude FUORI dalle bande.
    """
    if df.empty or len(df) < 21: return "NEUTRAL", 0, {}
    
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.rsi(length=14, append=True)

    rsi_col = next((c for c in df.columns if c.startswith('RSI_')), None)
    bbl_col = next((c for c in df.columns if c.startswith('BBL_')), None)
    bbu_col = next((c for c in df.columns if c.startswith('BBU_')), None)

    if not all([rsi_col, bbl_col, bbu_col]): return "NEUTRAL", 0, {}

    last_close = float(df['close'].iloc[-1])
    rsi = float(df[rsi_col].iloc[-1])
    bollinger_low = float(df[bbl_col].iloc[-1])
    bollinger_high = float(df[bbu_col].iloc[-1])

    if any(pd.isna([last_close, rsi, bollinger_low, bollinger_high])):
        return "NEUTRAL", 0, {}
        
    details = {'RSI': rsi, 'BBL': bollinger_low, 'BBU': bollinger_high}
    
    # CONDIZIONE LONG SEMPLIFICATA: Prezzo chiude SOTTO la banda e RSI è ipervenduto
    if last_close < bollinger_low and rsi < RSI_OVERSOLD:
        return "STRONG LONG", 90, details
        
    # CONDIZIONE SHORT SEMPLIFICATA: Prezzo chiude SOPRA la banda e RSI è ipercomprato
    if last_close > bollinger_high and rsi > RSI_OVERBOUGHT:
        return "STRONG SHORT", 90, details
        
    return "NEUTRAL", 10, details

def run_single_scan(data_client, asset, timeframe):
    """
    Esegue l'analisi di Mean Reversion Pro.
    """
    signals = []
    symbol, source = asset['symbol'], asset['source']
    df = data_client.get_data(symbol, timeframe, limit=200, source=source)
    if df is None or df.empty: return signals
    
    # La funzione di analisi ora è quella corretta
    signal, confidence, details = analyze_mean_reversion_pro(df)
    
    if signal != "NEUTRAL":
        entry_price = float(df['close'].iloc[-1])
        stop_loss, take_profit = calculate_sl_tp(df, signal, entry_price)
        
        details.update({'Stop Loss': stop_loss, 'Take Profit': take_profit})
        signals.append({
            'Asset': symbol, 'Segnale': signal, 'Prezzo': entry_price, 
            'Stop Loss': stop_loss, 'Take Profit': take_profit, 
            'Dettagli': str(details), 'Strategia': "Mean Reversion Pro", 'Timeframe': timeframe
        })
    return signals
