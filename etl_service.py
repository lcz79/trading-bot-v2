# --- PRIMISSIMA COSA DA FARE: CARICARE LE VARIABILI D'AMBIENTE ---
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------

import time
import schedule
from datetime import datetime
import pandas as pd
from decimal import Decimal
from collections import defaultdict

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

def resolve_signal_conflicts(signals):
    """
    Arbitro dei segnali. Applica la regola del dominio del trend.
    """
    if not signals:
        return []

    # Se c'è un solo segnale, non ci sono conflitti.
    if len(signals) == 1:
        return signals

    print(f"-> Rilevato potenziale conflitto: {len(signals)} segnali per lo stesso asset/timeframe. Avvio arbitrato...")
    
    trend_signals = [s for s in signals if s['Strategia'] == 'Trend Following']
    reversion_signals = [s for s in signals if s['Strategia'] == 'Mean Reversion']

    # REGOLA: Se esiste un segnale di Trend, vince lui.
    if trend_signals:
        # Se ci sono più segnali di trend (raro), prendiamo il primo.
        final_signal = trend_signals[0]
        print(f"-> VERDETTO ARBITRO: Domina il segnale di Trend Following '{final_signal['Segnale']}'. Gli altri vengono scartati.")
        return [final_signal]

    # Se non ci sono segnali di Trend, prendiamo il segnale di Mean Reversion.
    if reversion_signals:
        final_signal = reversion_signals[0]
        print(f"-> VERDETTO ARBITRO: Nessun segnale di Trend. Vince il segnale di Mean Reversion '{final_signal['Segnale']}'.")
        return [final_signal]
    
    # Caso di fallback, non dovrebbe accadere
    return []


def run_analysis_and_store():
    print(f"\n[{time.ctime()}] === AVVIO CICLO DI ANALISI ETL (v8.0 - Arbitro) ===")

    try:
        with database.session_scope() as session:
            open_positions_df = pd.read_sql("SELECT symbol FROM open_positions", database.engine)
            open_position_symbols = set(open_positions_df['symbol'].unique())
            if open_position_symbols:
                print(f"-> Consapevolezza: Trovate {len(open_position_symbols)} posizioni aperte: {list(open_position_symbols)}")

            print("-> Fase 1&2: Caricamento e screening di qualità degli asset...")
            all_assets = [{'symbol': asset, 'source': source} for source, func in ASSET_SOURCES.items() for asset in func()]
            crypto_bulk_data = external_apis.get_crypto_bulk_metrics([a['symbol'] for a in all_assets if a['source'] == 'Binance'])
            
            high_quality_assets = []
            for asset in all_assets:
                symbol = asset['symbol']
                score, details = market_analysis.get_fundamental_quality_score(asset, crypto_bulk_data)
                
                db_score = session.query(database.QualityScore).filter(database.QualityScore.asset == symbol).first()
                if db_score:
                    db_score.quality_score = score
                    db_score.details = details
                else:
                    db_score = database.QualityScore(asset=symbol, quality_score=score, details=details)
                    session.add(db_score)
                
                if score >= MIN_QUALITY_SCORE:
                    high_quality_assets.append(asset)
            
            session.commit()
            print(f"-> Trovati {len(high_quality_assets)} asset di alta qualità. I Quality Score nel DB sono stati aggiornati.")

            print("-> Fase 3: Esecuzione analisi tecniche...")
            database.clear_old_signals(days=2)
            
            final_signals_to_store = []
            
            for asset in high_quality_assets:
                symbol = asset['symbol']
                if symbol in open_position_symbols:
                    print(f"-> IGNORATO {symbol}: Posizione già aperta.")
                    continue

                for timeframe in TIMEFRAMES:
                    # Raccoglie tutti i segnali per questo asset/timeframe
                    potential_signals = []
                    for strategy_name in STRATEGIES:
                        signals = market_analysis.run_full_market_scan(financial_data_client, [asset], timeframe, strategy_name)
                        potential_signals.extend(signals)
                    
                    # Risolve i conflitti
                    resolved_signals = resolve_signal_conflicts(potential_signals)
                    final_signals_to_store.extend(resolved_signals)

            # Salva nel database solo i segnali che hanno superato l'arbitraggio
            for s in final_signals_to_store:
                new_signal = database.TechnicalSignal(
                    asset=s['Asset'], timeframe=s['Timeframe'], strategy=s['Strategia'], signal=s['Segnale'],
                    entry_price=Decimal(str(s['Prezzo'])),
                    stop_loss=Decimal(str(s['Stop Loss'])) if s['Stop Loss'] is not None else None,
                    take_profit=Decimal(str(s['Take Profit'])) if s['Take Profit'] is not None else None,
                    details=s['Dettagli']
                )
                session.add(new_signal)
                print(f"-> NUOVO SEGNALE CONFERMATO: {s['Asset']} ({s['Timeframe']}) - {s['Segnale']} (Strategia: {s['Strategia']})")
            
            session.commit()

    except Exception as e:
        print(f"ERRORE FATALE nel ciclo di analisi: {e}")
    
    print(f"=== CICLO DI ANALISI COMPLETATO. Prossimo ciclo tra 30 minuti. ===")


if __name__ == '__main__':
    database.init_db()
    
    print("\n--- Avvio Servizio ETL (v8.0 - Arbitro) ---")
    print("Servizio avviato. Eseguo un ciclo ora, poi ogni 30 minuti.")
    print("Questo terminale deve rimanere aperto.")
    
    run_analysis_and_store()
    
    schedule.every(30).minutes.do(run_analysis_and_store)

    while True:
        schedule.run_pending()
        time.sleep(1)
