import time
import schedule
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

from services import telegram_service_logic as logic
from database import init_db
from utils.network_utils import is_connected # <-- NUOVO IMPORT

def check_and_notify():
    """
    Controlla la presenza di nuovi segnali 'STRONG' nel database e invia
    notifiche tramite Telegram.
    """
    print(f"\n[{time.ctime()}] === CONTROLLO NUOVI SEGNALI PER TELEGRAM (v8.1 - Resiliente) ===")

    # --- CONTROLLO DI RETE PRELIMINARE ---
    # Anche se il DB è locale, la notifica richiede la rete.
    if not is_connected():
        print("❌ ERRORE DI RETE: Connessione a Internet assente. Impossibile inviare notifiche.")
        print("=== CICLO TELEGRAM INTERROTTO. Si riproverà al prossimo intervallo. ===")
        return # Interrompe l'esecuzione di questo ciclo

    try:
        logic.process_new_signals_for_telegram()
    except Exception as e:
        print(f"🔥 ERRORE CRITICO INASPETTATO nel ciclo di Telegram: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=== CONTROLLO TELEGRAM COMPLETATO. Prossimo ciclo tra 1 minuto. ===")


if __name__ == "__main__":
    print("🚀 Avvio del servizio Telegram 'Postino' del Progetto Phoenix...")
    init_db()

    # Esegui subito il primo controllo
    check_and_notify()

    # Pianifica i controlli successivi
    schedule.every(1).minutes.do(check_and_notify)

    while True:
        schedule.run_pending()
        time.sleep(1)
