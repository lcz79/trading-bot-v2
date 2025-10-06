import yfinance as yf
import pandas as pd

def get_daily_data(symbol, period="1y", interval="1d"):
    """
    Recupera dati storici da Yahoo Finance, accettando un intervallo.
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Passa l'intervallo alla funzione history di yfinance
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            print(f"WARN: Nessun dato restituito da Yahoo per {symbol} (period={period}, interval={interval})")
            return None
        
        # Rinomina le colonne per essere coerenti con il resto del nostro sistema
        data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)

        # Rimuovi il timezone per evitare problemi di compatibilità
        if data.index.tz is not None:
            data.index = data.index.tz_convert(None)

        return data
    except Exception as e:
        print(f"ERRORE in yahoo_client per {symbol}: {e}")
        return None

if __name__ == '__main__':
    # Test per verificare che la funzione funzioni con l'intervallo
    print("--- Test del Client Yahoo Finance ---")
    print("\nRichiesta dati giornalieri per AAPL:")
    aapl_daily = get_daily_data("AAPL", period="1mo", interval="1d")
    if aapl_daily is not None:
        print(aapl_daily.head())

    print("\nRichiesta dati orari per AAPL:")
    aapl_hourly = get_daily_data("AAPL", period="1wk", interval="1h")
    if aapl_hourly is not None:
        print(aapl_hourly.head())
