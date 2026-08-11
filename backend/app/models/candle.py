"""TICKR — Candle ORM model (OHLCV daily data)"""
from datetime import date
from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from app.database import Base


class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, default="NSE")
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "date", name="uq_candle_symbol_date"),
    )

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "date": self.date.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
