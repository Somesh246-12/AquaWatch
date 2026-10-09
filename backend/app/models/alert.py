"""SQLAlchemy model for leak and anomaly alerts."""

from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.zone import Zone


class Alert(Base):
    """Represents an anomaly or leak alert detected for a specific zone.

    Attributes:
        id: Primary key identifier.
        zone_id: Foreign key referencing zones.id.
        timestamp: Timestamp of the alert occurrence.
        alert_type: Type of alert (e.g. 'leak', 'spike', 'abnormal_usage').
        severity: Urgency of the alert ('low', 'medium', 'high').
        message: Explanatory diagnostic message.
        resolved: Flag indicating whether the alert has been acknowledged/resolved.
    """

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_zone_id_resolved", "zone_id", "resolved"),
    )

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, nullable=False, default=False, index=True)

    # Relationship to Zone
    zone = relationship("Zone", back_populates="alerts")

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, zone_id={self.zone_id}, "
            f"type='{self.alert_type}', severity='{self.severity}', resolved={self.resolved})>"
        )
