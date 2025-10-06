import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Trading System v4.0", layout="wide")
st.title("🚀 Trading System v4.0 - The Vault")

DB_FILE = "trading_system.db"
PERFORMANCE_INTERVAL_MIN = 15
SCANNER_INTERVAL_MIN = 30

def get_db_data(query):
    """Funzione generica per leggere dati dal database."""
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Errore di lettura dal database: {e}")
        return pd.DataFrame()

def display_countdown(label, last_update_time, interval_minutes):
    """Visualizza un conto alla rovescia per il prossimo aggiornamento."""
    if last_update_time and not pd.isna(last_update_time):
        # Conversione esplicita e sicura a datetime
        last_update_time = pd.to_datetime(last_update_time)
        next_update_time = last_update_time + timedelta(minutes=interval_minutes)
        time_left = next_update_time - datetime.now()
        
        if time_left.total_seconds() > 0:
            minutes, seconds = divmod(int(time_left.total_seconds()), 60)
            st.caption(f"{label} tra: **{minutes:02d}:{seconds:02d}**")
        else:
            st.caption(f"{label}: In attesa di esecuzione...")
    else:
        st.caption(f"{label}: In attesa del primo aggiornamento...")

def style_scanner_table(df):
    """Colora la tabella dei segnali."""
    def get_color(signal):
        if "LONG" in signal: return 'background-color: #2E4035; color: #7FFF7F;'
        if "SHORT" in signal: return 'background-color: #4B2F2F; color: #FF7F7F;'
        return ''
    return df.style.apply(lambda row: [get_color(row['signal'])] * len(row), axis=1)

# --- PANNELLO PERFORMANCE ---
st.header("📈 Performance del Conto (Bybit)")

col_btn, col_timer_perf = st.columns([1, 5])
with col_btn:
    if st.button("🔄 Aggiorna Vista"):
        st.rerun()
with col_timer_perf:
    last_perf_update_df = get_db_data("SELECT MAX(timestamp) as last_update FROM performance_log")
    last_perf_update = last_perf_update_df['last_update'].iloc[0] if not last_perf_update_df.empty else None
    display_countdown("Prossimo aggiornamento Saldo/P&L", last_perf_update, PERFORMANCE_INTERVAL_MIN)

performance_df = get_db_data("SELECT * FROM performance_log ORDER BY timestamp DESC LIMIT 2880")
if not performance_df.empty:
    performance_df['timestamp'] = pd.to_datetime(performance_df['timestamp'])
    latest_data = performance_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Equity Totale (EUR)", f"€{latest_data['total_equity']:,.2f}")
    col2.metric("P&L Non Realizzato", f"€{latest_data['unrealized_pnl']:,.2f}")
    col3.metric("P&L Realizzato (24h)", "In Sviluppo")
    st.line_chart(performance_df.set_index('timestamp')['total_equity'])
else:
    st.warning("Nessun dato di performance trovato. `exchange_service.py` è in esecuzione?")

st.divider()

# --- MARKET SCANNER ---
st.header("🔥 Market Scanner")
last_scan_time_df = get_db_data("SELECT MAX(last_updated) as last_scan FROM technical_signals")
last_scan_time = last_scan_time_df['last_scan'].iloc[0] if not last_scan_time_df.empty else None
display_countdown("Prossimo Scan di Mercato", last_scan_time, SCANNER_INTERVAL_MIN)

signals_df = get_db_data("SELECT asset, timeframe, strategy, signal, price, stop_loss, take_profit, details, last_updated FROM technical_signals ORDER BY asset")

if not signals_df.empty:
    signals_df['last_updated'] = pd.to_datetime(signals_df['last_updated'])
    strategy_filter = st.selectbox("Filtra per Strategia", options=["Tutte"] + list(signals_df['strategy'].unique()))
    
    filtered_df = signals_df.copy()
    if strategy_filter != "Tutte":
        filtered_df = filtered_df[filtered_df['strategy'] == strategy_filter]

    st.dataframe(style_scanner_table(filtered_df.drop(columns=['last_updated'])), use_container_width=True, hide_index=True)
else:
    st.info("Nessun segnale tecnico trovato. Il servizio ETL è in esecuzione?")

with st.expander("Mostra Risultati Screening di Qualità"):
    quality_df = get_db_data("SELECT asset, quality_score, details, last_updated FROM quality_scores ORDER BY quality_score DESC")
    if not quality_df.empty:
        quality_df['last_updated'] = pd.to_datetime(quality_df['last_updated'])
    st.dataframe(quality_df, use_container_width=True, hide_index=True)
