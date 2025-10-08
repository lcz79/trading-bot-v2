# etl_service.py - v5.0.1 (Final Fix)
# ----------------------------------------------------------------
# - Corregge il nome del parametro passato a run_single_scan.
# ----------------------------------------------------------------

from dotenv import load_dotenv
load_dotenv()

import time
import schedule
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import database
from config import ASSETS_TO_ANALYZE, TIMEFRAMES_CONFIG
from api_clients.coingecko_client import CoinGeckoClient
from api_clients.data_client import FinancialDataClient
from analysis import market_analysis

# --- Configurazione ---
MIN_QUALITY_SCORE = 50
ETL_INTERVAL_MINUTES = 30
MAX_WORKERS = 10
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def analyze_asset_fully(asset: dict, data_client: FinancialDataClient) -> list:
    """
    Worker che esegue l'intero processo di analisi per un singolo asset.
    """
    symbol = asset['symbol']
    source = asset['source']
    timeframes = TIMEFRAMES_CONFIG.get(asset['type'], [])
    
    try:
        data_per_tf = {tf: data_client.get_klines(symbol, tf, source) for tf in timeframes}
        
        daily_data = data_per_tf.get('D')
        if daily_data is None or daily_data.empty:
            logging.warning(f"Dati giornalieri non disponibili per {symbol}, analisi HTF saltata.")
            return []
        htf_trend, _ = market_analysis.get_higher_timeframe_trend(daily_data)

        all_signals = []
        for tf, df in data_per_tf.items():
            if df is not None and not df.empty:
                # --- FIX: Passa 'df' come 'original_df' ---
                signals = market_analysis.run_single_scan(original_df=df, symbol=symbol, timeframe=tf, htf_trend=htf_trend)
                if signals:
                    logging.info(f"Trovati {len(signals)} segnali per {symbol} su timeframe {tf}.")
                    all_signals.extend(signals)
        return all_signals
    except Exception as e:
        logging.error(f"Errore nel worker per {symbol}: {e}", exc_info=False)
        return []

def run_etl_cycle():
    """Funzione principale del servizio ETL."""
    logging.info("=== AVVIO CICLO DI ANALISI ETL (v5.1) ===")
    
    cg_client = CoinGeckoClient()
    data_client = FinancialDataClient()

    logging.info("Fase 1: Quality Scoring...")
    all_symbols_base = [a['symbol'].replace('USDT', '').replace('1000', '') for a in ASSETS_TO_ANALYZE]
    crypto_bulk_data = cg_client.get_crypto_bulk_data(all_symbols_base)
    high_quality_assets = [a for a in ASSETS_TO_ANALYZE if market_analysis.get_fundamental_quality_score(a, crypto_bulk_data)[0] >= MIN_QUALITY_SCORE]
    logging.info(f"Trovati {len(high_quality_assets)} asset di alta qualità su {len(ASSETS_TO_ANALYZE)}.")

    if not high_quality_assets:
        logging.warning("Nessun asset di alta qualità trovato. Ciclo terminato.")
        return

    logging.info("Fase 2: Analisi tecniche in parallelo...")
    all_candidate_signals = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_asset = {executor.submit(analyze_asset_fully, asset, data_client): asset for asset in high_quality_assets}
        for future in as_completed(future_to_asset):
            signals = future.result()
            if signals:
                all_candidate_signals.extend(signals)

    if not all_candidate_signals:
        logging.info("Nessun segnale candidato trovato in questo ciclo.")
    else:
        logging.info(f"Fase 3: Trovati {len(all_candidate_signals)} segnali candidati. Salvataggio in corso...")
        with database.session_scope() as session:
            for signal in all_candidate_signals:
                session.add(database.TradeIntent(
                    symbol=signal['Asset'], direction=signal['Segnale'].split(' ')[-1],
                    entry_price=signal['Prezzo'], stop_loss=signal['Stop Loss'],
                    take_profit=signal['Take Profit'], score=signal['Score'],
                    strategy=signal['Strategia'], status='NEW', timeframe=signal['Timeframe']
                ))
        logging.info("✅ Segnali salvati nel database.")
    logging.info(f"=== CICLO DI ANALISI COMPLETATO. Prossimo ciclo tra {ETL_INTERVAL_MINUTES} minuti. ===")

if __name__ == "__main__":
    database.init_db(reset=True)
    logging.info("--- Avvio Servizio ETL (v5.1 - Final & Stable) ---")
    run_etl_cycle()
    schedule.every(ETL_INTERVAL_MINUTES).minutes.do(run_etl_cycle)
    while True:
        try:
            schedule.run_pending(); time.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Servizio ETL arrestato manualmente.")
            break
        except Exception as e:
            logging.critical(f"🔥 ERRORE FATALE nel loop principale: {e}", exc_info=True)
            time.sleep(60)
