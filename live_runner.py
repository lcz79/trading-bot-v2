# live_runner.py - PHOENIX v12.0 Live Trading Engine
import logging
import time
from datetime import datetime, timezone  # <-- ECCO LA CORREZIONE!
import pandas as pd

import config
import database
from api_clients.data_client import FinancialDataClient
from api_clients.bybit_client import BybitClient
from analysis.session_clock import in_session, is_eod_window, TZ
from analysis.intraday_rules import IntradayState, IntradayRules
from analysis.contextual_analyzer import get_market_bias

# --- Importa TUTTE le tue strategie ---
from analysis.strategy_vwap_rev import vwap_reversion_intraday
from analysis.strategy_orb import opening_range_breakout
from analysis.strategy_bb_squeeze import bollinger_squeeze_breakout

logging.basicConfig(level=logging.INFO, format='[LIVE RUNNER] [%(levelname)s] %(message)s')

def run_live_bot():
    """
    Il ciclo principale del bot di trading live.
    Prende la logica dal backtester polimorfico e la applica in tempo reale.
    """
    logging.info("--- 🔥 PHOENIX LIVE RUNNER v12.0 ATTIVATO 🔥 ---")
    
    data_client = FinancialDataClient()
    trade_client = BybitClient()
    rules = IntradayRules()
    db_session = database.session_scope()

    # Stato persistente del bot
    intraday_states = {asset: IntradayState() for asset in config.ASSET_UNIVERSE}
    market_biases = {asset: 'SIDEWAYS' for asset in config.ASSET_UNIVERSE}
    last_bias_check = {}

    while True:
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(TZ)

        # Controlla se siamo nella sessione di trading
        if not in_session(now_local):
            logging.info(f"Fuori sessione. Prossimo controllo tra {config.RUNNER_SLEEP_SECONDS} sec.")
            time.sleep(config.RUNNER_SLEEP_SECONDS)
            continue

        # Logica di appiattimento posizioni a fine giornata (da implementare se necessario)
        if is_eod_window(now_local):
            logging.warning("Finestra di fine giornata. Sospendo nuove operazioni.")
            # Qui andrebbe la logica per chiudere le posizioni aperte, se vuoi.
            time.sleep(config.RUNNER_SLEEP_SECONDS)
            continue

        logging.info(f"--- Inizio scansione assets ({now_local.strftime('%Y-%m-%d %H:%M:%S')}) ---")

        for asset in config.ASSET_UNIVERSE:
            try:
                state = intraday_states[asset]
                state.reset_if_new_day(now_local)

                # 1. Analisi di Contesto (una volta ogni 4 ore circa)
                if asset not in last_bias_check or (now_utc - last_bias_check.get(asset, now_utc)).total_seconds() > 4 * 3600:
                    df_context = data_client.get_klines(asset, config.CONTEXT_TIMEFRAME, limit=400)
                    if df_context is not None and not df_context.empty:
                        market_biases[asset] = get_market_bias(df_context)
                        last_bias_check[asset] = now_utc
                        logging.info(f"[{asset}] Nuovo BIAS di mercato calcolato: {market_biases[asset]}")

                # 2. Scarica i dati operativi più recenti
                df_trigger = data_client.get_klines(asset, config.OPERATIONAL_TIMEFRAME, limit=400)
                if df_trigger is None or df_trigger.empty:
                    logging.warning(f"[{asset}] Impossibile scaricare i dati operativi. Salto.")
                    continue

                # 3. Ricerca Polimorfica di Segnali (riutilizziamo la tua logica!)
                all_signals = []
                bias = market_biases[asset]
                
                # Aggiungi qui ogni nuova strategia che creerai in futuro
                vwap_signals = vwap_reversion_intraday(df_trigger, asset=asset) or []
                bb_signals = bollinger_squeeze_breakout(df_trigger, bias=bias) or []
                orb_signals = opening_range_breakout(df_trigger) or []
                
                all_signals.extend(vwap_signals)
                all_signals.extend(bb_signals)
                all_signals.extend(orb_signals)

                if not all_signals:
                    continue

                # 4. Scoring e Selezione del Segnale Migliore
                for signal in all_signals:
                    is_aligned = (bias == 'BULLISH' and signal['side'] == 'Long') or \
                                 (bias == 'BEARISH' and signal['side'] == 'Short')
                    if bias != 'SIDEWAYS':
                        if is_aligned: signal['score'] += 10
                        elif signal['strategy'] == 'VWAP-Reversion': signal['score'] -= 15 # Penalizza reversion contro trend
                
                valid_signals = [s for s in all_signals if s['score'] >= config.INTRADAY_SIGNAL_SCORE_THRESHOLD]
                if not valid_signals:
                    continue

                best_signal = max(valid_signals, key=lambda s: s.get("score", 0))
                logging.info(f"[{asset}] Trovato segnale valido: {best_signal['strategy']} ({best_signal['side']}), Score: {best_signal['score']}")

                # 5. Applica Regole Intraday e Salva il Segnale
                # NOTA: questo codice NON esegue ordini, ma salva solo il segnale nel DB.
                # L'esecuzione è lasciata manuale tramite il Command Center (app.py)
                is_allowed, reason = rules.allow_new_trade(now=now_local, equity=10000, state=state, signal_score=best_signal.get("score", 0))
                if is_allowed:
                    logging.info(f"[{asset}] Segnale approvato dalle regole intraday. Lo salvo nel database.")
                    rules.on_filled(state)
                    
                    # Crea e salva l'oggetto segnale nel database
                    signal_to_save = database.TechnicalSignal(
                        asset=asset,
                        timeframe=config.OPERATIONAL_TIMEFRAME,
                        signal=f"{best_signal['strategy']} {best_signal['side']}",
                        entry_price=best_signal['entry_price'],
                        take_profit=best_signal['tp'],
                        stop_loss=best_signal['sl'],
                        details=str({
                            "strategy": best_signal['strategy'],
                            "score": best_signal['score'],
                            "bias": bias,
                            "coherence": "Aligned" if is_aligned else "Divergent",
                            "final_score": best_signal['score'] # Puoi creare uno score più complesso
                        }),
                        created_at=now_utc
                    )
                    db_session.add(signal_to_save)
                    db_session.commit()
                    logging.info(f"[{asset}] SEGNALE SALVATO CON SUCCESSO!")

                else:
                    logging.warning(f"[{asset}] Segnale scartato dalle regole intraday: {reason}")

            except Exception as e:
                logging.error(f"Errore durante l'analisi di {asset}: {e}", exc_info=True)

        logging.info(f"--- Scansione completata. In attesa per {config.RUNNER_SLEEP_SECONDS} secondi. ---")
        time.sleep(config.RUNNER_SLEEP_SECONDS)

if __name__ == "__main__":
    database.init_db()
    run_live_bot()
