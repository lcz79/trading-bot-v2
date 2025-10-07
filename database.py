import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Definizione dei Modelli ---

class TradeIntent(Base):
    __tablename__ = 'trade_intents'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    status = Column(String, default='NEW', nullable=False)
    timeframe = Column(String)
    strategy = Column(String)
    
    # Aggiungiamo la relazione: un intento può avere più ordini (anche se di solito è uno)
    orders = relationship("Order", back_populates="intent")

    def __repr__(self):
        return f"<TradeIntent(id={self.id}, symbol='{self.symbol}', status='{self.status}')>"

# --- NUOVO MODELLO AGGIUNTO ---
class Order(Base):
    """
    Rappresenta un ordine eseguito sull'exchange.
    Questo modello era mancante e causava l'errore di dipendenza.
    """
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    # Collega questo ordine all'intento che lo ha generato
    intent_id = Column(Integer, ForeignKey('trade_intents.id'), nullable=False)
    
    symbol = Column(String, nullable=False)
    order_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False) # e.g., 'NEW', 'FILLED', 'CANCELED'
    side = Column(String, nullable=False) # 'Buy' or 'Sell'
    price = Column(Float, nullable=False)
    qty = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Aggiungiamo la relazione inversa
    intent = relationship("TradeIntent", back_populates="orders")

    def __repr__(self):
        return f"<Order(id={self.id}, order_id='{self.order_id}', status='{self.status}')>"
# -----------------------------

class OpenPosition(Base):
    __tablename__ = 'open_positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, unique=True)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    position_value = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Funzioni di Utilità del Database ---

def init_db():
    print("-> Sincronizzazione modelli con il database...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database pronto e sincronizzato con i modelli.")
    except SQLAlchemyError as e:
        print(f"🔥 Errore durante l'inizializzazione del database: {e}")

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        print(f"🔥 Errore di sessione database: {e}")
        session.rollback()
        raise
    finally:
        session.close()
