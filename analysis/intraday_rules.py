# analysis/intraday_rules.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config
from analysis.session_clock import minutes_to_close, in_session

@dataclass
class IntradayState:
    """Mantiene lo stato della giornata di trading. In produzione, andrebbe su DB."""
    tz: ZoneInfo = ZoneInfo(config.TIMEZONE)
    trading_day: str = ""
    realized_pnl_usd: float = 0.0
    trades_count: int = 0
    last_loss_time: datetime | None = None

    def reset_if_new_day(self, now: datetime):
        """Azzera le statistiche giornaliere se inizia un nuovo giorno di trading."""
        day_str = now.date().isoformat()
        if self.trading_day != day_str:
            self.trading_day = day_str
            self.realized_pnl_usd = 0.0
            self.trades_count = 0
            self.last_loss_time = None
            print(f"Nuovo giorno di trading: {day_str}. Stato azzerato.")


class IntradayRules:
    """Implementa le regole di rischio e i guardrail per il trading intraday."""
    def __init__(self):
        self.max_loss_perc_day = config.MAX_LOSS_PERC_DAY
        self.max_trades_per_day = config.MAX_TRADES_PER_DAY
        self.cooldown_min_after_loss = config.COOLDOWN_MIN_AFTER_LOSS
        self.min_minutes_before_close = config.MIN_MINUTES_BEFORE_CLOSE
        self.min_signal_score = config.INTRADAY_SIGNAL_SCORE_THRESHOLD

    def allow_new_trade(self, *, now: datetime, equity: float, state: IntradayState, signal_score: int) -> tuple[bool, str]:
        """Controlla se tutte le condizioni per aprire un nuovo trade sono soddisfatte."""
        state.reset_if_new_day(now)

        if not in_session(now):
            return False, "Fuori orario di sessione"

        if minutes_to_close(now) < self.min_minutes_before_close:
            return False, "Troppo vicino alla chiusura per nuovi ingressi"

        if state.trades_count >= self.max_trades_per_day:
            return False, f"Raggiunto max trades giornalieri ({self.max_trades_per_day})"

        daily_loss_usd = self.max_loss_perc_day * equity
        if equity > 0 and state.realized_pnl_usd <= -daily_loss_usd:
            return False, f"Raggiunto il loss cap giornaliero (Perdita: ${state.realized_pnl_usd:.2f})"

        if state.last_loss_time:
            cooldown_end_time = state.last_loss_time + timedelta(minutes=self.cooldown_min_after_loss)
            if now < cooldown_end_time:
                return False, f"Cooldown attivo dopo una perdita fino alle {cooldown_end_time.strftime('%H:%M:%S')}"

        if signal_score < self.min_signal_score:
            return False, f"Score segnale ({signal_score}) sotto soglia ({self.min_signal_score})"

        return True, "OK"

    def on_filled(self, state: IntradayState):
        """Aggiorna lo stato dopo l'apertura di un trade."""
        state.trades_count += 1

    def on_closed_trade(self, state: IntradayState, realized_pnl: float, now: datetime):
        """Aggiorna lo stato dopo la chiusura di un trade."""
        state.realized_pnl_usd += realized_pnl
        if realized_pnl < 0:
            state.last_loss_time = now