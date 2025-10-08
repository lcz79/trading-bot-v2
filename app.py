# app.py — Phoenix Command Center v6.0 (Fusion FINAL)
# Integra la Telemetria Live (v5.0) con la Visualizzazione Dettagliata dei Segnali (v4.0).

import streamlit as st
import pandas as pd
import database
from sqlalchemy import desc
import datetime
import ast

# Importiamo il client Bybit
try:
    from api_clients.bybit_client import BybitClient
except ImportError:
    BybitClient = None

st.set_page_config(page_title="Phoenix Command Center", page_icon="🔥", layout="wide")
database.init_db()

# Funzione per caricare i dati dal DB locale
@st.cache_data(ttl=30)
def load_db_data():
    with database.session_scope() as session:
        signals_q = session.query(database.TechnicalSignal).order_by(desc(database.TechnicalSignal.id)).statement
        signals_df = pd.read_sql(signals_q, database.engine, parse_dates=['created_at'])
        return signals_df

# Funzione per caricare i dati LIVE da Bybit
@st.cache_data(ttl=15)
def load_live_data():
    if not BybitClient: return 0, []
    client = BybitClient()
    balance_data = client.get_wallet_balance()
    positions_data = client.get_positions()
    
    total_equity = 0
    if balance_data and balance_data.get('retCode') == 0:
        try:
            total_equity = float(balance_data['result']['list'][0]['totalEquity'])
        except (IndexError, KeyError):
             total_equity = 0 # Gestisce il caso di wallet vuoto
        
    positions_list = []
    if positions_data and positions_data.get('retCode') == 0:
        positions_list = positions_data['result']['list']
        
    return total_equity, positions_list

# --- UI PRINCIPALE ---
st.title("🔥 Phoenix Command Center v6.0")

if st.button("🔄 Aggiorna Dati"):
    st.cache_data.clear()

signals_df = load_db_data()
total_equity_usd, live_positions = load_live_data()

# ===== SEZIONE EQUITY E POSIZIONI LIVE =====
st.header("🛰️ Telemetria Live dal Conto Bybit")

c1, c2, c3 = st.columns(3)
c1.metric("Equity Totale Conto (USD)", f"${total_equity_usd:,.2f}")

if live_positions:
    pos_df = pd.DataFrame(live_positions)
    pos_df['size'] = pd.to_numeric(pos_df['size'], errors='coerce')
    open_positions_df = pos_df[pos_df['size'] > 0].copy()

    if not open_positions_df.empty:
        open_positions_df['unrealisedPnl'] = pd.to_numeric(open_positions_df['unrealisedPnl'], errors='coerce').fillna(0)
        total_unrealised_pnl = open_positions_df['unrealisedPnl'].sum()
        
        c2.metric("Posizioni Aperte", len(open_positions_df))
        c3.metric("P&L Fluttuante", f"${total_unrealised_pnl:,.2f}", delta=f"{total_unrealised_pnl:,.2f}")
        
        st.subheader("Dettaglio Posizioni Aperte")
        display_cols = ['symbol', 'side', 'size', 'avgPrice', 'unrealisedPnl', 'leverage', 'liqPrice']
        st.dataframe(open_positions_df[display_cols].rename(columns={
            'symbol': 'Simbolo', 'side': 'Direzione', 'size': 'Quantità', 
            'avgPrice': 'Prezzo Medio Ingresso', 'unrealisedPnl': 'P&L non realizzato',
            'leverage': 'Leva', 'liqPrice': 'Prezzo Liquidazione'
        }))
    else:
        c2.metric("Posizioni Aperte", 0); c3.metric("P&L Fluttuante", "$0.00")
        st.info("Nessuna posizione attualmente aperta sull'exchange.")
else:
    c2.metric("Posizioni Aperte", "N/A"); c3.metric("P&L Fluttuante", "N/A")
    st.warning("Impossibile recuperare i dati da Bybit. Controlla le chiavi API o la connessione.")

# ===== SEZIONE SEGNALI DAL BOT (CODICE COMPLETO E CORRETTO) =====
st.header("🎯 Segnali Generati dal Bot")

if not signals_df.empty:
    for index, signal in signals_df.iterrows():
        try: details = ast.literal_eval(signal.details)
        except: details = {}
            
        coherence = details.get('coherence', 'N/A')
        final_score = details.get('final_score', 0)
        direction = "Long" if "LONG" in signal.signal.upper() else "Short"
        color = "green" if direction == "Long" else "red"
        unique_key_prefix = f"sig_{signal.id}"
        
        st.subheader(f":{color}[{signal.signal.upper()}] - {signal.asset}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Timeframe Segnale", signal.timeframe.upper())
        c2.metric("Coerenza", str(coherence))
        c3.metric("Score Finale", f"{final_score}")
        
        c_prices1, c_prices2, c_prices3 = st.columns(3)
        entry_price = float(signal.entry_price)
        take_profit = float(signal.take_profit) if signal.take_profit else 0
        stop_loss = float(signal.stop_loss) if signal.stop_loss else 0
        
        c_prices1.metric("Prezzo Entrata", f"{entry_price:.4f}")
        c_prices2.metric("Take Profit", f"{take_profit:.4f}")
        c_prices3.metric("Stop Loss", f"{stop_loss:.4f}")
        
        with st.expander("Calcolatore Rischio/Rendimento"):
            leverage = st.slider("Leva", 1, 50, 10, key=f"lev_{unique_key_prefix}")
            investment = st.number_input("Importo Investimento ($)", min_value=10.0, value=100.0, step=10.0, key=f"inv_{unique_key_prefix}")
            
            position_size = (investment * leverage) / entry_price
            potential_profit = (take_profit - entry_price) * position_size if direction == "Long" else (entry_price - take_profit) * position_size
            potential_loss = (entry_price - stop_loss) * position_size if direction == "Long" else (stop_loss - entry_price) * position_size
            
            c_calc1, c_calc2 = st.columns(2)
            c_calc1.success(f"Potenziale Guadagno: ${potential_profit:.2f}")
            c_calc2.error(f"Potenziale Perdita: ${potential_loss:.2f}")
            
        st.divider()
else:
    st.info("Nessun nuovo segnale generato dal bot. Esegui il runner per cercare opportunità.")
