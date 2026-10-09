"""Tests for AquaWatch database models, relationships, and initialization."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from app.models import Zone, Reading, Alert, InjectedAnomaly
from app.services.init_db import init_db


def test_all_four_tables_created(test_db):
    """1. Verify that all four required tables are created in the database."""
    engine = test_db["engine"]
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    required_tables = ["zones", "readings", "alerts", "injected_anomalies"]
    for table in required_tables:
        assert table in table_names, f"Expected table '{table}' not found in database."


def test_exactly_five_default_zones_exist(test_db):
    """2. Verify that exactly five default zones exist after initialization with correct budgets."""
    session = test_db["session"]
    zones = session.query(Zone).order_by(Zone.id).all()

    assert len(zones) == 5, f"Expected 5 default zones, got {len(zones)}"

    expected_zones = {
        "Household": 1500.0,
        "Hostel Block": 5000.0,
        "Garden": 2500.0,
        "Kitchen": 2000.0,
        "Community Tank": 8000.0,
    }

    zone_map = {z.name: z.daily_budget_litres for z in zones}
    assert set(zone_map.keys()) == set(expected_zones.keys())

    for name, expected_budget in expected_zones.items():
        assert zone_map[name] == expected_budget, (
            f"Budget mismatch for zone '{name}': expected {expected_budget}, got {zone_map[name]}"
        )


def test_zone_names_are_unique(test_db):
    """3. Verify that zone names have a uniqueness constraint."""
    session = test_db["session"]
    duplicate_zone = Zone(
        name="Household",  # Already exists
        type="residential",
        daily_budget_litres=1200.0,
    )
    session.add(duplicate_zone)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_init_db_idempotency_does_not_duplicate_zones(test_db):
    """4. Verify that running initialization multiple times does not duplicate zones."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]

    # Run initialization again
    init_db(engine_override=engine, session_factory_override=session_factory)

    # Check zone count
    session = test_db["session"]
    zones = session.query(Zone).all()
    assert len(zones) == 5


def test_valid_reading_insertion(test_db):
    """5. Verify that a valid reading can be inserted and retrieved."""
    session = test_db["session"]
    zone = session.query(Zone).first()
    now = datetime.now(timezone.utc)

    reading = Reading(zone_id=zone.id, timestamp=now, litres=55.2)
    session.add(reading)
    session.commit()

    retrieved = session.query(Reading).filter_by(id=reading.id).first()
    assert retrieved is not None
    assert retrieved.zone_id == zone.id
    assert retrieved.litres == 55.2


def test_reading_negative_litres_rejected_by_db(test_db):
    """6. Verify that inserting a reading with negative litres fails at the database level."""
    session = test_db["session"]
    zone = session.query(Zone).first()
    now = datetime.now(timezone.utc)

    negative_reading = Reading(zone_id=zone.id, timestamp=now, litres=-10.0)
    session.add(negative_reading)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_reading_referencing_valid_zone_works(test_db):
    """7. Verify that a reading correctly references a valid zone relationship."""
    session = test_db["session"]
    zone = session.query(Zone).filter_by(name="Kitchen").first()
    now = datetime.now(timezone.utc)

    reading = Reading(zone_id=zone.id, timestamp=now, litres=80.0)
    session.add(reading)
    session.commit()

    # Access relationship from both ends
    assert reading.zone.name == "Kitchen"
    assert reading in zone.readings


def test_alert_insertion(test_db):
    """8. Verify that an alert can be inserted and queried."""
    session = test_db["session"]
    zone = session.query(Zone).filter_by(name="Hostel Block").first()
    now = datetime.now(timezone.utc)

    alert = Alert(
        zone_id=zone.id,
        timestamp=now,
        alert_type="leak",
        severity="high",
        message="Suspected continuous night flow leak.",
        resolved=False,
    )
    session.add(alert)
    session.commit()

    retrieved = session.query(Alert).filter_by(id=alert.id).first()
    assert retrieved is not None
    assert retrieved.alert_type == "leak"
    assert retrieved.severity == "high"
    assert retrieved.message == "Suspected continuous night flow leak."


def test_alert_defaults_to_unresolved(test_db):
    """9. Verify that an alert defaults to resolved=False."""
    session = test_db["session"]
    zone = session.query(Zone).first()
    now = datetime.now(timezone.utc)

    alert = Alert(
        zone_id=zone.id,
        timestamp=now,
        alert_type="spike",
        severity="medium",
        message="Sudden consumption burst.",
    )
    session.add(alert)
    session.commit()

    retrieved = session.query(Alert).filter_by(id=alert.id).first()
    assert retrieved.resolved is False


def test_injected_anomaly_insertion(test_db):
    """10. Verify that an injected anomaly (ground truth) can be inserted."""
    session = test_db["session"]
    zone = session.query(Zone).filter_by(name="Garden").first()
    now = datetime.now(timezone.utc)

    anomaly = InjectedAnomaly(
        zone_id=zone.id,
        timestamp=now,
        anomaly_type="slow_leak",
    )
    session.add(anomaly)
    session.commit()

    retrieved = session.query(InjectedAnomaly).filter_by(id=anomaly.id).first()
    assert retrieved is not None
    assert retrieved.anomaly_type == "slow_leak"
    assert retrieved.zone_id == zone.id
    assert retrieved.zone.name == "Garden"


def test_foreign_key_enforcement(test_db):
    """11. Verify that foreign key constraints prevent inserting child records with invalid zone_id."""
    session = test_db["session"]
    invalid_zone_id = 99999
    now = datetime.now(timezone.utc)

    # Reading with non-existent zone
    reading = Reading(zone_id=invalid_zone_id, timestamp=now, litres=25.0)
    session.add(reading)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Alert with non-existent zone
    alert = Alert(
        zone_id=invalid_zone_id,
        timestamp=now,
        alert_type="leak",
        severity="low",
        message="Test alert",
    )
    session.add(alert)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Anomaly with non-existent zone
    anomaly = InjectedAnomaly(
        zone_id=invalid_zone_id,
        timestamp=now,
        anomaly_type="burst",
    )
    session.add(anomaly)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
