import os
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Numeric,
    Index, UniqueConstraint, text, JSON
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta, timezone

# ========================================================
# CONFIGURAZIONE DATABASE
# ========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non impostata")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# ========================================================
# MIXINS
# ========================================================

class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("timezone('utc', now())"),  # Nota: onupdate non è standard, ma ok per ora
        nullable=False,
    )

# ========================================================
# MODELLI DEL DATABASE
# ========================================================

class QualityScore(Base, TimestampMixin):
    __tablename__ = "quality_scores"
    id = Column(Integer, primary_key=True)
    asset = Column(String, index=True, unique=True, nullable=False)
    quality_score = Column(Integer, nullable=False)
    details = Column(JSON, nullable=True)

class TechnicalSignal(Base, TimestampMixin):
    __tablename__ = "technical_signals"
    id = Column(Integer, primary_key=True)
    asset = Column(String, index=True, nullable=False)
    timeframe = Column(String, index=True, nullable=False)
    strategy = Column(String, index=True, nullable=False)
    strategy_version = Column(String, nullable=True)
    signal = Column(String, index=True, nullable=False)
    entry_price = Column(Numeric(38, 18), nullable=False)
    stop_loss = Column(Numeric(38, 18))
    take_profit = Column(Numeric(38, 18))
    market_category = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    params = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)
    
    # --- NUOVA COLONNA PER LE NOTIFICHE ---
    notified_at = Column(DateTime(timezone=True), nullable=True, index=True)

Index("ix_signal_asset_tf_time", TechnicalSignal.asset, TechnicalSignal.timeframe, TechnicalSignal.updated_at.desc())

class OpenPosition(Base, TimestampMixin):
    __tablename__ = "open_positions"
    id = Column(Integer, primary_key=True)
    exchange = Column(String, nullable=False)
    account_id = Column(String, nullable=True)
    symbol = Column(String, index=True, nullable=False)
    position_side = Column(String, nullable=False)  # es. 'long' o 'short'
    size = Column(Numeric(38, 18), nullable=False)
    entry_price = Column(Numeric(38, 18), nullable=False)
    pnl = Column(Numeric(38, 18), nullable=True)

    __table_args__ = (
        UniqueConstraint("exchange", "account_id", "symbol", "position_side", name="uq_pos_scope"),
    )

class PerformanceLog(Base):
    __tablename__ = "performance_log"
    id = Column(Integer, primary_key=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=text("timezone('utc', now())"),
        nullable=False,
        index=True,
    )
    total_equity = Column(Numeric(38, 18), nullable=False)
    unrealized_pnl = Column(Numeric(38, 18), nullable=True)

# ========================================================
# FUNZIONI DI SERVIZIO
# ========================================================

def init_db():
    print("-> Sincronizzazione modelli con il database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database pronto e sincronizzato con i modelli.")

@contextmanager
def session_scope():
    """Fornisce uno scope transazionale per le sessioni del database."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def clear_old_signals(days: int = 2):
    """Cancella i segnali più vecchi di un certo numero di giorni."""
    with session_scope() as session:
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        (session.query(TechnicalSignal)
                .filter(TechnicalSignal.created_at < threshold)
                .delete(synchronize_session=False))
    print(f"-> Segnali più vecchi di {days} giorni cancellati.")
