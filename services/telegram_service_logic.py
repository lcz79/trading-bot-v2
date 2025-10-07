import requests
import os
import pandas_ta as ta
from database import session_scope, TechnicalSignal, OpenPosition
from api_clients import financial_data_client
from datetime import datetime, timezone

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def _format_price(price, asset):
    """Formatta il prezzo con un numero appropriato di decimali."""
    if price is None: return "N/A"
    price_val = float(price)
    if "USDT" in asset or "USD" in asset:
        if price_val > 10: return f"{price_val:,.2f}"
        elif price_val > 0.01: return f"{price_val:,.4f}"
        else: return f"{price_val:,.8f}"
    else: return f"{price_val:,.2f}"

def send_telegram_message(message):
    """Invia un messaggio a Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token o Chat ID Telegram mancanti.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("-> Messaggio Telegram inviato con successo.")
            return True
        else:
            print(f"-> Errore Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"-> Errore invio Telegram: {e}")
        return False

def process_new_signals_for_telegram():
    """Cerca nuovi segnali, li notifica e li marca come inviati."""
    with session_scope() as session:
        signals_to_notify = session.query(TechnicalSignal).filter(
            TechnicalSignal.signal.like('%STRONG%'),
            TechnicalSignal.notified_at == None
        ).order_by(TechnicalSignal.created_at).all()

        if not signals_to_notify:
            print("-> Nessun nuovo segnale da notificare.")
            return

        print(f"-> Trovati {len(signals_to_notify)} nuovi segnali da notificare...")
        for signal in signals_to_notify:
            entry_price_f = _format_price(signal.entry_price, signal.asset)
            stop_loss_f = _format_price(signal.stop_loss, signal.asset)
            take_profit_f = _format_price(signal.take_profit, signal.asset)
            icon = "🟢" if "LONG" in signal.signal else "🔴"
            message = (
                f"{icon} *Nuovo Segnale STRONG* {icon}\n\n"
                f"*Asset:* `{signal.asset}`\n"
                f"*Segnale:* `{signal.signal}`\n"
                f"*Prezzo:* `{entry_price_f}`\n"
                f"*Stop Loss:* `{stop_loss_f}`\n"
                f"*Take Profit:* `{take_profit_f}`\n"
                f"*Strategia:* `{signal.strategy} ({signal.timeframe})`"
            )
            if send_telegram_message(message):
                signal.notified_at = datetime.now(timezone.utc)
                session.add(signal)

def process_position_management_suggestions():
    """Analizza le posizioni aperte e suggerisce aggiustamenti per lo Stop Loss."""
    print("-> Avvio analisi per gestione posizioni...")
    with session_scope() as session:
        open_positions = session.query(OpenPosition).all()
        if not open_positions:
            print("-> Nessuna posizione aperta da analizzare.")
            return

        for pos in open_positions:
            df = financial_data_client.get_data(pos.symbol, "15", 50, "Bybit-linear")
            if df is None or df.empty:
                continue

            # Calcoliamo un Trailing Stop basato sull'ATR (Average True Range)
            df.ta.atr(length=14, append=True)
            atr_col = next((col for col in df.columns if col.startswith('ATRr_')), None)
            if not atr_col or pd.isna(df[atr_col].iloc[-1]):
                continue

            last_close = float(df['close'].iloc[-1])
            last_atr = float(df[atr_col].iloc[-1])
            
            current_sl_db_record = session.query(TechnicalSignal).filter(
                TechnicalSignal.asset == pos.symbol
            ).order_by(TechnicalSignal.created_at.desc()).first()

            if not current_sl_db_record or not current_sl_db_record.stop_loss:
                continue

            current_sl = float(current_sl_db_record.stop_loss)
            new_suggested_sl = 0

            if pos.position_side.upper() == 'LONG' and last_close > pos.entry_price:
                # Per posizioni LONG in profitto, il nuovo SL è sotto il prezzo attuale
                # di una distanza pari a 2.5 volte l'ATR
                new_suggested_sl = last_close - (last_atr * 2.5)
                # Suggeriamo di spostare lo SL solo se il nuovo è più alto del vecchio
                if new_suggested_sl > current_sl:
                    pnl_percent = (last_close - pos.entry_price) / pos.entry_price * 100
                    message = (
                        f"📈 *Gestione Posizione LONG*\n\n"
                        f"*Asset:* `{pos.symbol}`\n"
                        f"*Profitto Attuale:* `+{pnl_percent:.2f}%`\n"
                        f"Il prezzo si è mosso a favore. Si consiglia di alzare lo Stop Loss per proteggere i profitti.\n\n"
                        f"*SL Attuale:* `{_format_price(current_sl, pos.symbol)}`\n"
                        f"*Nuovo SL Suggerito:* `{_format_price(new_suggested_sl, pos.symbol)}`"
                    )
                    if send_telegram_message(message):
                        # Aggiorniamo lo SL nel DB per non inviare più la stessa notifica
                        current_sl_db_record.stop_loss = new_suggested_sl
                        session.add(current_sl_db_record)

            elif pos.position_side.upper() == 'SHORT' and last_close < pos.entry_price:
                # Per posizioni SHORT in profitto, il nuovo SL è sopra il prezzo attuale
                new_suggested_sl = last_close + (last_atr * 2.5)
                # Suggeriamo di spostare lo SL solo se il nuovo è più basso del vecchio
                if new_suggested_sl < current_sl:
                    pnl_percent = (pos.entry_price - last_close) / pos.entry_price * 100
                    message = (
                        f"📉 *Gestione Posizione SHORT*\n\n"
                        f"*Asset:* `{pos.symbol}`\n"
                        f"*Profitto Attuale:* `+{pnl_percent:.2f}%`\n"
                        f"Il prezzo si è mosso a favore. Si consiglia di abbassare lo Stop Loss per proteggere i profitti.\n\n"
                        f"*SL Attuale:* `{_format_price(current_sl, pos.symbol)}`\n"
                        f"*Nuovo SL Suggerito:* `{_format_price(new_suggested_sl, pos.symbol)}`"
                    )
                    if send_telegram_message(message):
                        current_sl_db_record.stop_loss = new_suggested_sl
                        session.add(current_sl_db_record)
