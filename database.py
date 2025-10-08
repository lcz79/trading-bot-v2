# database.py - (Phoenix Patch v7.0 Applied)
# Aggiunta la tabella TechnicalSignal per i segnali multi-timeframe.

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, inspect, func, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from datetime import datetime

# ... (Codice esistente: Base, TradeIntent, OpenPosition, TradeHistory) ...
Base = declarative_base()

class TradeIntent(Base):
    __tablename__ = 'trade_intents'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    score = Column(Integer)
    status = Column(String, default='NEW')
    timestamp = Column(DateTime, default=datetime.utcnow)

class OpenPosition(Base):
    __tablename__ = 'open_positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class TradeHistory(Base):
    __tablename__ = 'trade_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    status = Column(String) # 'TP', 'SL', 'MANUAL'
    timestamp = Column(DateTime, default=datetime.utcnow)

# NUOVA TABELLA
class TechnicalSignal(Base):
    __tablename__ = 'technical_signals'
    id = Column(Integer, primary_key=True)
    asset = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy = Column(String(50))
    signal = Column(String(100))
    entry_price = Column(Numeric(20, 8))
    stop_loss = Column(Numeric(20, 8), nullable=True)
    take_profit = Column(Numeric(20, 8), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ... (Codice esistente: engine, Session, init_db, session_scope) ...
DATABASE_URL = "sqlite:///phoenix_trading.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Errore di sessione: {e}")
        raise
    finally:
        session.close()
