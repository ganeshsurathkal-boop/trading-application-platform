"""TICKR — Installed plugin metadata (dynamically-loaded indicators/scanners)"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, UniqueConstraint
from app.database import Base


class InstalledPlugin(Base):
    __tablename__ = "installed_plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)          # registry key, e.g. "RSI"
    plugin_type = Column(String(20), nullable=False)     # "indicator" | "scanner"
    version = Column(String(20), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)
    entry_module = Column(String(100), nullable=False)   # module filename, without .py
    entry_class = Column(String(100), nullable=False)    # class name inside the module
    dir_name = Column(String(200), nullable=False, unique=True)  # extracted folder name on disk
    enabled = Column(Boolean, default=True, nullable=False)
    installed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("name", "plugin_type", name="uq_plugin_name_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.plugin_type,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
        }
