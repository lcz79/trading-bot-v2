import time
import schedule
from dotenv import load_dotenv
import traceback

# Carica le variabili d'ambiente
load_dotenv()

from services import telegram_service_logic as logic
from database import init_db
from utils.network_utils import is_connected

def check_and_notify():
    """
    Esegue il ciclo completo di notifiche:
    1. Invia nuovi segnali non ancora notificati.
    2. Invia suggerimenti di gestione per le posizioni aperte.
    """
    print(f"\n[{time.ctime()}] === AVVIO CICLO NOTIFICHE TELEGRAM (v9.0 - Gestione Attiva) ===")

    if not is_connected():
        print("❌ ERRORE DI RETE: Connessione a Internet assente.")
        print("=== CICLO TELEGRAM INTERROTTO. Prossimo ciclo tra 5 minuti. ===")
        return

    try:
        # 1. Processa e invia i nuovi segnali di trading
        print("-> Controllo nuovi segnali...")
        logic.process_new_signals_for_telegram()

        # 2. Processa e invia suggerimenti per le posizioni aperte
        print("\n-> Controllo gestione posizioni...")
        logic.process_position_management_suggestions()

    except Exception as e:
        print(f"🔥 ERRORE CRITICO INASPETTATO nel ciclo di Telegram: {e}")
        traceback.print_exc()
    finally:
        print(f"=== CICLO NOTIFICHE COMPLETATO. Prossimo ciclo tra 5 minuti. ===")


if __name__ == "__main__":
    print("🚀 Avvio del servizio Telegram 'Postino' del Progetto Phoenix (v9.0)...")
    init_db()

    # Esegui subito il primo ciclo completo
    check_and_notify()

    # Pianifica i cicli successivi ogni 5 minuti
    schedule.every(5).minutes.do(check_and_notify)

    while True:
        schedule.run_pending()
        time.sleep(1)
