# bot_config.py - v1.1
#
# Questo file contiene le impostazioni globali per il comportamento del bot.
# Modifica queste variabili per cambiare la strategia del bot senza toccare il codice.

# --- LIVELLO DI SENSIBILITÀ DEL MOTORE DI CONFLUENZA ---
SENSITIVITY_LEVEL = "BALANCED"


# --- DIZIONARIO DELLE SOGLIE ---
# Associa ogni livello di sensibilità a un punteggio di soglia.
# Questo dizionario è importato sia dal motore di analisi che dal backtester.
SENSITIVITY_THRESHOLDS = {
    "CONSERVATIVE": 70,
    "BALANCED": 50,
    "AGGRESSIVE": 35
}
