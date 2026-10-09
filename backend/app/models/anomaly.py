"""SQLAlchemy model for ground truth injected anomalies.

IMPORTANT:
This table represents the GROUND TRUTH generated exclusively by the simulator.
It must NOT be accessed by detection algorithms during analysis.
It is reserved strictly for benchmarking and computing detector evaluation metrics
(Precision, Recall, and F1-score).
"""

from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.zone import Zone


class InjectedAnomaly(Base):
    """Ground truth anomaly injected during simulation.

    Attributes:
        id: Primary key identifier.
        zone_id: Foreign key referencing zones.id.
        timestamp: Timestamp of the injected anomaly event.
        anomaly_type: Category of anomaly ('slow_leak', 'burst', 'wastage_day').
    """

    __tablename__ = "injected_anomalies"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    anomaly_type = Column(String(50), nullable=False)

    # Relationship to Zone
    zone = relationship("Zone", back_populates="injected_anomalies")

    def __repr__(self) -> str:
        return (
            f"<InjectedAnomaly(id={self.id}, zone_id={self.zone_id}, "
            f"timestamp='{self.timestamp}', type='{self.anomaly_type}')>"
        )
