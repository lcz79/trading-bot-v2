# --- PRIMISSIMA COSA DA FARE: CARICARE LE VARIABILI D'AMBIENTE ---
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------

import os
import time
import schedule
import requests
from datetime import datetime, timedelta, timezone

import database

# --- CONFIGURAZIONE ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

notified_signal_ids = set()

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRORE: Token o Chat ID di Telegram non impostati nel file .env")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"-> Messaggio Telegram inviato con successo.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERRORE durante l'invio del messaggio Telegram: {e}")
        return False

def check_and_notify():
    print(f"\n[{time.ctime()}] -> Controllo nuovi segnali...")
    
    try:
        with database.session_scope() as session:
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=35)
            
            new_signals = (
                session.query(database.TechnicalSignal)
                .filter(database.TechnicalSignal.created_at > time_threshold)
                .order_by(database.TechnicalSignal.created_at.asc())
                .all()
            )

            if not new_signals:
                print("-> Nessun nuovo segnale trovato.")
                return

            for signal in new_signals:
                if signal.id in notified_signal_ids:
                    continue

                entry_price = float(signal.entry_price)
                stop_loss = float(signal.stop_loss) if signal.stop_loss else 'N/A'
                take_profit = float(signal.take_profit) if signal.take_profit else 'N/A'

                message = (
                    f"🚨 *NUOVO SEGNALE DI TRADING* 🚨\n\n"
                    f"*Asset:* `{signal.asset}`\n"
                    f"*Timeframe:* `{signal.timeframe}`\n"
                    f"*Strategia:* `{signal.strategy}`\n"
                    f"*Segnale:* *{signal.signal}*\n\n"
                    f"--- *Piano di Trading* ---\n"
                    f"*Prezzo di Entrata:* `{entry_price:.4f}`\n"
                    f"*Stop Loss (SL):* `{stop_loss:.4f if isinstance(stop_loss, float) else stop_loss}`\n"
                    f"*Take Profit (TP):* `{take_profit:.4f if isinstance(take_profit, float) else take_profit}`\n"
                )
                
                print(f"-> Trovato nuovo segnale non notificato: {signal.asset} {signal.signal}")
                if send_telegram_message(message):
                    notified_signal_ids.add(signal.id)

    except Exception as e:
        print(f"ERRORE FATALE durante il controllo dei segnali: {e}")


if __name__ == '__main__':
    database.init_db()

    schedule.every(1).minute.do(check_and_notify)
    
    print("\n--- Avvio Servizio Telegram (v7.1 - Env Fix) ---")
    print("Servizio avviato. Controllo nuovi segnali ogni minuto.")
    print("Questo terminale deve rimanere aperto.")

    check_and_notify()

    while True:
        schedule.run_pending()
        time.sleep(1)
