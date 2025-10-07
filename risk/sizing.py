"""
Modulo per il calcolo della dimensione della posizione (Position Sizing).
"""

def percent_risk_size(
    equity: float,
    stop_loss_price: float,
    entry_price: float,
    risk_pct: float,
    min_trade_size: float = 0.001,
    leverage: int = 1
) -> float:
    """
    Calcola la dimensione della posizione usando il metodo "Fixed Fractional".
    
    Args:
        equity (float): Il capitale totale dell'account.
        stop_loss_price (float): Il prezzo a cui lo stop loss verrà piazzato.
        entry_price (float): Il prezzo di ingresso previsto.
        risk_pct (float): La percentuale di capitale da rischiare (es. 0.02 per il 2%).
        min_trade_size (float): La dimensione minima tradabile per l'asset (es. 0.001 per BTC).
        leverage (int): La leva utilizzata (default è 1, no leva).
    
    Returns:
        float: La quantità di asset da acquistare/vendere (es. 0.05 BTC).
               Restituisce 0 se il rischio è nullo o i parametri non sono validi.
    """
    if equity <= 0 or risk_pct <= 0:
        return 0.0

    # 1. Calcola l'importo monetario da rischiare
    risk_amount_per_trade = equity * risk_pct
    
    # 2. Calcola il rischio per unità di asset
    risk_per_unit = abs(entry_price - stop_loss_price)
    
    if risk_per_unit == 0:
        return 0.0 # Evita divisione per zero
        
    # 3. Calcola la dimensione della posizione
    # La leva non influisce sul CALCOLO DEL RISCHIO, ma sul capitale richiesto (margine).
    # La size è determinata solo dal rischio che siamo disposti a correre.
    position_size = risk_amount_per_trade / risk_per_unit
    
    # 4. Arrotonda alla dimensione minima tradabile per l'exchange
    if position_size < min_trade_size:
        return 0.0 # La size calcolata è troppo piccola per essere eseguita
        
    # Esempio di arrotondamento (può essere più complesso in base alle regole dell'exchange)
    # Per ora, restituiamo un valore con un numero ragionevole di decimali
    return round(position_size, 8)
