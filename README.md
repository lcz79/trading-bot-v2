# Trading Bot v2 - Strategia Pullback Ottimizzata

Questo è un bot di trading per criptovalute sviluppato per operare su timeframe orari. Il sistema implementa una strategia di "Pullback Trading" basata su medie mobili esponenziali (EMA), con parametri ottimizzati individualmente per ogni asset.

## Strategia Implementata: "Operazione Pullback"

- **Definizione Trend:** Una EMA lenta (es. 50, 100, 200) definisce il trend principale. Si cercano solo trade LONG sopra la EMA e solo SHORT sotto.
- **Zona di Ingresso:** Una EMA veloce (es. 10, 20) identifica la zona di pullback.
- **Segnale:** L'ingresso avviene dopo un pullback verso la EMA veloce, alla prima candela di conferma che segnala la ripresa del trend principale.
- **Gestione del Rischio:** Stop Loss posizionato sul minimo/massimo della candela precedente e Take Profit calcolato con un rapporto Rischio/Rendimento fisso.

## Componenti del Progetto

- `optimizer.py`: Script per l'ottimizzazione dei parametri della strategia. Esegue centinaia di backtest per trovare la combinazione di EMA e R/R con il Profit Factor più alto per ogni singolo asset.
- `optimal_strategies.json`: File di configurazione (generato dall'optimizer) che contiene il "DNA" della strategia migliore per ogni criptovaluta.
- `etl_service.py`: Il servizio principale che opera in tempo reale. Carica le strategie ottimali e analizza il mercato, generando segnali.
- `market_analysis.py`: Il motore di analisi che implementa la logica di pullback.
- `database.py`: Gestione del database SQLite per il salvataggio dei segnali.
- `app.py`: Una dashboard web interattiva (basata su Streamlit) per visualizzare i segnali di trading in tempo reale.
- `backtester.py`: Script versatile usato per testare le varie iterazioni della strategia.

## Come Avviare il Bot

1.  **Crea e attiva un ambiente virtuale:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **(Opzionale) Esegui l'ottimizzatore per generare la tua configurazione:**
    ```bash
    python optimizer.py
    ```
4.  **Avvia il servizio di analisi in un terminale:**
    ```bash
    sh start_etl_service.sh
    ```
5.  **Avvia la dashboard in un altro terminale:**
    ```bash
    streamlit run app.py
    ```