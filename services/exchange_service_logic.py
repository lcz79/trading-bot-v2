from api_clients import bybit_client
from database import session_scope, PerformanceLog, OpenPosition
from datetime import datetime

def sync_account_balance():
    balance_data = bybit_client.get_wallet_balance()
    if balance_data:
        total_equity = float(balance_data.get('totalEquity', 0))
        unrealized_pnl = float(balance_data.get('totalUnrealizedProfit', 0))
        with session_scope() as session:
            log = PerformanceLog(
                timestamp=datetime.utcnow(),
                total_equity=total_equity,
                unrealized_pnl=unrealized_pnl
            )
            session.add(log)
        print(f"Saldo sincronizzato: Equity {total_equity}, P&L {unrealized_pnl}")
    else:
        print("Errore nel recupero del saldo.")

def sync_open_positions():
    """
    Sincronizza le posizioni aperte, gestendo correttamente il caso in cui non ci siano posizioni.
    """
    positions = bybit_client.get_open_positions()

    # Controlla se la chiamata API ha avuto successo (non è None)
    if positions is not None:
        with session_scope() as session:
            # Cancella sempre le posizioni vecchie per riflettere lo stato attuale
            session.query(OpenPosition).delete()

            # Se la lista non è vuota, aggiungi le nuove posizioni
            if positions:
                for pos in positions:
                    position = OpenPosition(
                        exchange='Bybit',
                        symbol=pos['symbol'],
                        position_side=pos['side'],
                        size=float(pos['size']),
                        entry_price=float(pos['avgPrice']),
                        pnl=float(pos.get('unrealizedPnl', 0))
                    )
                    session.add(position)
                print(f"Posizioni sincronizzate: {len(positions)} aperte.")
            else:
                # Se la lista è vuota, significa che non ci sono posizioni aperte
                print("Posizioni sincronizzate: 0 aperte.")
    else:
        # Questo blocco viene eseguito solo se la chiamata API è fallita (ha restituito None)
        print("Errore nel recupero delle posizioni (la chiamata API è fallita).")
