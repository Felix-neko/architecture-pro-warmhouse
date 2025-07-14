from datetime import datetime, timezone
from typing import List, Any, Optional

from sqlalchemy import (
    Integer,
    DateTime,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB as JSON


from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
)

Base = declarative_base()


class FloatTelemetrySampleORM(Base):
    __tablename__ = "float_telemetry_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id!r} time={self.time!r}>"


class JsonTelemetrySampleORM(Base):
    __tablename__ = "json_telemetry_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id!r} time={self.time!r}>"
