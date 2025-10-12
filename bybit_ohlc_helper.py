# bybit_ohlc_helper.py
from typing import Optional, List, Dict
import time

# Atteso: sessione pybit.unified_trading.HTTP già creata dal tuo codice principale.
# Questo helper NON crea la session, la riceve dall'esterno.

def _fetch_kline(session, symbol: str, interval: str, limit: int = 200) -> Optional[List[Dict]]:
    """
    Chiama l'endpoint kline v5 di Bybit con la sessione pybit.
    Ritorna una lista di candele o None se l'API fallisce.
    """
    try:
        # pybit unificato usa: get_kline(category, symbol, interval, limit, ...)
        # Per spot/linear solitamente category="linear" o "spot".
        # Proveremo in ordine: "linear" -> "spot".
        for category in ("linear", "spot"):
            resp = session.get_kline(
                category=category, symbol=symbol, interval=interval, limit=limit
            )
            # Struttura attesa: {'retCode':0, 'result':{'list': [...]}}
            if resp and resp.get("retCode") == 0:
                result = resp.get("result") or {}
                data = result.get("list") or []
                if data:
                    return data
            # Piccola pausa tra tentativi per evitare rate-limit
            time.sleep(0.1)
        return None
    except Exception:
        return None

def get_ohlc_with_fallback(session, symbol: str, limit: int = 200) -> Optional[dict]:
    """
    Tenta di ottenere OHLC in 1D. Se non disponibile, prova 4H.
    Ritorna un dict: {'interval':'1D'|'4H', 'data':[...]} oppure None.
    """
    # 1) Prova daily (1D)
    data_1d = _fetch_kline(session, symbol, interval="D", limit=limit)  # "D" = 1D su v5
    if data_1d:
        return {"interval": "1D", "data": data_1d}

    # 2) Fallback a 4H
    data_4h = _fetch_kline(session, symbol, interval="240", limit=limit)  # 240 minuti = 4H
    if data_4h:
        return {"interval": "4H", "data": data_4h}

    # 3) Niente dati disponibili
    return None

