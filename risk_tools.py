def calc_position_size(balance, risk_frac, entry, stop, tick_value, tick_size):
    risk_money = balance * risk_frac
    risk_per_unit = abs(entry - stop)
    if tick_size == 0: return 0 # Evita divisione per zero
    ticks = max(1, round(risk_per_unit / tick_size))
    loss_per_unit = ticks * tick_value
    if loss_per_unit == 0: return 0 # Evita divisione per zero
    qty = max(0, int(risk_money / loss_per_unit))
    return qty