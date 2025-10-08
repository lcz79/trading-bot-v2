# app.py — Phoenix Dashboard v4.2.0 (Streamlit Native)
# ----------------------------------------------------------------
# - Rimosso il ciclo 'while True' per risolvere StreamlitDuplicateElementKey.
# - Integrata la libreria streamlit-autorefresh per aggiornamenti puliti.
# - Struttura del codice allineata alle best practice di Streamlit.
# ----------------------------------------------------------------

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import database
from sqlalchemy import desc
import time
import datetime
from api_clients.bybit_client import BybitClient

# --- Configurazione Pagina (eseguita una sola volta) ---
st.set_page_config(page_title="Phoenix Dashboard", page_icon="🔥", layout="wide")
database.init_db()

# --- Funzioni di Utilità ---
@st.cache_data(ttl=30)
def load_data():
    """Carica tutti i dati necessari dal database e dall'exchange."""
    print(f"[{time.ctime()}] Eseguo load_data...")
    total_equity = "N/A"
    
    try:
        client = BybitClient()
        balance_data = client.session.get_wallet_balance(accountType="UNIFIED")
        if balance_data and balance_data['retCode'] == 0:
            total_equity = float(balance_data['result']['list'][0]['totalEquity'])
    except Exception as e:
        print(f"🔥 ERRORE recupero saldo: {e}")

    with database.session_scope() as session:
        intents_q = session.query(database.TradeIntent).filter(
            database.TradeIntent.status.in_(['NEW', 'SIMULATED'])
        ).order_by(desc(database.TradeIntent.id)).statement # Ordina per ID per stabilità
        
        positions_q = session.query(database.OpenPosition).statement
        
        signals_df = pd.read_sql(intents_q, database.engine)
        positions_df = pd.read_sql(positions_q, database.engine)
        
        # Simula performance passate
        past_trades = pd.DataFrame()
        
        return signals_df, positions_df, past_trades, total_equity

# --- UI PRINCIPALE (verrà rieseguita da Streamlit) ---

# Attiva l'auto-refresh della pagina ogni 30 secondi
st_autorefresh(interval=30 * 1000, key="data_refresh")

st.title("🔥 Phoenix Trading System Dashboard")

signals, positions, past_trades, total_equity = load_data()

# 1. ANALISI PERFORMANCE
st.header("📈 Performance & Equity")
c1, c2, c3, c4 = st.columns(4)

equity_display = f"${total_equity:,.2f}" if isinstance(total_equity, float) else "Errore API"
c1.metric("Equity Totale Conto", equity_display)

if not past_trades.empty:
    total_pnl = past_trades['pnl'].sum()
    win_trades = past_trades[past_trades['pnl'] > 0]
    win_rate = (len(win_trades) / len(past_trades)) * 100 if not past_trades.empty else 0
    c2.metric("P&L Realizzato (Sim.)", f"${total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")
    c3.metric("Win Rate (Sim.)", f"{win_rate:.1f}%")
else:
    c2.metric("P&L Realizzato (Sim.)", "N/A")
    c3.metric("Win Rate (Sim.)", "N/A")

c4.metric("Posizioni Aperte", f"{len(positions)}")

# 2. SEGNALI OPERATIVI
st.header("🎯 Segnali Operativi in Attesa")
if not signals.empty:
    # Aggiungiamo un ulteriore controllo per sicurezza, anche se l'ID dovrebbe essere unico
    signals = signals.drop_duplicates(subset=['id'], keep='first')
    
    for index, signal in signals.iterrows():
        color = "green" if signal.direction == "Long" else "red"
        # Usiamo una combinazione di ID e timestamp per una chiave ancora più robusta
        unique_key_prefix = f"{signal.id}_{int(pd.Timestamp(signal.timestamp).timestamp())}"

        st.subheader(f":{color}[{signal.direction.upper()}] - {signal.symbol} (Score: {signal.score})")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Prezzo di Entrata", f"{signal.entry_price:.4f}")
        c2.metric("Take Profit", f"{signal.take_profit:.4f}")
        c3.metric("Stop Loss", f"{signal.stop_loss:.4f}")
        
        with st.expander("Calcolatore Rischio/Rendimento"):
            leverage = st.slider("Leva", 1, 50, 10, key=f"lev_{unique_key_prefix}")
            investment = st.number_input("Importo Investimento ($)", min_value=10.0, value=100.0, step=10.0, key=f"inv_{unique_key_prefix}")
            
            position_size = (investment * leverage) / signal.entry_price
            potential_profit = (signal.take_profit - signal.entry_price) * position_size if signal.direction == "Long" else (signal.entry_price - signal.take_profit) * position_size
            potential_loss = (signal.entry_price - signal.stop_loss) * position_size if signal.direction == "Long" else (signal.stop_loss - signal.entry_price) * position_size
            
            c_calc1, c_calc2 = st.columns(2)
            c_calc1.success(f"Potenziale Guadagno: ${potential_profit:.2f}")
            c_calc2.error(f"Potenziale Perdita: ${potential_loss:.2f}")
        st.divider()
else:
    st.info("Nessun nuovo segnale operativo. In attesa del prossimo ciclo di analisi.")

# 3. TIMER (logica semplificata)
st.sidebar.header("⚙️ Stato del Sistema")
st.sidebar.info(f"Pagina aggiornata: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.sidebar.info("L'aggiornamento automatico è attivo (ogni 30 secondi).")
