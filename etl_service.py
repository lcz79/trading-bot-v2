# etl_service.py - v4.0 (Production Portfolio Trader)
import pandas as pd
import logging
import time
import json
import os
import glob
from datetime import datetime, timezone

from data_sources import binance_client
import database as db

# Importiamo il motore di valutazione che conosce tutte le nostre logiche
from strategy_generator import evaluate_strategy_extended

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- MAPPATURA DELLE LOGICHE DI STRATEGIA ---
# Questo dizionario traduce i nomi delle logiche in "ricette" eseguibili
STRATEGY_BLUEPRINTS = {
    "Pullback_v13_Original": {
        "name": "Pullback_v13_Original", 
        "trend_filter": "check_trend_condition", 
        "entry_condition": "check_pullback_entry_condition", 
        "exit_logic": "calculate_sl_tp"
    },
    "EMA_Cross_v1_WithTrendFilter": {
        "name": "EMA_Cross_v1_WithTrendFilter", 
        "trend_filter": "check_trend_condition", 
        "entry_condition": "check_ema_cross_entry_condition", 
        "exit_logic": "calculate_sl_tp"
    }
}


def load_latest_production_strategies():
    """
    Trova e carica il file delle strategie di produzione più recente.
    """
    try:
        list_of_files = glob.glob('production_strategies_*.json')
        if not list_of_files:
            logging.error("ERRORE CRITICO: Nessun file 'production_strategies_*.json' trovato.")
            return None
        latest_file = max(list_of_files, key=os.path.getctime)
        logging.info(f"Caricamento del file di strategie di produzione: {latest_file}")
        with open(latest_file, 'r') as f:
            strategies = json.load(f)
        return strategies
    except Exception as e:
        logging.error(f"ERRORE CRITICO durante il caricamento delle strategie: {e}")
        return None

def run_analysis_cycle(production_strategies):
    """
    Esegue un ciclo di analisi per ogni asset nel portafoglio di strategie.
    """
    if not production_strategies:
        logging.warning("Nessuna strategia da eseguire. In attesa...")
        return

    logging.info(f"--- AVVIO CICLO DI ANALISI PORTAFOGLIO ({len(production_strategies)} assets) ---")

    for asset, strategy_data in production_strategies.items():
        logic_name = strategy_data.get('logic_name')
        params = strategy_data.get('params')
        
        if not logic_name or not params:
            logging.warning(f"Dati di strategia incompleti per {asset}. Salto.")
            continue
            
        if logic_name not in STRATEGY_BLUEPRINTS:
            logging.warning(f"Logica di strategia '{logic_name}' per {asset} non riconosciuta. Salto.")
            continue
            
        strategy_logic = STRATEGY_BLUEPRINTS[logic_name]

        try:
            logging.info(f"Analisi per {asset} con logica '{logic_name}'...")
            
            # Scarica i dati più recenti
            klines = binance_client.get_historical_klines(asset, "1h", "210 hours ago UTC")
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = pd.to_numeric(df[col])

            # Esegui la valutazione della strategia specifica
            signal = evaluate_strategy_extended(df, params, strategy_logic)

            if signal:
                # Arricchiamo il segnale con i metadati
                signal['symbol'] = asset
                signal['strategy'] = logic_name
                signal['timestamp_generated'] = datetime.now(timezone.utc).isoformat()

                if db.check_recent_signal(asset, signal['type']):
                    logging.info(f"Segnale per {asset} ({signal['type']}) già registrato di recente. Salto.")
                else:
                    db.save_signal(signal)
                    logging.info(f"✅✅✅ SEGNALE TROVATO E SALVATO: {signal['type']} {asset} @ {signal['entry']} | SL {signal['sl']} | TP {signal['tp']}")
            else:
                logging.info(f"Nessuna opportunità valida per {asset}.")

        except Exception as e:
            logging.error(f"Errore durante l'analisi di {asset}: {e}")
            
    logging.info("--- CICLO DI ANALISI COMPLETATO ---")


if __name__ == "__main__":
    db.init_db()
    
    # Carica le strategie una sola volta all'avvio
    production_strategies = load_latest_production_strategies()
    if not production_strategies:
        exit() # Esce se non riesce a caricare le strategie

    while True:
        try:
            run_analysis_cycle(production_strategies)
            logging.info("In attesa per il prossimo ciclo... (30 minuti)")
            time.sleep(1800) # 30 minuti
        except KeyboardInterrupt:
            logging.info("Ricevuto segnale di interruzione. Chiusura del servizio ETL.")
            break
        except Exception as e:
            logging.error(f"Errore inatteso nel ciclo principale: {e}")
            time.sleep(60) # Attendi un minuto prima di riprovare
