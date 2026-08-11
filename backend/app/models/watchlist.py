"""TICKR — Watchlist ORM models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    stocks = relationship("WatchlistStock", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    symbol = Column(String(30), nullable=False)
    exchange = Column(String(10), nullable=False, default="NSE")
    added_at = Column(DateTime, default=datetime.utcnow)

    watchlist = relationship("Watchlist", back_populates="stocks")
