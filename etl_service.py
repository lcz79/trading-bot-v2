# etl_service.py – Phoenix v3.1.6 (Final Type-Casting Patch)

from dotenv import load_dotenv
load_dotenv()

import os
import time
import schedule
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
import multiprocessing
import traceback

import pandas as pd
import numpy as np # Importiamo numpy per il controllo dei tipi

import database
from analysis import market_analysis
from api_clients import coingecko_client, data_client

from debug.faulthandler_setup import enable as enable_faulthandler
from config import ASSETS_TO_ANALYZE, TIMEFRAMES_CONFIG

MIN_QUALITY_SCORE = 50
MAX_WORKERS = int(os.getenv("PHOENIX_MAX_WORKERS", "4"))
TASK_TIMEOUT_SECS = int(os.getenv("PHOENIX_TASK_TIMEOUT", "45"))

enable_faulthandler(sigusr1=True, periodic_seconds=0)

def _analyze_one(asset: dict, timeframe: str):
    try:
        from analysis import market_analysis
        from api_clients import data_client as fdc_module
        data_client_instance = fdc_module.FinancialDataClient()
        htf_trend, htf_details = market_analysis.get_higher_timeframe_trend(data_client_instance, asset['symbol'], asset['source'])
        signals_found = market_analysis.run_single_scan(
            data_client=data_client_instance, asset=asset, timeframe=timeframe,
            htf_trend=htf_trend, htf_details=htf_details
        )
        return signals_found
    except Exception as e:
        error_info = f"{asset.get('symbol')} {timeframe} -> {type(e).__name__}: {e}\n{traceback.format_exc()}"
        return {"_error": error_info}

def run_analysis_and_store():
    print(f"\n[{time.ctime()}] === AVVIO CICLO DI ANALISI ETL (v3.1.6) ===")
    try:
        with database.session_scope() as session:
            print("-> Fase 1&2: Caricamento asset e quality scoring...")
            all_assets = ASSETS_TO_ANALYZE
            cg_client = coingecko_client.CoinGeckoClient()
            all_symbols_base = [a['symbol'].replace('1000', '') for a in all_assets if '1000' in a['symbol']] + [a['symbol'] for a in all_assets if '1000' not in a['symbol']]
            crypto_bulk_data = cg_client.get_crypto_bulk_data(all_symbols_base)
            high_quality_assets = [
                asset for asset in all_assets
                if market_analysis.get_fundamental_quality_score(asset, crypto_bulk_data)[0] >= MIN_QUALITY_SCORE
            ]
            print(f"-> Trovati {len(high_quality_assets)} asset di alta qualità.")
            print(f"-> Fase 3: Analisi tecniche (worker={MAX_WORKERS}, timeout={TASK_TIMEOUT_SECS}s)...")
            
            jobs = []
            for asset in high_quality_assets:
                for timeframe in TIMEFRAMES_CONFIG.get(asset.get('type', 'crypto'), []):
                    jobs.append((asset, timeframe))

            final_signals_to_store = []
            ctx = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(max_workers=MAX_WORKERS, mp_context=ctx) as ex:
                future_map = {ex.submit(_analyze_one, a, tf): (a, tf) for (a, tf) in jobs}
                for fut in as_completed(future_map):
                    a, tf = future_map[fut]
                    try:
                        res = fut.result(timeout=TASK_TIMEOUT_SECS)
                        if isinstance(res, dict) and res.get("_error"):
                            print(f"[WARN] Errore nel worker per {a['symbol']} ({tf}):\n{res['_error']}")
                            continue
                        if res:
                            final_signals_to_store.extend(res)
                    except TimeoutError:
                        print(f"[TIMEOUT] L'analisi di {a['symbol']} ({tf}) ha superato i {TASK_TIMEOUT_SECS}s -> saltato.")
                    except Exception as e:
                        print(f"[ERRORE] L'analisi di {a['symbol']} ({tf}) ha fallito: {type(e).__name__}: {e}")

            if final_signals_to_store:
                print(f"-> Trovati {len(final_signals_to_store)} segnali candidati. Li salvo come TradeIntent...")
                for signal_data in final_signals_to_store:
                    existing_intent = session.query(database.TradeIntent).filter_by(symbol=signal_data['Asset'], status='NEW').first()
                    if not existing_intent:
                        
                        # --- CORREZIONE FINALE: Conversione dei tipi ---
                        # Convertiamo esplicitamente i valori numerici in float standard di Python
                        # prima di passarli al database.
                        intent = database.TradeIntent(
                            symbol=signal_data['Asset'],
                            direction=signal_data['Segnale'].split(' ')[1],
                            entry_price=float(signal_data['Prezzo']),
                            stop_loss=float(signal_data['Stop Loss']),
                            take_profit=float(signal_data['Take Profit']),
                            strategy=signal_data['Strategia'],
                            timeframe=signal_data['Timeframe']
                        )
                        # ---------------------------------------------

                        session.add(intent)
                        print(f"-> NUOVO INTENTO: {intent.symbol} ({intent.timeframe}) - {intent.direction}")
            
            session.commit() # Questo ora funzionerà
    except Exception as e:
        print(f"ERRORE FATALE nel ciclo di analisi: {type(e).__name__}: {e}")
        traceback.print_exc()
    print(f"=== CICLO DI ANALISI COMPLETATO. Prossimo ciclo tra 30 minuti. ===")


if __name__ == '__main__':
    print("--- RESET FORZATO DEL DATABASE ---")
    try:
        db_engine = database.engine
        db_base = database.Base
        print("-> Eliminazione tabelle esistenti...")
        db_base.metadata.drop_all(db_engine)
        print("-> Creazione nuove tabelle...")
        db_base.metadata.create_all(db_engine)
        print("✅ Database resettato e sincronizzato con successo.")
    except Exception as e:
        print(f"🔥 Errore durante il reset del database: {e}")
        exit()

    print("\n--- Avvio Servizio ETL (v3.1.6) ---")
    print("Servizio avviato. Eseguo un ciclo ora, poi ogni 30 minuti.")
    print("Questo terminale deve rimanere aperto.")

    run_analysis_and_store()

    schedule.every(30).minutes.do(run_analysis_and_store)
    while True:
        schedule.run_pending()
        time.sleep(1)
