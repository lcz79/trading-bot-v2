# services/exchange_service_logic.py - v5.0.1 (Safe Key Access)
# Utilizza il metodo .get() per accedere alle chiavi API opzionali,
# prevenendo i KeyError quando una chiave non è presente.

from database import session_scope, PerformanceLog, OpenPosition
from api_clients.bybit_client import BybitClient

def sync_account_balance():
    """Recupera il saldo del conto e lo salva nel PerformanceLog."""
    print("  -> Sincronizzazione saldo conto...")
    try:
        client = BybitClient()
        balance_data = client.session.get_wallet_balance(accountType="UNIFIED")

        if balance_data and balance_data.get('retCode') == 0:
            wallet_info = balance_data['result']['list'][0]
            total_equity = float(wallet_info.get('totalEquity', 0.0))
            
            # --- CORREZIONE CON ACCESSO SICURO (.get) ---
            # Se la chiave 'unrealizedPnl' non esiste, usa 0.0 come valore di default.
            unrealized_pnl = float(wallet_info.get('unrealizedPnl', 0.0))
            # ---------------------------------------------
            
            realized_pnl = 0.0 # Placeholder

            with session_scope() as session:
                new_log = PerformanceLog(
                    total_equity=total_equity,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=realized_pnl
                )
                session.add(new_log)
            print(f"  ✅ Saldo aggiornato: Equity ${total_equity:,.2f}")
        else:
            ret_msg = balance_data.get('retMsg', 'Errore API sconosciuto') if balance_data else "Nessuna risposta dall'API"
            print(f"  - ⚠️ Impossibile recuperare il saldo: {ret_msg}")

    except Exception as e:
        print(f"  - 🔥 ERRORE CRITICO in sync_account_balance: {e}")


def sync_open_positions():
    """Recupera le posizioni aperte e le sincronizza con il database."""
    print("  -> Sincronizzazione posizioni aperte...")
    try:
        client = BybitClient()
        positions_data = client.session.get_positions(
            category="linear", 
            settleCoin="USDT"
        )

        if positions_data and positions_data.get('retCode') == 0:
            open_positions = [p for p in positions_data['result']['list'] if float(p.get('size', 0)) > 0]
            
            with session_scope() as session:
                session.query(OpenPosition).delete()
                for pos in open_positions:
                    new_pos = OpenPosition(
                        symbol=pos['symbol'], side=pos['side'],
                        entry_price=float(pos['avgPrice']), size=float(pos['size']),
                        position_value=float(pos['positionValue']), leverage=int(pos['leverage'])
                    )
                    session.add(new_pos)
                print(f"  ✅ Trovate e sincronizzate {len(open_positions)} posizioni aperte.")
        else:
            ret_msg = positions_data.get('retMsg', 'Errore API sconosciuto') if positions_data else "Nessuna risposta dall'API"
            print(f"  - ⚠️ Impossibile recuperare le posizioni: {ret_msg}")

    except Exception as e:
        print(f"  - 🔥 ERRORE CRITICO in sync_open_positions: {e}")
