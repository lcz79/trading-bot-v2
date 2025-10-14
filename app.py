# app.py - v2.0 (Risoluzione Conflitto Database)
import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")

# --- INIZIALIZZAZIONE ESPLICITA DEL DATABASE ---
# Questa riga assicura che, dal punto di vista della dashboard,
# il database e la tabella vengano creati PRIMA di qualsiasi tentativo di lettura.
# Questo risolve il conflitto con il servizio in background.
db.init_db()

# --- HEADER ---
st.title("🤖 Trading Bot - Dashboard Segnali")
st.markdown(f"Ultimo aggiornamento: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")

# --- FUNZIONI ---
def fetch_data():
    """Recupera i segnali dal database."""
    try:
        signals = db.get_all_signals()
        if not signals:
            return pd.DataFrame()
        
        df = pd.DataFrame(signals)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calcoli per il potenziale guadagno/perdita
        df['Potenziale Guadagno ($)'] = (df['take_profit'] - df['entry_price']).abs() * 100 # Esempio con 100$ di size
        df['Potenziale Perdita ($)'] = (df['entry_price'] - df['stop_loss']).abs() * 100 # Esempio con 100$ di size
        
        return df
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        return pd.DataFrame()

# --- MAIN LAYOUT ---
signals_df = fetch_data()

# --- CONTROLLI ---
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader(f"Segnali Trovati ({len(signals_df)})")

with col2:
    if st.button("🔄 Aggiorna Dati"):
        st.rerun()

    if st.button("🗑️ Esporta in CSV e Cancella"):
        if not signals_df.empty:
            csv_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_export.csv"
            signals_df.to_csv(csv_filename, index=False)
            db.delete_all_signals()
            st.success(f"Dati esportati in `{csv_filename}` e database pulito.")
            st.rerun()
        else:
            st.warning("Nessun dato da esportare.")

# --- VISUALIZZAZIONE DATI ---
if not signals_df.empty:
    display_df = signals_df[[
        'timestamp', 'symbol', 'signal_type', 'score', 
        'entry_price', 'stop_loss', 'take_profit',
        'Potenziale Guadagno ($)', 'Potenziale Perdita ($)',
        'details'
    ]].rename(columns={
        'timestamp': 'Data',
        'symbol': 'Simbolo',
        'signal_type': 'Segnale',
        'score': 'Punteggio',
        'entry_price': 'Prezzo Ingresso',
        'details': 'Dettagli Confluenza'
    })
    
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("Nessun segnale trovato nel database. In attesa del prossimo ciclo di analisi...")
