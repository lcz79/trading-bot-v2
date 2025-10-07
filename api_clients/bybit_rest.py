# api_clients/bybit_rest.py
# ------------------------------------------------------------------
# Alternativa REST "hard-timeout" a pybit per scaricare K-line.
# Usa la sessione robusta di infra/http.py con retry & timeout.
#
# Puoi usarla per testare/aggirare eventuali freeze legati a pybit.
# ------------------------------------------------------------------

import pandas as pd
from infra.http import new_session, DEFAULT_TIMEOUT

BASE_URL = "https://api.bybit.com"
_s = new_session()

INTERVAL_MAP = {"1h": "60", "4h": "240", "1d": "D"}

def get_klines(symbol: str, timeframe: str, category: str = "linear", limit: int = 200) -> pd.DataFrame:
    """
    Scarica kline da Bybit v5/market/kline.
    category: "spot" | "linear" | "inverse" (se usi derivati, "linear")
    """
    iv = INTERVAL_MAP.get(timeframe.lower())
    if not iv:
        raise ValueError(f"Interval non supportato: {timeframe}")

    params = {
        "category": category,
        "symbol": symbol,
        "interval": iv,
        "limit": limit
    }

    r = _s.get(f"{BASE_URL}/v5/market/kline", params=params, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    payload = r.json()

    if payload.get("retCode") != 0:
        raise RuntimeError(f"Bybit retCode={payload.get('retCode')} retMsg={payload.get('retMsg')}")

    rows = payload.get("result", {}).get("list", [])
    if not rows:
        return pd.DataFrame()

    # Bybit restituisce: [timestamp, open, high, low, close, volume, turnover]
    df = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v", "turnover"])
    df["t"] = pd.to_datetime(df["t"].astype("int64"), unit="ms")
    df.set_index("t", inplace=True)
    df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(
        pd.to_numeric, errors="coerce"
    )
    return df.sort_index()