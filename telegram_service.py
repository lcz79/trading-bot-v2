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
    """
    Prepara il testo per la modalità MarkdownV2 di Telegram,
    eseguendo l'escape dei caratteri speciali.
    """
    # Lista di caratteri che Telegram richiede di 'escapare'
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    # Applica l'escape aggiungendo un '\' prima di ogni carattere speciale
    return "".join(f'\\{char}' if char in escape_chars else char for char in str(text))

def send_telegram_message(message):
    """
    Invia un messaggio formattato in MarkdownV2 a Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRORE: Credenziali Telegram non trovate in .env")
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2' # Riattiviamo la formattazione!
    }
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"ERRORE: Impossibile inviare il messaggio. Status: {response.status_code}, Risposta: {response.text}")
            return
        print(f"-> Messaggio formattato inviato a Telegram: {message.splitlines()[0]}")
    except requests.exceptions.RequestException as e:
        print(f"ERRORE di rete nell'invio a Telegram: {e}")

def check_and_send_signals():
    """
    Controlla il database per nuovi segnali e li invia in formato professionale.
    """
    global sent_signals_cache
    session = database.get_db_session()
    try:
        signals_df = pd.read_sql_query("SELECT * FROM technical_signals", database.engine)
        current_signal_ids = set()
        
        for _, row in signals_df.iterrows():
            signal_id = f"{row['asset']}-{row['timeframe']}-{row['strategy']}-{row['signal']}"
            current_signal_ids.add(signal_id)
            
            if signal_id not in sent_signals_cache:
                # Applica l'escape a ogni variabile prima di costruire il messaggio
                asset = escape_markdown_v2(row['asset'])
                timeframe = escape_markdown_v2(row['timeframe'])
                signal = escape_markdown_v2(row['signal'])
                price = escape_markdown_v2(row['price'])
                stop_loss = escape_markdown_v2(row['stop_loss'])
                take_profit = escape_markdown_v2(row['take_profit'])
                strategy = escape_markdown_v2(row['strategy'])
                
                # Messaggio ben formattato con MarkdownV2
                message = (
                    f"🚨 *Nuovo Segnale Trovato* 🚨\n\n"
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
        print("--- Avvio Servizio Notifiche Telegram (v1.2 - Formattazione Robusta) ---")
        print("Controllo nuovi segnali ogni minuto...")
        
        # Resettiamo la cache per inviare di nuovo i segnali nel nuovo formato
        sent_signals_cache.clear()
        print("Cache dei segnali inviati resettata per un nuovo invio formattato.")
        
        check_and_send_signals()
        
        schedule.every(1).minute.do(check_and_send_signals)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
