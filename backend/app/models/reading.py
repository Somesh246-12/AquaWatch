"""SQLAlchemy model for water consumption readings."""

from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.zone import Zone


class Reading(Base):
    """Represents an hourly water consumption reading for a zone.

    Attributes:
        id: Primary key identifier.
        zone_id: Foreign key referencing zones.id.
        timestamp: Time when consumption was recorded.
        litres: Volume of water consumed in litres (>= 0).
    """

    __tablename__ = "readings"
    __table_args__ = (
        CheckConstraint("litres >= 0", name="ck_readings_non_negative_litres"),
        Index("ix_readings_zone_id_timestamp", "zone_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    litres = Column(Float, nullable=False)

    # Relationship to Zone
    zone = relationship("Zone", back_populates="readings")

    def __repr__(self) -> str:
        return (
            f"<Reading(id={self.id}, zone_id={self.zone_id}, "
            f"timestamp='{self.timestamp}', litres={self.litres})>"
        )
