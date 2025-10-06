# --- PRIMISSIMA COSA DA FARE: CARICARE LE VARIABILI D'AMBIENTE ---
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import database

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- FUNZIONI DI STILE E COUNTDOWN ---

def style_signals_table(df):
    def highlight_signal(row):
        signal_text = str(row.get('signal', '')).upper()
        color = ''
        if 'LONG' in signal_text:
            color = 'background-color: rgba(46, 139, 87, 0.3);'
        elif 'SHORT' in signal_text:
            color = 'background-color: rgba(139, 0, 0, 0.2);'
        return [color] * len(row)
    return df.style.apply(highlight_signal, axis=1)

def get_countdown_to_next_interval(interval_minutes):
    now = datetime.now()
    minutes_past_hour = now.minute
    intervals_past = minutes_past_hour // interval_minutes
    next_run_minute = (intervals_past + 1) * interval_minutes
    
    if next_run_minute >= 60:
        next_run_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_run_time = now.replace(minute=next_run_minute, second=0, microsecond=0)

    delta = next_run_time - now
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    return f"tra {minutes} min e {seconds} sec"

# --- FUNZIONI DI CARICAMENTO DATI ---
@st.cache_data(ttl=60)
def load_data():
    # Usiamo il nuovo session_scope anche per la lettura per coerenza
    with database.session_scope() as session:
        performance_df = pd.read_sql("SELECT * FROM performance_log ORDER BY timestamp DESC LIMIT 100", session.bind)
        signals_df = pd.read_sql("SELECT * FROM technical_signals ORDER BY created_at DESC", session.bind)
        quality_df = pd.read_sql("SELECT * FROM quality_scores ORDER BY quality_score DESC", session.bind)
        positions_df = pd.read_sql("SELECT * FROM open_positions", session.bind)
    return performance_df, signals_df, quality_df, positions_df

# --- TITOLO E HEADER ---
st.title("📈 Trading Bot Dashboard v3.4 (Env Fix)")
st.markdown(f"Ultimo aggiornamento della dashboard: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")

# --- PANNELLO DI STATO DEI SERVIZI ---
# ... (il resto del file rimane identico) ...
st.subheader("Stato dei Servizi")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Stato Exchange Service", value="ATTIVO ✅")
    countdown_exchange_placeholder = st.empty()
with col2:
    st.metric(label="Stato ETL Service (Analisi)", value="ATTIVO ✅")
    countdown_etl_placeholder = st.empty()

# --- CARICAMENTO DATI INIZIALE ---
performance_df, signals_df, quality_df, positions_df = load_data()

# --- DASHBOARD PRINCIPALE ---
st.header("Performance Finanziaria")
if not performance_df.empty:
    latest_perf = performance_df.iloc[0]
    equity = float(latest_perf['total_equity'])
    pnl = float(latest_perf['unrealized_pnl'])
    c1, c2 = st.columns(2)
    c1.metric("Total Equity (USDT)", f"${equity:,.2f}")
    c2.metric("Unrealized P&L (USDT)", f"${pnl:,.2f}", delta_color=("inverse" if pnl < 0 else "normal"))
    st.line_chart(performance_df.rename(columns={'timestamp':'index'}).set_index('index')['total_equity'])
else:
    st.warning("Nessun dato di performance trovato.")

st.header("Posizioni Aperte")
if not positions_df.empty:
    st.dataframe(positions_df, use_container_width=True)
else:
    st.info("Nessuna posizione aperta al momento.")

st.header("Segnali di Mercato Recenti")
if not signals_df.empty:
    st.dataframe(style_signals_table(signals_df), use_container_width=True)
else:
    st.info("Nessun segnale tecnico generato nell'ultimo ciclo.")

st.header("Asset Quality Score")
if not quality_df.empty:
    st.dataframe(quality_df, use_container_width=True)
else:
    st.warning("Nessun dato di quality score trovato.")

# --- LOOP DI AGGIORNAMENTO COUNTDOWN ---
while True:
    countdown_exchange_placeholder.markdown(f"**Prossimo aggiornamento Saldo/Posizioni:** {get_countdown_to_next_interval(15)}")
    countdown_etl_placeholder.markdown(f"**Prossimo Scan di Mercato:** {get_countdown_to_next_interval(30)}")
    time.sleep(1)
