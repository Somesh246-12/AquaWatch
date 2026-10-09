"""Alert service layer handling alerts querying and status updates."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert


def get_alerts(
    db: Session,
    zone_id: Optional[int] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    alert_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Alert]:
    """Retrieves alerts matching optional filter criteria, ordered newest first."""
    query = db.query(Alert)

    if zone_id is not None:
        query = query.filter(Alert.zone_id == zone_id)
    if severity is not None:
        query = query.filter(Alert.severity == severity)
    if resolved is not None:
        query = query.filter(Alert.resolved == resolved)
    if alert_type is not None:
        query = query.filter(Alert.alert_type == alert_type)

    return query.order_by(Alert.timestamp.desc()).offset(offset).limit(limit).all()


def get_alert_by_id(db: Session, alert_id: int) -> Optional[Alert]:
    """Retrieves a single alert by identifier."""
    return db.query(Alert).filter(Alert.id == alert_id).first()


def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Marks an alert as resolved (resolved = True).

    Returns:
        The updated Alert entity, or None if the alert does not exist.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None

    alert.resolved = True
    db.commit()
    db.refresh(alert)
    return alert
