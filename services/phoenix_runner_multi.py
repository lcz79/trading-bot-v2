# services/phoenix_runner_multi.py (Patch 2)
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import database
import config
from api_clients.data_client import FinancialDataClient
from analysis.multi_timeframe_analyzer import analyze_multi_timeframes

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(asctime)s] %(message)s')

COHERENCE_BONUS = {"HIGH": 15, "MEDIUM": 5, None: 0}

def _choose_signal(signals_dict, coherence):
    if not signals_dict: return None
    if coherence == "HIGH": return signals_dict.get("Daily") or signals_dict.get("4H") or max(signals_dict.values(), key=lambda s: s["score"])
    if coherence == "MEDIUM": return signals_dict.get("4H") or signals_dict.get("15m") or max(signals_dict.values(), key=lambda s: s["score"])
    return max(signals_dict.values(), key=lambda s: s["score"])

def run_multi_timeframe_cycle():
    logging.info("=== Phoenix Multi-Timeframe Cycle (v7.0) ===")
    data_client = FinancialDataClient()
    database.init_db()
    with database.session_scope() as session:
        try: open_pos_symbols = {p.symbol for p in session.query(database.OpenPosition).all()}
        except Exception: open_pos_symbols = set()
        for asset in config.ASSET_UNIVERSE:
            if asset in open_pos_symbols: continue
            result = analyze_multi_timeframes(asset, data_client, config)
            signals, coherence = result["signals"], result["coherence"]
            if not signals:
                logging.info(f"{asset}: nessun segnale su {config.ACTIVE_TIMEFRAMES}.")
                continue
            chosen = _choose_signal(signals, coherence)
            if not chosen: continue
            chosen_score = int(chosen.get("score", 0)) + COHERENCE_BONUS.get(coherence, 0)
            if chosen_score < getattr(config, "SIGNAL_SCORE_THRESHOLD", 70):
                logging.info(f"{asset}: segnale scartato (score {chosen_score} < soglia).")
                continue
            strategy, side = chosen.get("strategy", "Unknown"), chosen.get("side", "Unknown")
            signal_str = f"{side.upper()} ({strategy})"
            entry = Decimal(str(round(chosen["entry_price"], 8)))
            sl = Decimal(str(round(chosen["sl"], 8))) if chosen.get("sl") is not None else None
            tp = Decimal(str(round(chosen["tp"], 8))) if chosen.get("tp") is not None else None
            timeframe_label = chosen.get("timeframe", "1d")
            details = str({"coherence": coherence, "raw_score": chosen.get("score", 0), "final_score": chosen_score, "engine": strategy, "selected_timeframe": timeframe_label, "available_timeframes": list(signals.keys())})
            new_signal = database.TechnicalSignal(asset=asset, timeframe=timeframe_label, strategy=strategy, signal=signal_str, entry_price=entry, stop_loss=sl, take_profit=tp, details=details)
            session.add(new_signal)
            logging.info(f"✅ NUOVO SEGNALE: {asset} [{timeframe_label}] {signal_str} | score={chosen_score} | coherence={coherence}")
    logging.info("=== Ciclo Multi-Timeframe completato ===")

if __name__ == "__main__":
    run_multi_timeframe_cycle()