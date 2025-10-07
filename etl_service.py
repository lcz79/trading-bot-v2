import time
import schedule
from dotenv import load_dotenv
import traceback

# Carica le variabili d'ambiente
load_dotenv()

# Import dei moduli del progetto
from analysis import market_analysis
from database import init_db, clear_old_signals, session_scope, TechnicalSignal
from utils.network_utils import is_connected
from api_clients import financial_data_client, coingecko_client
from config import ASSETS_TO_ANALYZE, STRATEGIES, TIMEFRAMES_CONFIG

def run_etl_cycle():
    """
    Esegue un ciclo completo di ETL: Estrazione, Trasformazione (Analisi) e Caricamento (Salvataggio).
    """
    print(f"\n[{time.ctime()}] === AVVIO CICLO DI ANALISI ETL (v8.4 - Finale) ===")

    if not is_connected():
        print("❌ ERRORE DI RETE: Connessione a Internet assente. Il ciclo di analisi è stato saltato.")
        print("=== CICLO DI ANALISI INTERROTTO. Si riproverà al prossimo intervallo. ===")
        return

    try:
        # --- FASE 1: ESTRAZIONE E FILTRAGGIO ASSET ---
        print("-> Fase 1: Caricamento e screening di qualità degli asset...")
        
        crypto_symbols_to_fetch = [a['symbol'] for a in ASSETS_TO_ANALYZE if a.get('type') == 'crypto']
        crypto_bulk_data = coingecko_client.get_crypto_bulk_data(crypto_symbols_to_fetch)
        
        if not crypto_bulk_data and crypto_symbols_to_fetch:
            print("-> ATTENZIONE: Impossibile recuperare i dati fondamentali da CoinGecko. Gli asset crypto potrebbero non essere analizzati correttamente.")
        
        quality_assets = []
        for asset in ASSETS_TO_ANALYZE:
            score, details = market_analysis.get_fundamental_quality_score(asset, crypto_bulk_data)
            if score >= 50:
                quality_assets.append(asset)
                print(f"  -> Asset di qualità: {asset['symbol']} (Score: {score})")

        if not quality_assets:
            print("-> Info: Nessun asset ha superato lo screening di qualità. Fine del ciclo.")
            return
            
        print(f"-> Trovati {len(quality_assets)} asset di alta qualità. Inizio analisi tecnica.")

        # --- FASE 2: ANALISI TECNICA (TRASFORMAZIONE) ---
        print("-> Fase 2: Esecuzione analisi tecniche...")
        all_new_signals = []
        for asset in quality_assets:
            asset_type = asset.get('type', 'crypto')
            timeframes_for_asset = TIMEFRAMES_CONFIG.get(asset_type, [])
            
            for strategy_name in STRATEGIES:
                for timeframe in timeframes_for_asset:
                    print(f"  -> Analisi per {asset['symbol']} | Strategia: '{strategy_name}', Timeframe: {timeframe}")
                    
                    # Chiama la funzione che analizza un singolo asset/timeframe
                    signals_found = market_analysis.run_single_scan(
                        data_client=financial_data_client,
                        asset=asset,
                        timeframe=timeframe,
                        strategy_name=strategy_name
                    )
                    
                    if signals_found:
                        all_new_signals.extend(signals_found)
                        print(f"    ✅ Trovati {len(signals_found)} segnali 'STRONG'!")

        # --- FASE 3: CARICAMENTO SEGNALI NEL DATABASE ---
        if not all_new_signals:
            print("-> Info: Nessun nuovo segnale 'STRONG' generato in questo ciclo.")
        else:
            print(f"-> Fase 3: Salvataggio di {len(all_new_signals)} nuovi segnali nel database...")
            with session_scope() as session:
                for signal_data in all_new_signals:
                    new_signal = TechnicalSignal(
                        asset=signal_data['Asset'],
                        timeframe=signal_data['Timeframe'],
                        strategy=signal_data['Strategia'],
                        signal=signal_data['Segnale'],
                        entry_price=signal_data['Prezzo'],
                        stop_loss=signal_data['Stop Loss'],
                        take_profit=signal_data['Take Profit'],
                        details=signal_data['Dettagli']
                    )
                    session.add(new_signal)
            print("✅ Segnali salvati con successo.")

        # --- FASE 4: PULIZIA ---
        print("-> Fase 4: Pulizia vecchi segnali...")
        clear_old_signals(days=2)

    except Exception as e:
        print(f"🔥 ERRORE CRITICO INASPETTATO nel ciclo principale di ETL: {e}")
        traceback.print_exc()
    finally:
        print(f"=== CICLO DI ANALISI COMPLETATO. Prossimo ciclo tra 30 minuti. ===")


if __name__ == "__main__":
    print("🚀 Avvio del servizio ETL 'Arbitro' del Progetto Phoenix...")
    init_db()

    run_etl_cycle()

    schedule.every(30).minutes.do(run_etl_cycle)

    while True:
        schedule.run_pending()
        time.sleep(1)
