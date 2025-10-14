import logging
import json
from analysis import market_analysis # Importa il modulo corretto

def run_daily_scanner(asset_universe, data_provider):
    logging.info("🔍 Avvio scanner multi-asset giornaliero")
    with open('optimal_strategies.json', 'r') as f:
        settings = json.load(f)

    best_setups = []
    # data_provider è un dizionario: { "BTCUSDT": df_btc, "ETHUSDT": df_eth }
    for symbol, data in data_provider.items():
        params = settings['defaults'].copy()
        
        # Applica override per asset class
        # (Questa logica può essere migliorata, per ora è un esempio)
        asset_class = "crypto" # Default
        if any(x in symbol for x in ['USD', 'EUR', 'GBP', 'JPY']): asset_class = "forex"
        if any(x in symbol for x in ['NAS', 'SPX', 'DAX']): asset_class = "indices"
        if any(x in symbol for x in ['XAU', 'OIL', 'WTI']): asset_class = "commod"
        
        params.update(settings.get(asset_class, {}))
        
        # Applica override specifico per simbolo
        if symbol in settings.get('overrides', {}):
            params.update(settings['overrides'][symbol])

        # Esegui l'analisi che ora restituisce il segnale
        signal = market_analysis.run_pullback_analysis(symbol, data, params)
        if signal:
            best_setups.append(signal)

    logging.info(f"Scanner completato: trovati {len(best_setups)} setup.")
    return best_setups