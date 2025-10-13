# delete_test_signals.py - v2.0 (Modalità Pulizia Totale)
# ATTENZIONE: Questa versione dello script cancella TUTTI i segnali dal database.
# È utile per ripartire da zero dopo modifiche importanti alla logica di generazione.

import sqlite3
import os

# --- CONFIGURAZIONE ---
DB_FILE = "trading_signals.db"

def run_total_cleanup():
    """
    Si connette al database e cancella TUTTI i segnali registrati.
    """
    if not os.path.exists(DB_FILE):
        print(f"✅ File del database '{DB_FILE}' non trovato. Nessuna pulizia necessaria.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Conta quanti segnali ci sono prima di cancellarli
        cursor.execute("SELECT COUNT(*) FROM signals")
        count_before = cursor.fetchone()[0]

        if count_before == 0:
            print("✅ Il database è già vuoto. Nessuna pulizia necessaria.")
            conn.close()
            return

        print(f"Trovati {count_before} segnali totali. Inizio pulizia completa...")
        
        # Chiede una conferma all'utente prima di procedere
        confirm = input("⚠️ ATTENZIONE: Stai per cancellare TUTTI i segnali. Sei sicuro? (s/n): ")
        if confirm.lower() != 's':
            print("Pulizia annullata dall'utente.")
            conn.close()
            return

        # Esegue il comando SQL per cancellare tutte le righe
        cursor.execute("DELETE FROM signals")
        
        # Resetta anche il contatore dell'autoincremento per ripartire da 1
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='signals'")
        
        # Verifica il numero di righe cancellate
        deleted_count = cursor.rowcount
        
        # Salva le modifiche
        conn.commit()

        print(f"✅ Pulizia totale completata. {count_before} segnali sono stati rimossi.")

    except Exception as e:
        print(f"❌ ERRORE durante la pulizia del database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("--- Avvio Script di Pulizia Totale del Database ---")
    run_total_cleanup()
