# exchange_service.py - v5.0.0 (Verified Final)
# Motore principale del servizio "Contabile".

from dotenv import load_dotenv
load_dotenv()

import time
import schedule
import traceback
import database
from services import exchange_service_logic as logic

SYNC_INTERVAL_MINUTES = 5

def sync_exchange_data():
    """Funzione principale che orchestra la sincronizzazione."""
    print(f"\n[{time.ctime()}] === AVVIO CICLO SYNC EXCHANGE ===")
    try:
        logic.sync_account_balance()
        logic.sync_open_positions()
    except Exception as e:
        print(f"🔥 ERRORE CRITICO INASPETTATO nel ciclo di sync: {e}")
        traceback.print_exc()
    finally:
        print(f"=== CICLO SYNC COMPLETATO. Prossimo ciclo tra {SYNC_INTERVAL_MINUTES} minuti. ===")

if __name__ == "__main__":
    print("🚀 Avvio del servizio Exchange 'Contabile' del Progetto Phoenix...")
    database.init_db()
    
    # Esegui un primo ciclo all'avvio
    sync_exchange_data()

    # Pianifica le esecuzioni future
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_exchange_data)
    print(f"✅ Servizio pianificato. Il ciclo si ripeterà ogni {SYNC_INTERVAL_MINUTES} minuti.")

    # Ciclo infinito per mantenere il servizio attivo
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Servizio 'Contabile' arrestato manualmente.")
            break
