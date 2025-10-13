# app.py - v4.1 (Fix per il formato della data)
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "trading_signals.db"

def get_signals_from_db():
    """Recupera tutti i segnali dal database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT * FROM signals ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        return pd.DataFrame()

# --- Configurazione Pagina ---
st.set_page_config(page_title="Trading Signal Dashboard", layout="wide")

# --- Titolo e Header ---
st.title("🤖 Super Confluence Engine - Dashboard Operativa")
st.markdown("Questa dashboard mostra i segnali di trading generati dal bot, completi di parametri operativi.")

# --- Controlli Interattivi ---
st.sidebar.header("Parametri di Simulazione Trade")
investment_amount = st.sidebar.number_input("Importo Investimento ($)", min_value=10.0, value=100.0, step=10.0)
leverage = st.sidebar.number_input("Leva Finanziaria", min_value=1.0, value=10.0, step=1.0)

# --- Pulsante di Aggiornamento ---
if st.button("🔄 Aggiorna Dati"):
    st.cache_data.clear()
    st.rerun()

# --- Tabella Segnali ---
st.header("Segnali di Trading Rilevati")
signals_df = get_signals_from_db()

if not signals_df.empty:
    # --- FIX APPLICATO QUI ---
    # Specifichiamo a pandas il formato corretto per evitare errori di interpretazione.
    # 'errors="coerce"' trasformerà qualsiasi data non valida in 'NaT' (Not a Time)
    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'], errors='coerce')
    
    # Rimuoviamo eventuali righe con date non valide prima di procedere
    signals_df.dropna(subset=['timestamp'], inplace=True)
    
    # Formattiamo la data solo per la visualizzazione
    signals_df['timestamp_display'] = signals_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    # -------------------------
    
    results = []
    for index, row in signals_df.iterrows():
        entry = row['entry_price']
        sl = row['stop_loss']
        tp = row['take_profit']
        
        if pd.notna(entry) and pd.notna(sl) and pd.notna(tp) and entry > 0:
            risk_per_unit = abs(entry - sl)
            reward_per_unit = abs(tp - entry)
            position_size_usd = investment_amount * leverage
            units_traded = position_size_usd / entry
            potential_loss = units_traded * risk_per_unit
            potential_profit = units_traded * reward_per_unit
            results.append({
                "Potenziale Perdita ($)": f"{potential_loss:.2f}",
                "Potenziale Guadagno ($)": f"{potential_profit:.2f}"
            })
        else:
            results.append({"Potenziale Perdita ($)": "N/A", "Potenziale Guadagno ($)": "N/A"})
            
    results_df = pd.DataFrame(results, index=signals_df.index)
    display_df = pd.concat([signals_df, results_df], axis=1)
    
    columns_to_show = [
        'timestamp_display', 'symbol', 'signal_type', 'score', 
        'entry_price', 'stop_loss', 'take_profit',
        'Potenziale Guadagno ($)', 'Potenziale Perdita ($)',
        'details'
    ]
    display_df = display_df[columns_to_show].rename(columns={
        'timestamp_display': 'Data', 'symbol': 'Simbolo', 'signal_type': 'Segnale', 
        'score': 'Punteggio', 'entry_price': 'Prezzo Ingresso', 
        'stop_loss': 'Stop Loss', 'take_profit': 'Take Profit', 'details': 'Dettagli Confluenza'
    })

    st.dataframe(display_df, use_container_width=True)
else:
    st.info("Nessun segnale rilevato. Il bot è in ascolto del mercato...")

st.sidebar.info("I calcoli di profitto/perdita sono simulazioni e non includono commissioni o slippage.")
