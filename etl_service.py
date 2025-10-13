# etl_service.py - v3.0 (Orchestratore di Strategie Ottimali)
import pandas as pd
from pybit.unified_trading import HTTP
import logging
import time
import json

# Importiamo il nostro nuovo motore di analisi dinamico
from analysis.market_analysis import run_pullback_analysis

# --- CONFIGURAZIONE ---
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT"]
TIME_INTERVAL_MIN = 30
OPTIMAL_STRATEGIES_FILE = "optimal_strategies.json"
session = HTTP()

def get_klines_as_df(symbol: str, interval: str, limit: int = 200, start_time: int = None):
    # ... (funzione identica, non serve cambiarla) ...
    try:
        params = {"category": "spot", "symbol": symbol, "interval": interval, "limit": limit}
        if start_time: params["start"] = start_time
        response = session.get_kline(**params)
        if response.get('retCode') == 0 and response['result']['list']:
            data = response['result']['list']
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC')
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
            return df.sort_index()
        else:
            logging.warning(f"Nessun dato ricevuto da Bybit per {symbol}: {response.get('retMsg')}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Errore recupero k-line per {symbol}: {e}")
        return pd.DataFrame()

def load_optimal_strategies():
    """Carica il file JSON con le strategie ottimali."""
    try:
        with open(OPTIMAL_STRATEGIES_FILE, 'r') as f:
            strategies = json.load(f)
        logging.info("File delle strategie ottimali caricato con successo.")
        return strategies
    except FileNotFoundError:
        logging.error(f"ERRORE: File '{OPTIMAL_STRATEGIES_FILE}' non trovato. Esegui optimizer.py prima.")
        return None
    except json.JSONDecodeError:
        logging.error(f"ERRORE: File '{OPTIMAL_STRATEGIES_FILE}' non è un JSON valido.")
        return None

def run_etl_cycle(optimal_strategies: dict):
    """Esegue un ciclo di analisi usando le strategie personalizzate."""
    logging.info(f"=== AVVIO CICLO DI ANALISI OTTIMIZZATA ===")
    
    for symbol in SYMBOLS:
        # Prende i parametri specifici per questo simbolo
        params = optimal_strategies.get(symbol)
        if not params:
            logging.warning(f"Nessuna strategia ottimale trovata per {symbol}. Salto.")
            continue
        
        # Scarica i dati necessari (200 periodi sono sufficienti per la EMA più lenta)
        df_1h = get_klines_as_df(symbol, "60", limit=250)
        time.sleep(0.5)
        
        if not df_1h.empty:
            # Lancia l'analisi passando i parametri specifici
            run_pullback_analysis(symbol, df_1h, params)
        else:
            logging.warning(f"Dati per {symbol} non disponibili, salto l'analisi.")
        
        time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s')
    
    # Carica le strategie all'avvio
    strategies = load_optimal_strategies()
    
    if strategies:
        logging.info("--- Avvio Servizio ETL con Strategie Ottimizzate ---")
        while True:
            run_etl_cycle(strategies)
            logging.info(f"=== CICLO COMPLETATO. Prossimo ciclo tra {TIME_INTERVAL_MIN} minuti. ===")
            time.sleep(TIME_INTERVAL_MIN * 60)
    else:
        logging.error("Impossibile avviare il servizio. Risolvere gli errori del file di configurazione.")
