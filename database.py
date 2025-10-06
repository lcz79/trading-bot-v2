import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non è impostato nel file .env")

# --- Configurazione SQLAlchemy ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Definizione Tabelle come Classi (ORM) ---
class PerformanceLog(Base):
    __tablename__ = "performance_log"
    timestamp = Column(DateTime, primary_key=True, default=datetime.now)
    total_equity = Column(Float, nullable=False)
    unrealized_pnl = Column(Float)
    realized_pnl_24h = Column(Float)

class TechnicalSignal(Base):
    __tablename__ = "technical_signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    signal = Column(String, nullable=False)
    price = Column(String)
    stop_loss = Column(String)
    take_profit = Column(String)
    details = Column(String)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class QualityScore(Base):
    __tablename__ = "quality_scores"
    asset = Column(String, primary_key=True)
    quality_score = Column(Integer, nullable=False)
    details = Column(String)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# --- Funzioni di Gestione ---
def get_db_session():
    """Genera una sessione di database."""
    return SessionLocal()

def init_db():
    """Inizializza il database, creando le tabelle se non esistono."""
    try:
        print("-> Inizializzazione database (controllo tabelle PostgreSQL)...")
        Base.metadata.create_all(bind=engine)
        print("-> Database pronto.")
    except Exception as e:
        print(f"ERRORE durante l'inizializzazione del database: {e}")
        raise

# --- Funzioni di Interazione ---
def store_performance_log(session, equity, pnl, pnl_realized):
    try:
        log_entry = PerformanceLog(
            timestamp=datetime.now(), total_equity=equity, unrealized_pnl=pnl, realized_pnl_24h=pnl_realized
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"ERRORE nel salvataggio del performance_log: {e}")

def store_quality_score(session, asset, score, details):
    try:
        score_entry = QualityScore(asset=asset, quality_score=score, details=details)
        session.merge(score_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"ERRORE nel salvataggio del quality_score per {asset}: {e}")

def clear_old_signals(session):
    try:
        session.query(TechnicalSignal).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"ERRORE nella pulizia dei vecchi segnali: {e}")

def store_technical_signal(session, asset, timeframe, strategy, signal, price, sl, tp, details):
    try:
        signal_entry = TechnicalSignal(
            asset=asset, timeframe=timeframe, strategy=strategy, signal=signal,
            price=price, stop_loss=sl, take_profit=tp, details=details
        )
        session.add(signal_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"ERRORE nel salvataggio del segnale tecnico per {asset}: {e}")
