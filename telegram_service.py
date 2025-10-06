import os
import time
import requests
import schedule
from dotenv import load_dotenv
import database
import pandas as pd

# --- CONFIGURAZIONE ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- STATO GLOBALE ---
sent_signals_cache = set()

def escape_markdown_v2(text: str) -> str:
    """Prepara il testo per la modalità MarkdownV2 di Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{char}' if char in escape_chars else char for char in str(text))

def send_telegram_message(message):
    """Invia un messaggio formattato in MarkdownV2 a Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRORE: Credenziali Telegram non trovate in .env")
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'MarkdownV2'}
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"ERRORE: Impossibile inviare il messaggio. Status: {response.status_code}, Risposta: {response.text}")
            return
        print(f"-> Messaggio formattato con emoji inviato a Telegram: {message.splitlines()[0]}")
    except requests.exceptions.RequestException as e:
        print(f"ERRORE di rete nell'invio a Telegram: {e}")

def check_and_send_signals():
    """Controlla il database per nuovi segnali e li invia con segnali visivi."""
    global sent_signals_cache
    session = database.get_db_session()
    try:
        signals_df = pd.read_sql_query("SELECT * FROM technical_signals", database.engine)
        current_signal_ids = set()
        
        for _, row in signals_df.iterrows():
            signal_id = f"{row['asset']}-{row['timeframe']}-{row['strategy']}-{row['signal']}"
            current_signal_ids.add(signal_id)
            
            if signal_id not in sent_signals_cache:
                # --- NUOVA LOGICA PER GLI EMOJI ---
                signal_text = row['signal']
                if 'LONG' in signal_text.upper():
                    signal_emoji = "🟢"
                    signal_title = "Nuovo Segnale LONG"
                elif 'SHORT' in signal_text.upper():
                    signal_emoji = "🔴"
                    signal_title = "Nuovo Segnale SHORT"
                else:
                    signal_emoji = "⚪️"
                    signal_title = "Nuovo Segnale NEUTRO"
                # --- FINE NUOVA LOGICA ---

                asset = escape_markdown_v2(row['asset'])
                timeframe = escape_markdown_v2(row['timeframe'])
                signal = escape_markdown_v2(signal_text)
                price = escape_markdown_v2(row['price'])
                stop_loss = escape_markdown_v2(row['stop_loss'])
                take_profit = escape_markdown_v2(row['take_profit'])
                strategy = escape_markdown_v2(row['strategy'])
                
                message = (
                    f"{signal_emoji} *{escape_markdown_v2(signal_title)}* {signal_emoji}\n\n"
                    f"*Asset:* `{asset}`\n"
                    f"*Timeframe:* {timeframe}\n"
                    f"*Segnale:* *{signal}*\n\n"
                    f"*Prezzo di Ingresso:* `{price}`\n"
                    f"*Stop Loss:* `{stop_loss}`\n"
                    f"*Take Profit:* `{take_profit}`\n\n"
                    f"Strategia: _{strategy}_"
                )
                send_telegram_message(message)
                sent_signals_cache.add(signal_id)
        
        sent_signals_cache = sent_signals_cache.intersection(current_signal_ids)

    finally:
        session.close()

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRORE FATALE: Le credenziali di Telegram non sono impostate. Il servizio non può partire.")
    else:
        print("--- Avvio Servizio Notifiche Telegram (v1.3 - Con Segnali Visivi) ---")
        print("Controllo nuovi segnali ogni minuto...")
        
        # Resettiamo la cache per inviare i segnali con il nuovo formato emoji
        sent_signals_cache.clear()
        print("Cache dei segnali inviati resettata per un nuovo invio con emoji.")
        
        check_and_send_signals()
        
        schedule.every(1).minute.do(check_and_send_signals)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
