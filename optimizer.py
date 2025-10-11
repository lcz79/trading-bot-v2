# optimizer.py (v2.0 - "Genetic Portfolio" Edition)
import pandas as pd
import itertools
from tqdm import tqdm
import numpy as np

from backtest_engine import run_single_backtest
import config

# --- GRIGLIA DI PARAMETRI DA TESTARE ---
param_grid = {
    'k_atr': [0.8, 1.0, 1.2, 1.5, 1.8],
    'rsi_len': [12, 14, 16],
    'adx_threshold': [25, 28, 30, 32]
}
# -----------------------------------------

def run_full_optimization():
    print("--- 🧬 AVVIO LABORATORIO GENETICO: Creazione del Portfolio Ottimizzato 🧬 ---")
    
    keys, values = zip(*param_grid.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    optimized_params_portfolio = {}

    for asset in config.ASSET_UNIVERSE:
        print(f"\n--- Analizzando il DNA di {asset}... ---")
        
        results = []
        
        for params in tqdm(param_combinations, desc=f"Ottimizzazione {asset}", unit="combo"):
            vwap_params = {
                'k_atr': params['k_atr'],
                'rsi_len': params['rsi_len'],
                'adx_len': 14,
                'adx_threshold': params['adx_threshold']
            }
            
            result = run_single_backtest(
                asset=asset,
                start_date_str=config.BACKTEST_START_DATE,
                end_date_str=config.BACKTEST_END_DATE,
                vwap_params=vwap_params
            )
            
            if result:
                result.update(params)
                results.append(result)

        if not results:
            print(f"Nessun risultato valido per {asset}.")
            continue

        results_df = pd.DataFrame(results)
        
        viable_results = results_df[(results_df['trades'] >= 5) & (results_df['profit_factor'] > 1.2)]
        
        if viable_results.empty:
            print(f"Nessuna combinazione di parametri profittevole trovata per {asset}.")
            continue
            
        best_dna = viable_results.sort_values(by=['profit_factor', 'pnl'], ascending=False).iloc[0]
        
        print(f"✅ DNA Ottimale per {asset} trovato! PNL: ${best_dna['pnl']}, PF: {best_dna['profit_factor']}, Trades: {best_dna['trades']}")
        
        optimized_params_portfolio[asset] = {
            'k_atr': best_dna['k_atr'],
            'rsi_len': int(best_dna['rsi_len']),
            'adx_threshold': int(best_dna['adx_threshold'])
        }

    print("\n\n" + "="*60)
    print("--- 🧬 PORTFOLIO GENETICO COMPLETATO 🧬 ---")
    print("Copia e incolla il seguente blocco nel tuo file 'config.py':")
    
    config_string = "OPTIMIZED_PARAMS = {\n"
    for asset, params in optimized_params_portfolio.items():
        # Clean np.float64 for clean output
        cleaned_params = {k: (v if not isinstance(v, np.float64) else round(v, 4)) for k, v in params.items()}
        config_string += f'    "{asset}": {cleaned_params},\n'
    config_string += "}"
    
    print("\n" + config_string + "\n")
    print("="*60)

if __name__ == "__main__":
    run_full_optimization()
