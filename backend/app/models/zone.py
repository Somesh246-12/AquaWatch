"""SQLAlchemy model for monitoring zones."""

from typing import TYPE_CHECKING, List
from sqlalchemy import Column, Integer, String, Float, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.reading import Reading
    from app.models.alert import Alert
    from app.models.anomaly import InjectedAnomaly


class Zone(Base):
    """Represents a monitored water distribution or consumption zone.

    Attributes:
        id: Primary key identifier.
        name: Unique name of the zone (e.g. Household, Hostel Block).
        type: Functional classification of the zone.
        daily_budget_litres: Daily water allowance in litres (> 0).
    """

    __tablename__ = "zones"
    __table_args__ = (
        CheckConstraint("daily_budget_litres > 0", name="ck_zones_positive_budget"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False)
    daily_budget_litres = Column(Float, nullable=False)

    # Relationships
    readings = relationship(
        "Reading",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alerts = relationship(
        "Alert",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    injected_anomalies = relationship(
        "InjectedAnomaly",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Zone(id={self.id}, name='{self.name}', "
            f"type='{self.type}', daily_budget_litres={self.daily_budget_litres})>"
        )
