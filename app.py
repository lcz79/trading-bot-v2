import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import database

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- FUNZIONI DI STILE E COUNTDOWN ---

def style_signals_table(df):
    """Applica la colorazione verde/rosso alla tabella dei segnali."""
    def highlight_signal(row):
        signal_text = str(row.get('signal', '')).upper()
        color = ''
        if 'LONG' in signal_text:
            color = 'background-color: rgba(46, 139, 87, 0.3);'  # Verde
        elif 'SHORT' in signal_text:
            color = 'background-color: rgba(139, 0, 0, 0.2);'   # Rosso
        return [color] * len(row)
    return df.style.apply(highlight_signal, axis=1)

def get_countdown_to_next_interval(interval_minutes):
    """
    Calcola il tempo rimanente al prossimo intervallo di X minuti.
    Esempio: se sono le 10:07 e l'intervallo è 15, la prossima esecuzione è alle 10:15.
    """
    now = datetime.now()
    # Calcola quanti minuti sono passati dall'inizio dell'ora
    minutes_past_hour = now.minute
    # Calcola il numero di intervalli passati
    intervals_past = minutes_past_hour // interval_minutes
    # Calcola il minuto della prossima esecuzione
    next_run_minute = (intervals_past + 1) * interval_minutes
    
    # Gestisce il caso in cui la prossima esecuzione è nell'ora successiva
    if next_run_minute >= 60:
        next_run_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_run_time = now.replace(minute=next_run_minute, second=0, microsecond=0)

    delta = next_run_time - now
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    return f"tra {minutes} min e {seconds} sec"

# --- FUNZIONI DI CARICAMENTO DATI ---
@st.cache_data(ttl=60) # Cache dei dati per 60 secondi
def load_data():
    conn = database.engine.connect()
    try:
        performance_df = pd.read_sql("SELECT * FROM performance_log ORDER BY timestamp DESC LIMIT 100", conn)
        signals_df = pd.read_sql("SELECT * FROM technical_signals ORDER BY last_updated DESC", conn)
        quality_df = pd.read_sql("SELECT * FROM quality_scores ORDER BY quality_score DESC", conn)
        positions_df = pd.read_sql("SELECT * FROM open_positions", conn)
    finally:
        conn.close()
    return performance_df, signals_df, quality_df, positions_df

# --- TITOLO E HEADER ---
st.title("📈 Trading Bot Dashboard v3.3")
st.markdown(f"Ultimo aggiornamento della dashboard: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")

# --- PANNELLO DI STATO DEI SERVIZI ---
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
    equity = latest_perf['total_equity']
    pnl = latest_perf['unrealized_pnl']
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
