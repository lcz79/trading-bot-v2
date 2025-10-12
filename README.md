# 🔥 Phoenix Trading Bot v7 — Full Autonomous System

**Phoenix Trading Bot v7** è un sistema completo di **analisi automatica dei mercati**, generazione di segnali tecnici e visualizzazione in tempo reale, progettato per il trading su **Bybit** con integrazione diretta a **CoinGecko** e database locale.

> 🧠 Basato su Python, SQLAlchemy e Streamlit — costruito per operare come un vero "command center" per trader professionisti.

---

## 🚀 Funzionalità Principali

### 🧩 ETL Engine (Motore Analitico)
- Analisi automatica dei **fondamentali CoinGecko** per 10+ asset principali.  
- Download dati OHLC da **Bybit** (fino a 300 barre per timeframe).  
- Calcolo tecnico con trend detection (EMA, RSI, MACD, Volume Strength).  
- Generazione di **segnali LONG/SHORT** con score tecnico ponderato.  
- Salvataggio automatico nel database `phoenix_trading.db`.

### 📊 Dashboard Interattiva (Streamlit)
- Visualizzazione **in tempo reale** di equity, PnL e posizioni aperte su Bybit.  
- Analisi storica: giornaliera, settimanale, mensile e totale.  
- Tabella chiara di **segnali operativi** con:
  - Entry price, TP e SL già pronti.
  - Colori differenziati (🟢 LONG / 🔴 SHORT).
  - Calcolatore di rischio/rendimento personalizzato.
- Refresh dati live da database e API Bybit.

### 🧠 Architettura Modulare
- `etl_service.py`: motore principale che coordina le analisi.  
- `app.py`: dashboard e interfaccia di controllo.  
- `database.py`: ORM con SQLAlchemy e tabelle per segnali, trade e history.  
- `api_clients/`: moduli dedicati a Bybit e CoinGecko.  

---

## ⚙️ Installazione

Clona il repository:
```bash
git clone https://github.com/lcz79/trading-bot-v2.git
cd trading-bot-v2
# Progetto Phoenix - Trading Bot v7.0
