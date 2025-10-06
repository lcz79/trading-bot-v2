import time
import schedule
from datetime import datetime, timedelta

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
quality_scores_cache = {}
economic_events_cache = []
last_event_fetch_time = None

def is_in_news_blackout(event_time_str):
    """
    Controlla se l'orario attuale è in un periodo di "blackout" a causa di un evento economico.
    Questa funzione è semplificata e assume che l'orario dell'evento sia in formato HH:MM.
    """
    try:
        # Converte l'ora dell'evento in un oggetto datetime di oggi
        event_hour, event_minute = map(int, event_time_str.split(':'))
        now = datetime.utcnow()
        event_time = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
        
        # Calcola la differenza in secondi
        time_to_event = (event_time - now).total_seconds()
        
        # È in blackout se l'evento è tra (NEWS_BLACKOUT_HOURS) ore o è passato da meno di (NEWS_BLACKOUT_HOURS) ore
        if abs(time_to_event) < (NEWS_BLACKOUT_HOURS * 3600):
            return True
        return False

    except Exception:
        return False # Se c'è un errore, per sicurezza non blocchiamo

def run_analysis_and_store():
    global quality_scores_cache, economic_events_cache, last_event_fetch_time
    print(f"\n[{time.ctime()}] === AVVIO CICLO DI ANALISI ETL (v6.0 Final) ===")

    session = database.get_db_session()
    try:
        # FASE 1: Aggiornamento calendario economico
        if not last_event_fetch_time or (datetime.now() - last_event_fetch_time).total_seconds() > 3600:
            print("-> Fase 1: Aggiornamento calendario economico...")
            economic_events_cache = financial_data_client.get_upcoming_economic_events()
            last_event_fetch_time = datetime.now()
            if economic_events_cache:
                print(f"-> Trovati {len(economic_events_cache)} eventi ad alto impatto. Il sistema eviterà di fare trading vicino a questi orari.")
            else:
                print("-> Nessun evento economico ad alto impatto imminente o errore nel recupero.")

        # FASE 2: Caricamento e screening asset
        print("-> Fase 2: Caricamento e screening di qualità degli asset...")
        all_assets = [{'symbol': asset, 'source': source} for source, func in ASSET_SOURCES.items() for asset in func()]
        crypto_bulk_data = external_apis.get_crypto_bulk_metrics([a['symbol'] for a in all_assets if a['source'] == 'Binance'])
        
        high_quality_assets = []
        for asset in all_assets:
            symbol = asset['symbol']
            score, details = market_analysis.get_fundamental_quality_score(asset, crypto_bulk_data)
            database.store_quality_score(session, symbol, score, str(details))
            if score >= MIN_QUALITY_SCORE:
                high_quality_assets.append(asset)
        print(f"-> Trovati {len(high_quality_assets)} asset di alta qualità (score >= {MIN_QUALITY_SCORE}) su {len(all_assets)} totali.")

        # FASE 3: Analisi tecnica
        print("-> Fase 3: Esecuzione analisi tecniche...")
        database.clear_old_signals(session)
        for asset in high_quality_assets:
            symbol = asset['symbol']
            
            # CONTROLLO BLACKOUT DA NOTIZIE
            is_blackout = False
            blackout_reason = ""
            for event in economic_events_cache:
                if is_in_news_blackout(event['time']):
                    is_blackout = True
                    blackout_reason = f"Blackout per notizia: {event['event']} ({event['country']})"
                    break
            
            if is_blackout:
                print(f"-> IGNORATO {symbol}: {blackout_reason}")
                continue

            for timeframe in TIMEFRAMES:
                for strategy_name in STRATEGIES:
                    signals = market_analysis.run_full_market_scan([asset], timeframe, strategy_name)
                    for s in signals:
                        database.store_technical_signal(session, s['Asset'], timeframe, strategy_name, s['Segnale'], s['Prezzo'], s.get('Stop Loss'), s.get('Take Profit'), s['Dettagli'])
                        print(f"-> SEGNALE TROVATO: {s['Asset']} ({timeframe}) - {s['Segnale']}")
    
    finally:
        session.close()
    
    print("=== CICLO DI ANALISI COMPLETATO ===")

if __name__ == '__main__':
    database.init_db()
    run_analysis_and_store()
    schedule.every(30).minutes.do(run_analysis_and_store)
    print("\n--- Avvio Servizio ETL (v6.0 Final) ---")
    print(f"Prossimo ciclo di analisi completo tra 30 minuti.")
    while True:
        schedule.run_pending()
        time.sleep(1)
