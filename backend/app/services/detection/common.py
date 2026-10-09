"""Common data structures and utilities for the AquaWatch detection engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from app.models import Reading, Zone


@dataclass
class DetectionResult:
    """Represents a discrete anomaly detection event produced by any detector.

    Attributes:
        zone_id: Identifier of the monitored zone.
        zone_name: Human-readable name of the zone.
        timestamp: Start timestamp of the detected anomalous window.
        end_timestamp: Optional end timestamp for multi-hour events.
        method: Detection method ('rule_based', 'z_score', 'isolation_forest').
        anomaly_type: Inferred category ('slow_leak', 'burst', 'wastage_day', 'abnormal_usage').
        severity: Urgency of the anomaly ('low', 'medium', 'high').
        score: Optional numerical anomaly metric or confidence score.
        litres: Optional water consumption volume observed during the anomaly.
        message: Diagnostic explanation of why the reading was flagged.
        metadata: Additional method-specific attributes (duration, baseline, threshold, etc.).
    """

    zone_id: int
    zone_name: str
    timestamp: datetime
    end_timestamp: Optional[datetime] = None
    method: str = "rule_based"
    anomaly_type: str = "abnormal_usage"
    severity: str = "medium"
    score: Optional[float] = None
    litres: Optional[float] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_readings_dataframe(session: Session) -> pd.DataFrame:
    """Loads all time-series readings from database as a structured pandas DataFrame.

    Columns: ['id', 'zone_id', 'zone_name', 'timestamp', 'litres']
    Sorted by zone_id and timestamp.
    """
    query = (
        session.query(
            Reading.id,
            Reading.zone_id,
            Zone.name.label("zone_name"),
            Reading.timestamp,
            Reading.litres,
        )
        .join(Zone, Reading.zone_id == Zone.id)
        .order_by(Reading.zone_id, Reading.timestamp)
    )

    rows = query.all()
    if not rows:
        return pd.DataFrame(
            columns=["id", "zone_id", "zone_name", "timestamp", "litres"]
        )

    df = pd.DataFrame(
        [
            {
                "id": r.id,
                "zone_id": r.zone_id,
                "zone_name": r.zone_name,
                "timestamp": pd.to_datetime(r.timestamp),
                "litres": float(r.litres),
            }
            for r in rows
        ]
    )

    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    return df
