# app.py — Phoenix Command Center v7 (Pro Trading Dashboard)
# -------------------------------------------------------------------
# - Telemetria live Bybit (equity, posizioni, PnL fluttuante)
# - PnL storico (oggi/7d/30d/da inizio) + equity curve
# - Segnali operativi (verde LONG, rosso SHORT) con entry/TP/SL
# - Filtri simbolo/timeframe, export CSV, copia-ordine
# - Risk Manager (position sizing per rischio %)
# -------------------------------------------------------------------

from dotenv import load_dotenv
from pathlib import Path
import os
import datetime as dt
import pandas as pd
import numpy as np
import streamlit as st

# DB & Models
import database
from sqlalchemy import desc, text

# Opzionale: client Bybit per live data
try:
    from api_clients.bybit_client import BybitClient
except Exception:
    BybitClient = None

# === ENV ===
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# === PAGE CONFIG ===
st.set_page_config(page_title="Phoenix Command Center", page_icon="🔥", layout="wide")
database.init_db()

# === UTILS ===
def dt_utc_now():
    return dt.datetime.utcnow()

def start_of_day_utc():
    now = dt_utc_now()
    return dt.datetime(now.year, now.month, now.day)

def days_ago(n):
    return dt_utc_now() - dt.timedelta(days=n)

def to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

# ====== DATA LOADERS (CACHED) ======
@st.cache_data(ttl=20)
def load_live_bybit():
    """Equity + posizioni aperte dal client Bybit."""
    if not BybitClient:
        return 0.0, []
    try:
        client = BybitClient()
        balance = client.get_wallet_balance()
        positions = client.get_positions()
    except Exception:
        return 0.0, []

    total_equity = 0.0
    if balance and balance.get("retCode") == 0:
        try:
            total_equity = float(balance["result"]["list"][0]["totalEquity"])
        except Exception:
            total_equity = 0.0

    pos_list = []
    if positions and positions.get("retCode") == 0:
        pos_list = positions["result"]["list"]

    return total_equity, pos_list


@st.cache_data(ttl=20)
def load_signals(limit=200):
    """Carica segnali da technical_signals o trade_intents, il più ricco disponibile."""
    with database.session_scope() as session:
        # Preferisci technical_signals
        try:
            q = session.query(database.TechnicalSignal).order_by(desc(database.TechnicalSignal.id)).limit(limit).statement
            df = pd.read_sql(q, database.engine, parse_dates=["created_at"])
            if not df.empty:
                df["source_table"] = "technical_signals"
                return df
        except Exception:
            pass

        # Fallback su trade_intents
        try:
            q = session.query(database.TradeIntent).order_by(desc(database.TradeIntent.id)).limit(limit).statement
            df = pd.read_sql(q, database.engine, parse_dates=["timestamp"])
            if not df.empty:
                df = df.rename(columns={"timestamp": "created_at", "symbol": "asset", "direction": "signal", "score": "score"})
                df["timeframe"] = df.get("timeframe", pd.Series(["?"] * len(df)))
                df["strategy"] = df.get("strategy", pd.Series(["intent"] * len(df)))
                df["details"] = None
                df["source_table"] = "trade_intents"
                return df
        except Exception:
            pass

    return pd.DataFrame()


@st.cache_data(ttl=20)
def load_trade_history():
    """Carica la trade_history per metriche PnL ed equity curve."""
    try:
        with database.session_scope() as session:
            q = session.query(database.TradeHistory).order_by(desc(database.TradeHistory.timestamp)).statement
            df = pd.read_sql(q, database.engine, parse_dates=["timestamp"])
            return df
    except Exception:
        return pd.DataFrame()


# ====== HEADER ======
st.title("🔥 Phoenix Command Center v7")

# Auto-refresh soft
st.caption("Auto-refresh ogni 20s (live) • usa il bottone per forzare.")
col_ref, _ = st.columns([1, 8])
if col_ref.button("🔄 Aggiorna ora"):
    st.cache_data.clear()
    st.rerun()

# ====== TELEMETRIA LIVE ======
st.header("🛰️ Telemetria Live — Conto Bybit")
equity_usd, live_positions = load_live_bybit()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity Totale (USD)", f"${equity_usd:,.2f}")

# PnL fluttuante dalle posizioni aperte
open_positions_df = pd.DataFrame(live_positions)
if not open_positions_df.empty:
    for col in ["size", "unrealisedPnl", "avgPrice", "liqPrice"]:
        if col in open_positions_df.columns:
            open_positions_df[col] = pd.to_numeric(open_positions_df[col], errors="coerce")

    open_positions_df = open_positions_df[open_positions_df.get("size", 0) > 0]
    float_pnl = open_positions_df.get("unrealisedPnl", pd.Series([0.0])).fillna(0).sum()
    c2.metric("PnL Fluttuante", f"${float_pnl:,.2f}", delta=f"{float_pnl:,.2f}")
    c3.metric("Posizioni Aperte", int(len(open_positions_df)))
else:
    float_pnl = 0.0
    c2.metric("PnL Fluttuante", "$0.00")
    c3.metric("Posizioni Aperte", 0)

# Ultimo aggiornamento
c4.metric("Ultimo Refresh (UTC)", dt_utc_now().strftime("%H:%M:%S"))

# Dettaglio posizioni
if not open_positions_df.empty:
    st.subheader("Dettaglio Posizioni Aperte")
    disp_cols = ["symbol", "side", "size", "avgPrice", "unrealisedPnl", "leverage", "liqPrice"]
    show_cols = [c for c in disp_cols if c in open_positions_df.columns]
    st.dataframe(
        open_positions_df[show_cols].rename(columns={
            "symbol": "Simbolo", "side": "Direzione", "size": "Quantità",
            "avgPrice": "Prezzo Medio", "unrealisedPnl": "PnL non real.",
            "leverage": "Leva", "liqPrice": "Prezzo Liquidazione"
        }),
        use_container_width=True
    )
else:
    st.info("Nessuna posizione attualmente aperta.")

# ====== PnL STORICO & EQUITY CURVE ======
st.header("📈 PnL Storico & Equity Curve")

trades_df = load_trade_history()

def period_pnl(df, start, end=None):
    if df.empty:
        return 0.0
    if end is None:
        end = dt_utc_now()
    mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
    return float(df.loc[mask, "pnl"].fillna(0).sum())

today_start = start_of_day_utc()
pnl_today = period_pnl(trades_df, today_start)
pnl_7d = period_pnl(trades_df, days_ago(7))
pnl_30d = period_pnl(trades_df, days_ago(30))
pnl_total = float(trades_df["pnl"].fillna(0).sum()) if not trades_df.empty else 0.0

d1, d2, d3, d4 = st.columns(4)
d1.metric("PnL Oggi", f"${pnl_today:,.2f}", delta=f"{pnl_today:,.2f}")
d2.metric("PnL 7 Giorni", f"${pnl_7d:,.2f}", delta=f"{pnl_7d:,.2f}")
d3.metric("PnL 30 Giorni", f"${pnl_30d:,.2f}", delta=f"{pnl_30d:,.2f}")
d4.metric("PnL Totale", f"${pnl_total:,.2f}")

# Equity curve (cumulata trade_history)
if not trades_df.empty:
    ec = trades_df.sort_values("timestamp")[["timestamp", "pnl"]].copy()
    ec["equity_curve"] = ec["pnl"].fillna(0).cumsum()
    st.line_chart(ec.set_index("timestamp")["equity_curve"], height=220)
else:
    st.info("Nessun trade storico registrato (trade_history vuota).")

# ====== SEGNALI OPERATIVI ======
st.header("🎯 Segnali Operativi (Entry / TP / SL)")

signals_df = load_signals(limit=300)

if signals_df.empty:
    st.info("Nessun segnale disponibile. Attendi il prossimo ciclo ETL.")
else:
    # Normalizza colonne tra technical_signals e trade_intents
    # Colonne attese: asset, timeframe, strategy, signal, entry_price, take_profit, stop_loss, created_at, details
    rename_map = {
        "symbol": "asset",
        "timestamp": "created_at"
    }
    for k, v in rename_map.items():
        if k in signals_df.columns and v not in signals_df.columns:
            signals_df[v] = signals_df[k]

    # parsing numerici
    for c in ["entry_price", "take_profit", "stop_loss"]:
        if c in signals_df.columns:
            signals_df[c] = signals_df[c].apply(to_float)

    # Filtri rapidi
    left, mid, right = st.columns([3, 2, 1])
    all_assets = sorted(list(signals_df["asset"].dropna().unique()))
    f_asset = left.multiselect("Filtra per asset", options=all_assets, default=all_assets)
    all_tf = sorted(list(signals_df.get("timeframe", pd.Series(["1D"])).dropna().unique()))
    f_tf = mid.multiselect("Timeframe", options=all_tf, default=all_tf)
    sort_opt = right.selectbox("Ordina per", options=["created_at desc", "score desc", "asset asc"], index=0)

    df = signals_df.copy()
    df = df[df["asset"].isin(f_asset)]
    if "timeframe" in df.columns:
        df = df[df["timeframe"].isin(f_tf)]

    if sort_opt == "created_at desc" and "created_at" in df.columns:
        df = df.sort_values("created_at", ascending=False)
    elif sort_opt == "score desc" and "score" in df.columns:
        df = df.sort_values("score", ascending=False)
    elif sort_opt == "asset asc":
        df = df.sort_values("asset", ascending=True)

    # Tabella compatta con colori LONG/SHORT
    show_cols = ["created_at", "asset", "timeframe", "strategy", "signal", "entry_price", "take_profit", "stop_loss"]
    show_cols = [c for c in show_cols if c in df.columns]

    def color_rows(row):
        sig = str(row.get("signal", "")).upper()
        color = "background-color: rgba(0,255,0,0.08)" if "LONG" in sig else ("background-color: rgba(255,0,0,0.08)" if "SHORT" in sig else "")
        return [color] * len(row)

    st.dataframe(df[show_cols].style.apply(color_rows, axis=1), use_container_width=True, height=360)

    # Selezione singolo segnale per creare l'ordine + copia
    st.subheader("🧾 Dettaglio & Ordine Rapido")
    if "id" in df.columns:
        df["label"] = df.apply(lambda r: f"[{str(r.get('signal','')).upper()}] {r.get('asset','?')} {r.get('timeframe','?')} @ {r.get('entry_price','?')}", axis=1)
        selected = st.selectbox("Seleziona un segnale", options=df["label"].tolist())
        sel_row = df[df["label"] == selected].iloc[0]

        sym = sel_row.get("asset", "?")
        sig = str(sel_row.get("signal", "N/A")).upper()
        tf = sel_row.get("timeframe", "?")
        entry = sel_row.get("entry_price", 0.0)
        tp = sel_row.get("take_profit", 0.0)
        sl = sel_row.get("stop_loss", 0.0)

        cA, cB, cC, cD = st.columns(4)
        cA.metric("Segnale", sig)
        cB.metric("Asset", sym)
        cC.metric("Timeframe", str(tf))
        cD.metric("Entry", f"{entry:.6f}" if entry else "N/A")

        cE, cF = st.columns(2)
        cE.metric("Take Profit", f"{to_float(tp):.6f}" if tp else "N/A")
        cF.metric("Stop Loss", f"{to_float(sl):.6f}" if sl else "N/A")

        # Pulsante copia-ordine (testo)
        order_text = f"{sym} | {sig} | Entry: {entry} | TP: {tp} | SL: {sl} | TF: {tf}"
        st.text_area("Ordine da copiare su Bybit:", order_text, height=70)
        st.caption("Copia e incolla sopra in Bybit. (Puoi adattare quantità/leva secondo il Risk Manager sotto)")

    # Export CSV
    st.download_button("⬇️ Esporta Segnali (CSV)", data=df.to_csv(index=False).encode("utf-8"), file_name="signals_export.csv", mime="text/csv")

# ====== RISK MANAGER ======
st.header("🛡️ Risk Manager — Position Sizing")

rm1, rm2, rm3, rm4 = st.columns(4)
account_equity = rm1.number_input("Equity Conto (USD)", min_value=0.0, value=float(equity_usd), step=100.0)
risk_pct = rm2.number_input("Rischio per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
entry_price = rm3.number_input("Entry Price", min_value=0.0, value=0.0, format="%.6f")
stop_price = rm4.number_input("Stop Loss Price", min_value=0.0, value=0.0, format="%.6f")

if st.button("Calcola Size"):
    if entry_price > 0 and stop_price > 0 and entry_price != stop_price:
        risk_usd = account_equity * (risk_pct / 100.0)
        per_unit_risk = abs(entry_price - stop_price)
        if per_unit_risk == 0:
            st.error("Entry e Stop identici: impossibile calcolare.")
        else:
            qty = risk_usd / per_unit_risk
            st.success(f"Quantità consigliata: **{qty:,.4f}** (valore posizione ≈ ${qty * entry_price:,.2f})")
            st.caption("Nota: non include commissioni/slippage. Adatta per leva e step-size del contratto.")
    else:
        st.warning("Inserisci Entry e Stop validi per calcolare la size.")

# ====== FOOTER ======
st.markdown("---")
st.caption("Phoenix Command Center v7 • Live Telemetry • Real TA • Order-Ready Signals")
