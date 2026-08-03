from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "postgresql://postgres:password@localhost:5433/sec_data"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InsiderTrade(Base):
    __tablename__ = "insider_trades"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, index=True)
    share_owner = Column(String)
    is_director = Column(String)
    transaction_code = Column(String)
    shares_traded = Column(Float)
    price = Column(Float)
    total_value = Column(Float)

class WatchlistCompany(Base):
    __tablename__ = "watchlist_companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    cik = Column(String, unique=True)

Base.metadata.create_all(bind=engine)