# database.py - v3.0.0 (Production Ready)
# ----------------------------------------------------------------
# - Compatibile con PostgreSQL e SQLite.
# - Gestisce correttamente il reset con 'CASCADE' su PostgreSQL.
# - Codice pulito e formattato secondo le best practice.
# ----------------------------------------------------------------

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum as SQLAlchemyEnum, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session
from contextlib import contextmanager
import datetime
import enum

# --- Configurazione ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")

connect_args = {}
is_postgres = DATABASE_URL.startswith("postgres")
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelli ---
class TradeIntentStatus(enum.Enum):
    NEW = "NEW"; SIMULATED = "SIMULATED"; EXECUTED = "EXECUTED"; CLOSED = "CLOSED"; ERROR = "ERROR"

class TradeIntent(Base):
    __tablename__ = 'trade_intents'
    id = Column(Integer, primary_key=True, index=True); timestamp = Column(DateTime, default=datetime.datetime.utcnow); symbol = Column(String, index=True); direction = Column(String); entry_price = Column(Float); stop_loss = Column(Float); take_profit = Column(Float); score = Column(Integer); strategy = Column(String); status = Column(SQLAlchemyEnum(TradeIntentStatus), default=TradeIntentStatus.NEW); timeframe = Column(String)

class PerformanceLog(Base):
    __tablename__ = 'performance_logs'
    id = Column(Integer, primary_key=True, index=True); timestamp = Column(DateTime, default=datetime.datetime.utcnow); total_equity = Column(Float); unrealized_pnl = Column(Float); realized_pnl = Column(Float)

class OpenPosition(Base):
    __tablename__ = 'open_positions'
    id = Column(Integer, primary_key=True, index=True); symbol = Column(String, unique=True, index=True); side = Column(String); entry_price = Column(Float); size = Column(Float); position_value = Column(Float); leverage = Column(Integer); timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# --- Gestione ---
def init_db(reset: bool = False):
    print("--- Sincronizzazione Database ---")
    if reset:
        print("-> Richiesto reset del database. Eliminazione tabelle...")
        if is_postgres:
            print("   -> Rilevato PostgreSQL. Eseguo DROP...CASCADE.")
            with engine.connect() as connection:
                with connection.begin():
                    for table in reversed(Base.metadata.sorted_tables):
                        connection.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE;'))
            print("   -> DROP CASCADE completato.")
        else:
            Base.metadata.drop_all(engine)
        print("-> Tabelle eliminate.")
    
    print("-> Sincronizzazione modelli con il database...")
    Base.metadata.create_all(engine)
    print("✅ Database pronto e sincronizzato con i modelli.")

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback(); raise
    finally:
        session.close()
