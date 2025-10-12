# etl_service.py - Phoenix ETL v7.1 (Real Technical Analysis)
# ----------------------------------------------------------------
# - Fundamentals CoinGecko (bulk) -> DB (fundamentals)
# - Technical Analysis Bybit (EMA200/EMA50 + RSI14) -> DB (technical_signals)
# - Scheduler 30 min + esecuzione immediata
# ----------------------------------------------------------------

from dotenv import load_dotenv
from pathlib import Path
import os
import time
import math
import json
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import schedule
from pybit.unified_trading import HTTP

# === CONFIGURAZIONE LOG ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === CONFIG AMBIENTE ===
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

# === IMPORT LOCALI ===
import database
from database import session_scope, FundamentalAsset, TechnicalSignal
from api_clients.coingecko_client import CoinGeckoClient

# === PARAMETRI ===
ASSETS_TO_ANALYZE = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC", "DOT"]
TIMEFRAME_PRIMARY = "D"   # Bybit v5: "D" = 1D
TIMEFRAME_FALLBACK = "240"  # 240 minuti = 4H
MAX_BARS = 300

# === Mappa ID "sicuri" per nomi noti (usata solo come fallback logico)
FIXED_COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",  # spesso 'matic-network'; il client dinamico gestisce comunque
    "DOT": "polkadot"
}

# ======================================================================
#                      FUNZIONI TECNICHE (EMA & RSI)
# ======================================================================

def ema(series, period):
    """Calcola EMA (Exponential Moving Average) semplice e robusta."""
    if not series or len(series) < period:
        return [None] * len(series)
    k = 2 / (period + 1)
    ema_vals = [None] * len(series)
    # prima EMA come SMA iniziale
    sma = sum(series[:period]) / period
    ema_vals[period-1] = sma
    prev = sma
    for i in range(period, len(series)):
        val = series[i]
        prev = (val - prev) * k + prev
        ema_vals[i] = prev
    return ema_vals

def rsi(series, period=14):
    """Calcola RSI14 classico (Wilder). Ritorna lista con None dove non disponibile."""
    if not series or len(series) < period + 1:
        return [None] * len(series)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(series)):
        diff = series[i] - series[i-1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    # medie iniziali
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    rsi_vals = [None] * len(series)
    # primo valore RSI alla posizione period
    rs = avg_gain / avg_loss if avg_loss != 0 else math.inf
    rsi_vals[period] = 100 - (100 / (1 + rs))
    # valori successivi (RMA)
    for i in range(period+1, len(series)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else math.inf
        rsi_vals[i] = 100 - (100 / (1 + rs))
    return rsi_vals

def decide_signal(close, ema50, ema200, rsi14):
    """
    Regole:
      LONG  se close > EMA200 and EMA50 > EMA200 and RSI > 55
      SHORT se close < EMA200 and EMA50 < EMA200 and RSI < 45
      else  NEUTRAL
    """
    if ema200 is None or ema50 is None or rsi14 is None or close is None:
        return "NEUTRAL"
    if close > ema200 and ema50 > ema200 and rsi14 > 55:
        return "LONG"
    if close < ema200 and ema50 < ema200 and rsi14 < 45:
        return "SHORT"
    return "NEUTRAL"

# ======================================================================
#                        BYBIT: FETCH OHLC + TA
# ======================================================================

def fetch_kline(http, symbol_usdt, interval, limit=MAX_BARS):
    """Ritorna lista di candele Bybit v5 (result.list) oppure []."""
    for category in ("linear", "spot"):
        try:
            resp = http.get_kline(category=category, symbol=symbol_usdt, interval=interval, limit=limit)
            if resp and resp.get("retCode") == 0:
                data = (resp.get("result") or {}).get("list") or []
                if data:
                    return data
        except Exception as e:
            logging.warning(f"Bybit get_kline errore {symbol_usdt} [{category}/{interval}]: {e}")
        time.sleep(0.1)
    return []

def parse_closes(bybit_list):
    """
    Bybit v5: ogni item è tipicamente [start, open, high, low, close, volume, turnover]
    Close = item[4]
    """
    closes = []
    for item in bybit_list:
        try:
            closes.append(float(item[4]))
        except Exception:
            continue
    return closes

def analyze_symbol(http, base_symbol):
    """
    Scarica OHLC (1D, fallback 4H) e calcola EMA50/EMA200 + RSI14.
    Ritorna dict con: symbol, timeframe, direction, score, entry, tp, sl, details
    oppure None se non segnale.
    """
    symbol_usdt = f"{base_symbol}USDT"

    # 1) prova 1D
    data = fetch_kline(http, symbol_usdt, TIMEFRAME_PRIMARY, MAX_BARS)
    used_interval = "1D"
    # 2) fallback 4H
    if len(data) < 200:
        data = fetch_kline(http, symbol_usdt, TIMEFRAME_FALLBACK, MAX_BARS)
        used_interval = "4H"
    if len(data) < 50:
        logging.warning(f"Nessun dato sufficiente per {symbol_usdt}")
        return None

    closes = parse_closes(data)
    if len(closes) < 200:
        logging.warning(f"Dati insufficienti per calcolo EMA200 ({symbol_usdt}, {len(closes)} barre)")
        return None

    ema50_vals = ema(closes, 50)
    ema200_vals = ema(closes, 200)
    rsi_vals = rsi(closes, 14)

    last_close = closes[-1]
    last_ema50 = ema50_vals[-1]
    last_ema200 = ema200_vals[-1]
    last_rsi = rsi_vals[-1]

    direction = decide_signal(last_close, last_ema50, last_ema200, last_rsi)
    if direction == "NEUTRAL":
        return None

    # score semplice: media normalizzata delle tre condizioni
    cond_trend = 1.0 if (direction == "LONG" and last_ema50 > last_ema200) or (direction == "SHORT" and last_ema50 < last_ema200) else 0.5
    cond_distance = min(abs(last_close - last_ema200) / last_ema200, 0.05) / 0.05  # 0..1, limitato 5%
    cond_rsi = (last_rsi - 50) / 50 if direction == "LONG" else (50 - last_rsi) / 50
    cond_rsi = max(0.0, min(cond_rsi, 1.0))
    score = round((cond_trend + cond_distance + cond_rsi) / 3 * 100, 2)

    # TP/SL:  +2% / -1% (o viceversa)
    if direction == "LONG":
        entry = last_close
        tp = entry * 1.02
        sl = entry * 0.99
    else:  # SHORT
        entry = last_close
        tp = entry * 0.98
        sl = entry * 1.01

    details = {
        "ema50": round(last_ema50, 6) if last_ema50 else None,
        "ema200": round(last_ema200, 6) if last_ema200 else None,
        "rsi14": round(last_rsi, 2) if last_rsi else None,
        "timeframe": used_interval,
        "close": round(last_close, 6),
    }

    return {
        "symbol": base_symbol,
        "timeframe": used_interval,
        "direction": direction,
        "score": score,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "details": details
    }

# ======================================================================
#                        COINGECKO: BULK & SAVE
# ======================================================================

def save_fundamentals_bulk(cg_client, base_symbols):
    """Richiede dati in bulk e salva nella tabella fundamentals."""
    logging.info(f"Richiesta bulk a CoinGecko per {len(base_symbols)} asset...")
    # Usa il metodo bulk del tuo client (v7.0)
    market_data = cg_client.get_crypto_bulk_data(base_symbols)
    if not market_data:
        logging.warning("Nessun dato ricevuto da CoinGecko.")
        return 0

    # Salva su DB
    saved = 0
    with session_scope() as session:
        for asset in market_data:
            try:
                symbol = str(asset.get("symbol", "")).upper()
                # fallback a mappa fissa se servisse coin_id
                coin_id = asset.get("id") or FIXED_COINGECKO_IDS.get(symbol, symbol.lower())
                entry = FundamentalAsset(
                    symbol=symbol,
                    coin_id=coin_id,
                    name=asset.get("name"),
                    market_cap=asset.get("market_cap"),
                    volume_24h=asset.get("total_volume"),
                    price=asset.get("current_price"),
                    change_24h=asset.get("price_change_percentage_24h"),
                    rank=asset.get("market_cap_rank")
                )
                session.add(entry)
                saved += 1
            except Exception as e:
                logging.warning(f"Errore salvataggio fundamentals per {symbol}: {e}")
    logging.info(f"💾 Dati fondamentali salvati per {saved} asset.")
    return saved

# ======================================================================
#                           CICLO ETL
# ======================================================================

def run_etl_cycle():
    logging.info("=== AVVIO CICLO DI ANALISI ETL (v7.1) ===")
    try:
        # ---------- FASE 1: FUNDAMENTALS ----------
        cg_client = CoinGeckoClient()
        base_symbols = [s.replace("USDT", "").upper() for s in ASSETS_TO_ANALYZE]
        save_fundamentals_bulk(cg_client, base_symbols)

        # ---------- FASE 2: ANALISI TECNICA ----------
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")
        http = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

        results = []
        logging.info("Fase 2: Analisi tecniche (Bybit)...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(analyze_symbol, http, sym): sym for sym in base_symbols}
            for fut in as_completed(futures):
                res = fut.result()
                sym = futures[fut]
                if res:
                    results.append(res)
                    logging.info(f"📊 Segnale {res['direction']} {res['timeframe']} per {sym} (score {res['score']}).")
                else:
                    logging.info(f"— Nessun segnale per {sym} (condizioni non allineate).")

        # ---------- SALVATAGGIO SEGNALI ----------
        if results:
            with session_scope() as session:
                for r in results:
                    tech_signal = TechnicalSignal(
                        asset=r["symbol"],
                        timeframe=r["timeframe"],
                        strategy="EMA200+EMA50+RSI14",
                        signal=r["direction"],
                        entry_price=r["entry"],
                        take_profit=r["tp"],
                        stop_loss=r["sl"],
                        details=json.dumps({
                            "final_score": r["score"],
                            **r["details"]
                        })
                    )
                    session.add(tech_signal)
            logging.info(f"✅ Salvati {len(results)} segnali tecnici nel database.")
        else:
            logging.info("Nessun segnale tecnico da salvare in questo ciclo.")

        logging.info("=== ✅ CICLO COMPLETATO - Prossimo tra 30 minuti ===")

    except Exception as e:
        logging.error(f"❌ Errore nel ciclo ETL: {e}")
        traceback.print_exc()

# ======================================================================
#                        SCHEDULER / MAIN
# ======================================================================

def start_scheduler():
    logging.info("--- Avvio Servizio ETL (v7.1 - Real TA) ---")
    database.init_db()
    schedule.every(30).minutes.do(run_etl_cycle)
    run_etl_cycle()
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    start_scheduler()
