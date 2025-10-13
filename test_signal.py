# test_signal.py
import database as db
from datetime import datetime
import random

def run_test():
    """
    Inserisce un segnale di test nel database per verificare
    che la pipeline di visualizzazione funzioni.
    """
    print("--- Avvio Test di Integrità del Database ---")
    
    # Scegliamo una direzione a caso per rendere il test diverso ogni volta
    signal_type = random.choice(["LONG", "SHORT"])
    strategy = random.choice(["Day Trading (Trend Following)", "Scalping (Counter-Trend)"])
    
    test_signal = {
        "timestamp": datetime.utcnow(),
        "symbol": "BTCUSDT",
        "signal_type": signal_type,
        "timeframe": "TEST",
        "strategy": strategy,
        "score": 99.9,
        "details": f"SEGNALE DI TEST GENERATO MANUALMENTE ALLE {datetime.utcnow().strftime('%H:%M:%S')}"
    }
    
    try:
        db.save_signal(test_signal)
        print("\n✅ Segnale di test inserito con successo nel database.")
        print("\n--- COSA FARE ADESSO ---")
        print("1. Vai sulla tua dashboard nel browser.")
        print("2. Clicca sul pulsante 'Aggiorna Dati' in fondo alla pagina.")
        print("3. Controlla se il segnale di test per BTCUSDT appare nella tabella.")
        
    except Exception as e:
        print(f"\n❌ ERRORE: Impossibile inserire il segnale di test.")
        print(f"Dettagli errore: {e}")

if __name__ == "__main__":
    run_test()