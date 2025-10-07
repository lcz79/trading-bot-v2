import sys
import structlog

def configure_logging():
    """
    Configura structlog per un output JSON standardizzato.
    Questo logger è pensato per essere usato da tutti i servizi del bot.
    """
    structlog.configure(
        processors=[
            # Aggiunge il livello di log (es. 'info', 'error') al record
            structlog.stdlib.add_log_level,
            # Aggiunge un timestamp UTC in formato ISO 8601
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Aggiunge il nome del logger (es. 'etl_service')
            structlog.stdlib.add_logger_name,
            # Rende il log in formato JSON, perfetto per l'analisi automatica
            structlog.processors.JSONRenderer(),
        ],
        # Usa un logger wrapper che è compatibile con la libreria standard 'logging'
        wrapper_class=structlog.stdlib.BoundLogger,
        # Usa un logger factory standard
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache per performance
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    """
    Restituisce un'istanza del logger configurato.
    
    Args:
        name (str): Il nome del modulo/servizio che sta loggando (es. __name__).
    
    Returns:
        Un logger structlog.
    """
    return structlog.get_logger(name)

# Configura il logging non appena questo modulo viene importato
configure_logging()