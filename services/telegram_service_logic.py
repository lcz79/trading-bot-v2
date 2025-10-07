import requests
import os
from database import session_scope, TechnicalSignal
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token o Chat ID Telegram mancanti.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("Messaggio Telegram inviato.")
        else:
            print(f"Errore Telegram: {response.text}")
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def process_new_signals_for_telegram():
    since = datetime.utcnow() - timedelta(minutes=5)
    with session_scope() as session:
        new_signals = session.query(TechnicalSignal).filter(
            TechnicalSignal.created_at >= since,
            TechnicalSignal.signal.like('%STRONG%')
        ).all()
        for signal in new_signals:
            message = f"""
🚨 Nuovo Segnale STRONG 🚨
- Asset: {signal.asset}
- Segnale: {signal.signal}
- Prezzo: {signal.entry_price}
- SL: {signal.stop_loss}
- TP: {signal.take_profit}
- Strategia: {signal.strategy} ({signal.timeframe})
"""
            send_telegram_message(message)