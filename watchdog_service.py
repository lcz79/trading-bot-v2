import time
import traceback
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# CORREZIONE: Carica le variabili d'ambiente PRIMA di qualsiasi altro import
load_dotenv()

from infra.logging import get_logger
from database import session_scope, ServiceHeartbeat, init_db
# In futuro, importeremo il client di Telegram per inviare alert
# from notification.telegram_client import send_telegram_alert

# --- CONFIGURAZIONE ---
WATCHDOG_INTERVAL_SECONDS = 60 # Ogni quanto il watchdog controlla
ALERT_THRESHOLD_SECONDS = 180  # Soglia per considerare un servizio 'down' (3 minuti)
SERVICES_TO_MONITOR = ["etl_service", "execution_service"] # Aggiungi qui altri servizi futuri

logger = get_logger(__name__)

class WatchdogService:
    def __init__(self):
        logger.info("service_initializing", service_name="WatchdogService")
        self.last_alerts = {} # Per evitare di inviare lo stesso alert ripetutamente

    def run(self):
        logger.info("service_startup", service_name="WatchdogService", interval=WATCHDOG_INTERVAL_SECONDS)
        while True:
            try:
                self.check_services_health()
                time.sleep(WATCHDOG_INTERVAL_SECONDS)
            except Exception as e:
                logger.critical("watchdog_main_loop_failed", error=str(e), traceback=traceback.format_exc())
                time.sleep(120)

    def check_services_health(self):
        logger.info("health_check_start", services_to_monitor=SERVICES_TO_MONITOR)
        with session_scope() as session:
            for service_name in SERVICES_TO_MONITOR:
                heartbeat = session.query(ServiceHeartbeat).filter(ServiceHeartbeat.service_name == service_name).first()
                
                if not heartbeat:
                    self._send_alert_if_new(service_name, f"🔴 CRITICAL: Il servizio '{service_name}' non ha MAI inviato un heartbeat!")
                    continue

                # Calcola da quanto tempo non riceviamo un battito
                age_seconds = (datetime.now(timezone.utc) - heartbeat.timestamp).total_seconds()

                if age_seconds > ALERT_THRESHOLD_SECONDS:
                    self._send_alert_if_new(service_name, f"⚠️ WARNING: Il servizio '{service_name}' non risponde da {int(age_seconds)} secondi.")
                else:
                    # Se il servizio torna online, resetta l'alert
                    if service_name in self.last_alerts:
                        self._send_alert_if_new(service_name, f"✅ OK: Il servizio '{service_name}' è di nuovo online.", reset=True)
                        logger.info("service_recovered", service_name=service_name)
                        
        logger.info("health_check_end")

    def _send_alert_if_new(self, service_name, message, reset=False):
        """Invia un alert solo se è cambiato rispetto all'ultimo inviato per quel servizio."""
        last_message = self.last_alerts.get(service_name)
        
        if reset:
            # Se stiamo resettando, invia il messaggio di "OK" e rimuovi lo stato di alert
            if last_message:
                self._send_alert(message)
                del self.last_alerts[service_name]
            return

        if last_message != message:
            self._send_alert(message)
            self.last_alerts[service_name] = message
    
    def _send_alert(self, message: str):
        """Invia un messaggio di allerta (placeholder)."""
        logger.warning("sending_alert", alert_message=message)
        # In futuro, qui ci sarà la chiamata al bot di Telegram
        # send_telegram_alert(message, channel="CRITICAL_ALERTS")


if __name__ == "__main__":
    logger.info("service_pre_startup", service_name="WatchdogService")
    # init_db() viene chiamato implicitamente quando si importa da database,
    # ma è buona pratica assicurarsi che le variabili siano caricate prima.
    init_db()
    service = WatchdogService()
    service.run()
