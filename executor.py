# Gestisce: ordini stop, timeout, trailing, parziali
from risk_tools import calc_position_size

def execute_signal(exchange, signal, balance):
    symbol = signal['symbol']
    side = signal['signal_type']
    entry = signal['entry_price']
    sl = signal['stop_loss']
    tp = signal['take_profit']
    
    # mgmt è una stringa JSON, dobbiamo convertirla di nuovo in dizionario
    import json
    mgmt = json.loads(signal.get('mgmt_details', '{}'))

    # Calcolo posizione (valori di tick fittizi, da configurare)
    qty = calc_position_size(balance, 0.01, entry, sl, tick_value=0.1, tick_size=0.1)
    if qty == 0:
        print(f"Quantità calcolata è 0 per {symbol}, ordine non inviato.")
        return

    print(f"INVIO ORDINE per {symbol}: {side} {qty} @ {entry} (STOP)")
    
    # Esempio di invio ordine (logica da implementare con l'API dell'exchange)
    # if side == "LONG":
    #     exchange.create_order(symbol, 'stop_market', 'buy', qty, entry, {'stopPrice': entry})
    # else:
    #     exchange.create_order(symbol, 'stop_market', 'sell', qty, entry, {'stopPrice': entry})
    
    print("Logica di timeout e trailing da implementare.")