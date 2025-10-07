import sys
import signal
import faulthandler

def enable(sigusr1=True, periodic_seconds=None):
    """
    Attiva faulthandler.
    sigusr1=True  -> abilita dump via segnale SIGUSR1
    periodic_seconds=int -> dump periodico di tutti i thread
    """
    faulthandler.enable()

    if sigusr1:
        try:
            faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)
        except Exception:
            pass

    if periodic_seconds and isinstance(periodic_seconds, int) and periodic_seconds > 0:
        faulthandler.dump_traceback_later(timeout=periodic_seconds, repeat=True)
