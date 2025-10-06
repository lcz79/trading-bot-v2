import yfinance as yf
import pandas as pd

def get_klines(symbol: str, interval: str, limit: int):
    """
    Recupera dati storici da Yahoo Finance.
    'limit' non è direttamente supportato, quindi usiamo un periodo calcolato.
    """
    # yfinance usa un formato diverso per l'intervallo
    # e preferisce periodi di tempo invece di 'limit'
    period = "200d" # Un default ragionevole per ottenere abbastanza dati
    if interval == "1h":
        period = "730d" # Max per dati orari
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval.lower())
        
        if df.empty:
            return None
            
        # Rinominiamo le colonne per essere coerenti con Bybit
        df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Selezioniamo solo le colonne che ci servono e restituiamo le ultime 'limit' righe
        return df[['open', 'high', 'low', 'close', 'volume']].tail(limit)

    except Exception as e:
        print(f"ERRORE in yahoo_client.get_klines per {symbol}: {e}")
        return None
