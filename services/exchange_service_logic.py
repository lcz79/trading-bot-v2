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
    positions = bybit_client.get_open_positions()
    if positions:
        with session_scope() as session:
            session.query(OpenPosition).delete()
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
        print("Errore nel recupero delle posizioni.")