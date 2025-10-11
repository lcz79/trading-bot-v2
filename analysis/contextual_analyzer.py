# analysis/contextual_analyzer.py
import pandas as pd
import pandas_ta as ta
import config

def get_market_bias(df_context: pd.DataFrame):
    """
    Analizza il timeframe di contesto (4h) per determinare il bias di mercato.
    Restituisce 'BULLISH', 'BEARISH', or 'SIDEWAYS'.
    """
    if df_context is None or len(df_context) < config.EMA_CONTEXT_PERIOD:
        return 'SIDEWAYS' # Non abbiamo abbastanza dati per decidere

    df = df_context.copy()
    
    # Indicatori di contesto
    df.ta.ema(length=config.EMA_CONTEXT_PERIOD, append=True)
    df.ta.adx(length=config.ADX_CONTEXT_PERIOD, append=True)
    
    df.dropna(inplace=True)
    if df.empty:
        return 'SIDEWAYS'

    last_candle = df.iloc[-1]
    ema_col = f"EMA_{config.EMA_CONTEXT_PERIOD}"
    adx_col = f"ADX_{config.ADX_CONTEXT_PERIOD}"

    price = last_candle['close']
    ema = last_candle[ema_col]
    adx = last_candle[adx_col]

    # Logica per decidere il bias
    if adx > config.ADX_CONTEXT_THRESHOLD:
        if price > ema:
            return 'BULLISH'
        else:
            return 'BEARISH'
    else:
        return 'SIDEWAYS'