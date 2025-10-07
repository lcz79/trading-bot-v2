"""
Questo file __init__.py rende la cartella 'api_clients' un pacchetto Python
e definisce quali classi sono facilmente importabili dall'esterno.
"""

from .bybit_client import BybitClient
from .coingecko_client import CoinGeckoClient
from .data_client import FinancialDataClient
