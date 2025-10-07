# execution_service.py (MODALITÀ SIMULAZIONE - v1.1)
# ----------------------------------------------------------------
# Corregge il bug nella funzione get_market_price che impediva
# di leggere correttamente la risposta dell'API di Bybit.
# ----------------------------------------------------------------

from dotenv import load_dotenv
load_dotenv()

import os
import time
import traceback
from decimal import Decimal, ROUND_DOWN

import database
from api_clients.bybit_client import BybitClient

# --- CONFIGURAZIONE ---
MAX_SLIPPAGE_PERCENT = float(os.getenv("EXECUTION_MAX_SLIPPAGE", "0.005"))
RISK_PER_TRADE_USD = float(os.getenv("EXECUTION_RISK_USD", "10.0"))
SLEEP_INTERVAL = 10

class ExecutionService:
    def __init__(self):
        print("--- Avvio Servizio di Esecuzione (MODALITÀ SIMULAZIONE v1.1) ---")
        print("### NESSUN ORDINE REALE VERRÀ PIAZZATO ###")
        database.init_db()
        self.bybit_client = BybitClient()
        print("Servizio avviato. In attesa di nuovi intenti di trade da simulare...")

    def get_market_price(self, symbol):
        """Recupera il prezzo di mercato attuale per un simbolo."""
        try:
            tickers_response = self.bybit_client.session.get_tickers(category="linear", symbol=symbol)
            
            # --- CORREZIONE CHIAVE ---
            # Controlliamo che la risposta sia valida e navighiamo la struttura corretta:
            # la lista dei ticker si trova dentro la chiave 'result'.
            if (tickers_response and 
                tickers_response.get('retCode') == 0 and 
                'result' in tickers_response and 
                'list' in tickers_response['result'] and 
                tickers_response['result']['list']):
                
                last_price_str = tickers_response['result']['list'][0]['lastPrice']
                return float(last_price_str)
            else:
                print(f"  - ⚠️ Risposta non valida o vuota da get_tickers per {symbol}: {tickers_response.get('retMsg', 'N/A')}")
                return None
            # --- FINE CORREZIONE ---

        except Exception as e:
            print(f"  - 🔥 Errore durante la chiamata a get_tickers per {symbol}: {e}")
            return None

    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calcola la quantità (size) da acquistare/vendere basandosi sul rischio fisso."""
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit == 0:
            return 0.0
        
        size = RISK_PER_TRADE_USD / risk_per_unit
        
        if size > 10:
            return float(Decimal(size).quantize(Decimal('0.01'), rounding=ROUND_DOWN))
        else:
            return float(Decimal(size).quantize(Decimal('0.001'), rounding=ROUND_DOWN))

    def run(self):
        """Il ciclo principale del servizio."""
        while True:
            try:
                with database.session_scope() as session:
                    # Usiamo .with_for_update() per bloccare le righe e prevenire race conditions
                    # se avessimo più istanze di questo servizio (buona pratica).
                    new_intents = session.query(database.TradeIntent).filter_by(status='NEW').with_for_update().all()

                    if not new_intents:
                        time.sleep(SLEEP_INTERVAL)
                        continue

                    print(f"\n[{time.ctime()}] Trovati {len(new_intents)} nuovi intenti di trade da simulare.")

                    for intent in new_intents:
                        print(f"-> Valutazione intento #{intent.id}: {intent.symbol} {intent.direction}...")
                        
                        intent.status = 'PROCESSING'
                        session.commit()

                        market_price = self.get_market_price(intent.symbol)
                        if not market_price:
                            print(f"  - Riprovo al prossimo ciclo.")
                            intent.status = 'NEW' # Resetta per riprovare
                            session.commit()
                            continue

                        slippage = abs(market_price - intent.entry_price) / intent.entry_price
                        print(f"  - Prezzo segnale: {intent.entry_price}, Prezzo mercato: {market_price}, Slippage: {slippage:.2%}")

                        if slippage > MAX_SLIPPAGE_PERCENT:
                            print(f"  - ❌ Segnale SCADUTO. Slippage troppo alto. Proposta annullata.")
                            intent.status = 'CANCELED'
                            session.commit()
                            continue
                        
                        qty = self.calculate_position_size(market_price, intent.stop_loss)
                        if qty <= 0:
                            print(f"  - ❌ Quantità calcolata non valida ({qty}). Proposta annullata.")
                            intent.status = 'CANCELED'
                            session.commit()
                            continue
                        
                        print("\n" + "="*60)
                        print("  *** 📈 PROPOSTA DI TRADE (SIMULAZIONE) 📉 ***")
                        print("="*60)
                        print(f"  - Asset:     {intent.symbol}")
                        print(f"  - Direzione:   {intent.direction.upper()}")
                        print(f"  - Strategia:   {intent.strategy}")
                        print(f"  - Timeframe:   {intent.timeframe} min")
                        print("-" * 60)
                        print(f"  - Prezzo Entrata: {market_price:.5f}")
                        print(f"  - Quantità:       {qty}")
                        print(f"  - Take Profit:    {intent.take_profit:.5f}")
                        print(f"  - Stop Loss:      {intent.stop_loss:.5f}")
                        print("="*60 + "\n")
                        
                        intent.status = 'SIMULATED'
                        session.commit()

            except Exception as e:
                print(f"\n🔥 ERRORE FATALE nel servizio di esecuzione (simulazione): {e}")
                traceback.print_exc()
                time.sleep(30)

            time.sleep(SLEEP_INTERVAL)

if __name__ == '__main__':
    service = ExecutionService()
    service.run()
