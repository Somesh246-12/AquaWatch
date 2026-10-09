"""Tests for AquaWatch Pydantic schemas and data validation rules."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas import (
    ZoneCreate,
    ReadingCreate,
    AlertCreate,
    InjectedAnomalyCreate,
)


def test_zone_schema_validation():
    """Verify zone schema validation rules."""
    # Valid zone
    zone = ZoneCreate(name="Testing Zone", type="test", daily_budget_litres=1000.0)
    assert zone.name == "Testing Zone"
    assert zone.daily_budget_litres == 1000.0

    # Negative budget rejected
    with pytest.raises(ValidationError):
        ZoneCreate(name="Testing Zone", type="test", daily_budget_litres=-500.0)

    # Zero budget rejected
    with pytest.raises(ValidationError):
        ZoneCreate(name="Testing Zone", type="test", daily_budget_litres=0.0)


def test_reading_schema_validation():
    """Verify reading schema validation rules."""
    now = datetime.now(timezone.utc)

    # Valid reading
    reading = ReadingCreate(zone_id=1, timestamp=now, litres=25.5)
    assert reading.litres == 25.5

    # Zero litres is allowed (valid reading when idle)
    zero_reading = ReadingCreate(zone_id=1, timestamp=now, litres=0.0)
    assert zero_reading.litres == 0.0

    # Negative litres must be rejected
    with pytest.raises(ValidationError):
        ReadingCreate(zone_id=1, timestamp=now, litres=-1.0)


def test_alert_schema_validation():
    """Verify alert schema validation rules."""
    now = datetime.now(timezone.utc)

    # Valid alert
    alert = AlertCreate(
        zone_id=1,
        timestamp=now,
        alert_type="leak",
        severity="high",
        message="Pipe pressure dropped abnormally.",
    )
    assert alert.severity == "high"
    assert alert.resolved is False

    # Invalid severity rejected
    with pytest.raises(ValidationError):
        AlertCreate(
            zone_id=1,
            timestamp=now,
            alert_type="leak",
            severity="extreme",  # Not allowed
            message="Test message",
        )

    # Invalid alert_type rejected
    with pytest.raises(ValidationError):
        AlertCreate(
            zone_id=1,
            timestamp=now,
            alert_type="unknown_event",  # Not allowed
            severity="medium",
            message="Test message",
        )


def test_injected_anomaly_schema_validation():
    """Verify ground truth injected anomaly schema validation rules."""
    now = datetime.now(timezone.utc)

    # Valid injected anomaly
    anomaly = InjectedAnomalyCreate(
        zone_id=1,
        timestamp=now,
        anomaly_type="slow_leak",
    )
    assert anomaly.anomaly_type == "slow_leak"

    # Invalid anomaly type rejected
    with pytest.raises(ValidationError):
        InjectedAnomalyCreate(
            zone_id=1,
            timestamp=now,
            anomaly_type="random_tampering",  # Not allowed
        )
