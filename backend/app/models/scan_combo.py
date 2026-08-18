"""TICKR — Saved Scanner Combination ORM models"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ScanCombo(Base):
    __tablename__ = "scan_combos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    universe = Column(String(50), nullable=False, default="NIFTY 50")
    exchange = Column(String(10), nullable=False, default="NSE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    criteria = relationship(
        "ScanComboCriterion",
        back_populates="combo",
        cascade="all, delete-orphan",
        order_by="ScanComboCriterion.position",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_scan_combo_user_name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "universe": self.universe,
            "exchange": self.exchange,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "criteria": [c.to_dict() for c in self.criteria],
        }


class ScanComboCriterion(Base):
    __tablename__ = "scan_combo_criteria"

    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(Integer, ForeignKey("scan_combos.id"), nullable=False)
    scanner_name = Column(String(100), nullable=False)  # matches BaseScanner.name, e.g. "52-week high"
    params_json = Column(Text, nullable=False, default="{}")
    position = Column(Integer, nullable=False, default=0)

    combo = relationship("ScanCombo", back_populates="criteria")

    def to_dict(self) -> dict:
        return {
            "scanner_name": self.scanner_name,
            "params": json.loads(self.params_json) if self.params_json else {},
        }
