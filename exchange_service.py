import time
import schedule
from api_clients import bybit_client
import database

def fetch_and_store_performance():
    """
    Recupera i dati di performance del conto e li salva nel database.
    Ora calcola il P&L reale e usa il simbolo dell'Euro.
    """
    print(f"[{time.ctime()}] Esecuzione fetch_and_store_performance...")
    
    wallet_data = bybit_client.get_wallet_balance()
    if not wallet_data:
        print("-> Errore: Impossibile recuperare il saldo del portafoglio.")
        return

    total_equity = float(wallet_data.get('totalEquity', 0))
    
    open_positions = bybit_client.get_open_positions()
    
    total_unrealized_pnl = 0.0
    if open_positions:
        for position in open_positions:
            if float(position.get('size', 0)) > 0:
                total_unrealized_pnl += float(position.get('unrealisedPnl', 0))

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    realized_pnl_24h = 0.0

    conn = database.create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO performance_log (timestamp, total_equity, unrealized_pnl, realized_pnl_24h)
        VALUES (?, ?, ?, ?)
        """, (timestamp, total_equity, total_unrealized_pnl, realized_pnl_24h))
        conn.commit()
        conn.close()
        # --- MODIFICA VALUTA ---
        print(f"-> Successo! Dati salvati: Equity=€{total_equity:,.2f}, PnL non Real.=€{total_unrealized_pnl:,.2f}")
    else:
        print("-> Errore: Connessione al database fallita.")

if __name__ == '__main__':
    print("--- Avvio Servizio Monitoraggio Exchange (v1.3 EUR Edition) ---")
    
    fetch_and_store_performance()

    schedule.every(15).minutes.do(fetch_and_store_performance)
    print("Servizio pianificato. Prossima esecuzione tra 15 minuti.")

    while True:
        schedule.run_pending()
        time.sleep(1)
