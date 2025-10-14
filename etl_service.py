# etl_service.py - v2.1 (Supporto per la chiave "groups")
import time
import logging
import json
import pandas as pd
from datetime import datetime, timedelta

from data_sources import binance_client
from analysis import market_analysis

# --- CONFIGURAZIONE ---
LOG_FILE = 'etl_service.log'
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT"
]
STRATEGIES_FILE = 'optimal_strategies.json'
LOOP_INTERVAL_MINUTES = 30

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- FUNZIONI CORE ---
def load_strategies(filepath):
    """Carica l'intero file di configurazione delle strategie."""
    try:
        with open(filepath, 'r') as f:
            strategies = json.load(f)
        logging.info("File delle strategie caricato con successo.")
        return strategies
    except FileNotFoundError:
        logging.error(f"File delle strategie '{filepath}' non trovato.")
        return None
    except json.JSONDecodeError:
        logging.error(f"Errore nel parsing del file JSON '{filepath}'.")
        return None

def get_params_for_symbol(symbol, settings):
    """Costruisce i parametri per un simbolo specifico usando la logica multi-asset."""
    params = settings['defaults'].copy()
    
    asset_class = "crypto"
    if any(x in symbol for x in ['USD', 'EUR', 'GBP', 'JPY']): asset_class = "forex"
    if any(x in symbol for x in ['NAS', 'SPX', 'DAX']): asset_class = "indices"
    if any(x in symbol for x in ['XAU', 'OIL', 'WTI']): asset_class = "commod"
    
    # --- MODIFICA CHIAVE ---
    # Ora cerchiamo i parametri dentro la chiave "groups"
    if 'groups' in settings and asset_class in settings['groups']:
        params.update(settings['groups'][asset_class])
    
    if symbol in settings.get('overrides', {}):
        params.update(settings['overrides'][symbol])
            
    return params

def run_etl_cycle(symbols, all_settings):
    """Esegue un ciclo completo di analisi per i simboli dati."""
    logging.info("=== AVVIO CICLO DI ANALISI ===")
    
    for symbol in symbols:
        params = get_params_for_symbol(symbol, all_settings)
        logging.info(f"Analisi per {symbol} con parametri: {params}")

        try:
            klines = binance_client.get_historical_klines(symbol, "1h", "300 hours ago UTC")
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        except Exception as e:
            logging.error(f"Errore durante il download dei dati per {symbol}: {e}")
            continue

        try:
            market_analysis.run_pullback_analysis(symbol, df, params)
        except Exception as e:
            logging.error(f"Errore imprevisto durante l'analisi di {symbol}: {e}")
                
        time.sleep(0.5)

    logging.info(f"=== CICLO COMPLETATO. Prossimo ciclo tra {LOOP_INTERVAL_MINUTES} minuti. ===")


if __name__ == "__main__":
    strategy_settings = load_strategies(STRATEGIES_FILE)
    if strategy_settings:
        logging.info("--- Avvio Servizio ETL con Strategia Multi-Asset ---")
        while True:
            run_etl_cycle(SYMBOLS, strategy_settings)
            time.sleep(LOOP_INTERVAL_MINUTES * 60)
    else:
        logging.error("Impossibile avviare il servizio: errore nel caricamento delle strategie.")
