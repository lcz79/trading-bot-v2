import time
import schedule
from datetime import datetime
import pandas as pd

import database
from analysis import market_analysis
from api_clients import external_apis, financial_data_client

# --- CONFIGURAZIONE ---
ASSET_SOURCES = {
    'Binance': external_apis.get_binance_assets,
    'Yahoo': external_apis.get_yahoo_assets
}
STRATEGIES = ["Trend Following", "Mean Reversion"]
TIMEFRAMES = ["1h", "4h"]
MIN_QUALITY_SCORE = 70
NEWS_BLACKOUT_HOURS = 2

# --- STATO GLOBALE (CACHE) ---
economic_events_cache = []
last_event_fetch_time = None

def run_analysis_and_store():
    global economic_events_cache, last_event_fetch_time
    print(f"\n[{time.ctime()}] === AVVIO CICLO DI ANALISI ETL (v6.2 - Modalità Servizio) ===")

    session = database.get_db_session()
    try:
        # FASE 0: Recupera le posizioni aperte dal database
        open_positions_df = pd.read_sql("SELECT symbol FROM open_positions", database.engine)
        open_position_symbols = set(open_positions_df['symbol'].unique())
        if open_position_symbols:
            print(f"-> Consapevolezza: Trovate {len(open_position_symbols)} posizioni aperte: {list(open_position_symbols)}")

        # FASE 1 & 2: Caricamento e screening asset
        print("-> Fase 1&2: Caricamento e screening di qualità degli asset...")
        all_assets = [{'symbol': asset, 'source': source} for source, func in ASSET_SOURCES.items() for asset in func()]
        crypto_bulk_data = external_apis.get_crypto_bulk_metrics([a['symbol'] for a in all_assets if a['source'] == 'Binance'])
        
        high_quality_assets = []
        for asset in all_assets:
            symbol = asset['symbol']
            score, details = market_analysis.get_fundamental_quality_score(asset, crypto_bulk_data)
            database.store_quality_score(session, symbol, score, str(details))
            if score >= MIN_QUALITY_SCORE:
                high_quality_assets.append(asset)
        print(f"-> Trovati {len(high_quality_assets)} asset di alta qualità. I Quality Score nel DB sono stati aggiornati.")

        # FASE 3: Esecuzione analisi tecniche
        print("-> Fase 3: Esecuzione analisi tecniche...")
        database.clear_old_signals(session)
        
        for asset in high_quality_assets:
            symbol = asset['symbol']
            if symbol in open_position_symbols:
                print(f"-> IGNORATO {symbol}: Posizione già aperta.")
                continue

            for timeframe in TIMEFRAMES:
                for strategy_name in STRATEGIES:
                    signals = market_analysis.run_full_market_scan([asset], timeframe, strategy_name)
                    for s in signals:
                        database.store_technical_signal(session, s['Asset'], timeframe, strategy_name, s['Segnale'], s['Prezzo'], s.get('Stop Loss'), s.get('Take Profit'), s['Dettagli'])
                        print(f"-> NUOVO SEGNALE TROVATO: {s['Asset']} ({timeframe}) - {s['Segnale']}")
    
    finally:
        session.close()
    
    print(f"=== CICLO DI ANALISI COMPLETATO. Prossimo ciclo tra 30 minuti. ===")

if __name__ == '__main__':
    database.init_db()
    
    # --- MODIFICA CHIAVE ---
    # Non eseguiamo più l'analisi una volta all'avvio.
    # Il servizio parte e attende il primo ciclo schedulato.
    schedule.every(30).minutes.do(run_analysis_and_store)
    
    print("\n--- Avvio Servizio ETL (v6.2 - Modalità Servizio Puro) ---")
    print("Servizio avviato. Il primo ciclo di analisi inizierà tra 30 minuti.")
    print("Questo terminale deve rimanere aperto.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
