# --- PRIMISSIMA COSA DA FARE: CARICARE LE VARIABILI D'AMBIENTE ---
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------

import time
import schedule
from decimal import Decimal, InvalidOperation

import database
from api_clients import bybit_client

def sync_exchange_data():
    """
    Sincronizza i dati del conto (saldo, posizioni) dall'exchange al nostro database.
    """
    print(f"\n[{time.ctime()}] === AVVIO CICLO SYNC EXCHANGE (v7.1 - Env Fix) ===")
    
    try:
        with database.session_scope() as session:
            
            # --- 1. Recupero Saldo e Log Performance ---
            balance_data = bybit_client.get_wallet_balance()
            if balance_data:
                try:
                    total_equity = Decimal(balance_data.get('totalEquity', '0'))
                    unrealized_pnl = Decimal(balance_data.get('totalUnrealisedPnl', '0'))
                    
                    new_perf_log = database.PerformanceLog(
                        total_equity=total_equity,
                        unrealized_pnl=unrealized_pnl
                    )
                    session.add(new_perf_log)
                    print(f"-> Performance Log: Equity ${total_equity:.2f}, PNL ${unrealized_pnl:.2f}")

                except InvalidOperation:
                    print("ERRORE: Dati del saldo non validi dall'API.")
            else:
                print("-> ATTENZIONE: Impossibile recuperare il saldo del portafoglio.")

            # --- 2. Sincronizzazione Posizioni Aperte ---
            api_positions = bybit_client.get_open_positions()
            api_position_keys = set() 

            print(f"-> Trovate {len(api_positions)} posizioni aperte sull'exchange.")

            for pos_data in api_positions:
                try:
                    symbol = pos_data['symbol']
                    size_val = Decimal(pos_data.get('size', '0'))
                    side = 'long' if size_val > 0 else 'short'
                    
                    position_key = (symbol, side)
                    api_position_keys.add(position_key)

                    db_pos = session.query(database.OpenPosition).filter_by(
                        symbol=symbol, 
                        position_side=side,
                        exchange='Bybit'
                    ).first()

                    if db_pos:
                        db_pos.size = abs(size_val)
                        db_pos.entry_price = Decimal(pos_data.get('avgPrice', '0'))
                        db_pos.pnl = Decimal(pos_data.get('unrealisedPnl', '0'))
                    else:
                        new_db_pos = database.OpenPosition(
                            exchange='Bybit', symbol=symbol, position_side=side,
                            size=abs(size_val), entry_price=Decimal(pos_data.get('avgPrice', '0')),
                            pnl=Decimal(pos_data.get('unrealisedPnl', '0'))
                        )
                        session.add(new_db_pos)
                        print(f"-> NUOVA POSIZIONE RILEVATA e salvata: {symbol} ({side})")

                except (InvalidOperation, KeyError) as e:
                    print(f"ERRORE: Dati posizione non validi dall'API per {pos_data.get('symbol', 'N/A')}. Errore: {e}")

            # --- 3. Pulizia Posizioni Chiuse ---
            db_positions_to_check = session.query(database.OpenPosition).filter_by(exchange='Bybit').all()
            closed_count = 0
            for db_pos in db_positions_to_check:
                if (db_pos.symbol, db_pos.position_side) not in api_position_keys:
                    print(f"-> POSIZIONE CHIUSA RILEVATA: {db_pos.symbol} ({db_pos.position_side}). Rimuovendo dal DB...")
                    session.delete(db_pos)
                    closed_count += 1
            
            if closed_count > 0:
                print(f"-> {closed_count} posizioni chiuse rimosse dal database.")

    except Exception as e:
        print(f"ERRORE FATALE nel ciclo di sync exchange: {e}")

    print("=== CICLO SYNC EXCHANGE COMPLETATO ===")


if __name__ == '__main__':
    database.init_db()

    schedule.every(15).minutes.do(sync_exchange_data)
    
    print("\n--- Avvio Servizio Exchange (v7.1 - Env Fix) ---")
    print("Servizio avviato. Il primo ciclo di sync inizierà tra 15 minuti.")
    print("Questo terminale deve rimanere aperto.")

    sync_exchange_data()

    while True:
        schedule.run_pending()
        time.sleep(1)
