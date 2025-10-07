import time
import schedule
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

from services import exchange_service_logic as logic
from database import init_db
from utils.network_utils import is_connected # <-- NUOVO IMPORT

def sync_exchange_data():
    """
    Ciclo principale per sincronizzare i dati dell'exchange (saldo, posizioni).
    """
    print(f"\n[{time.ctime()}] === AVVIO CICLO SYNC EXCHANGE (v8.1 - Resiliente) ===")

    # --- CONTROLLO DI RETE PRELIMINARE ---
    if not is_connected():
        print("❌ ERRORE DI RETE: Connessione a Internet assente. Il ciclo di sincronizzazione è stato saltato.")
        print("=== CICLO SYNC INTERROTTO. Si riproverà al prossimo intervallo. ===")
        return # Interrompe l'esecuzione di questo ciclo

    try:
        # Sincronizza il saldo (equity)
        logic.sync_account_balance()
        
        # Sincronizza le posizioni aperte
        logic.sync_open_positions()

    except Exception as e:
        print(f"🔥 ERRORE CRITICO INASPETTATO nel ciclo di sync exchange: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=== CICLO SYNC COMPLETATO. Prossimo ciclo tra 5 minuti. ===")

if __name__ == "__main__":
    print("🚀 Avvio del servizio Exchange 'Contabile' del Progetto Phoenix...")
    init_db()

    # Esegui subito la prima sincronizzazione
    sync_exchange_data()

    # Pianifica le sincronizzazioni successive
    schedule.every(5).minutes.do(sync_exchange_data)

    while True:
        schedule.run_pending()
        time.sleep(1)
