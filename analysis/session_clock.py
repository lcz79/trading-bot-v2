# analysis/session_clock.py (v2.0 - Backtest-Aware)
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import config

TZ = ZoneInfo(config.TIMEZONE)
SESSION_START = config.SESSION_START_TIME
SESSION_END   = config.SESSION_END_TIME
EOD_MARGIN_MIN = config.EOD_FLATTEN_WINDOW_MIN

def now_it() -> datetime:
    """Restituisce l'ora corrente nel fuso orario della sessione."""
    return datetime.now(TZ)

def session_bounds(for_date: datetime):
    """
    Restituisce gli orari di inizio e fine della sessione di trading
    PER LA DATA SPECIFICATA.
    """
    # Usa il giorno della data passata come argomento, non il giorno corrente.
    d = for_date.date()
    start = datetime.combine(d, SESSION_START, TZ)
    end   = datetime.combine(d, SESSION_END,   TZ)
    return start, end

def in_session(ts: datetime | None = None) -> bool:
    """Controlla se siamo all'interno della finestra operativa."""
    ts = ts or now_it()
    # Calcola i limiti della sessione per il giorno del timestamp che stiamo controllando.
    start, end = session_bounds(for_date=ts)
    return start <= ts <= end

def minutes_to_close(ts: datetime | None = None) -> int:
    """Restituisce i minuti rimanenti alla chiusura della sessione."""
    ts = ts or now_it()
    if not in_session(ts):
        return 0
    _, end = session_bounds(for_date=ts)
    delta = end - ts
    return max(0, int(delta.total_seconds() // 60))

def is_eod_window(ts: datetime | None = None) -> bool:
    """Controlla se siamo nella finestra di "fine giornata" per chiudere le posizioni."""
    return in_session(ts) and minutes_to_close(ts) <= EOD_MARGIN_MIN
