"""Tests for AquaWatch deterministic water consumption simulator."""

from datetime import timedelta
import os
from pathlib import Path
import pytest
from sqlalchemy import func
from app.models import Zone, Reading, InjectedAnomaly
from app.services.simulator import (
    simulate_dataset,
    reset_simulation_data,
    get_simulation_summary,
    export_readings_to_csv,
    DEFAULT_SIMULATION_START,
)


@pytest.fixture
def populated_sim_db(test_db):
    """Provides a test database pre-populated with the 60-day deterministic simulation."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]
    simulate_dataset(
        days=60,
        seed=42,
        persist=True,
        engine=engine,
        session_factory=session_factory,
    )
    return test_db


def test_simulator_creates_7200_readings(populated_sim_db):
    """1. Verify simulator creates exactly 7,200 readings (60 days * 24 hrs * 5 zones)."""
    session = populated_sim_db["session"]
    total = session.query(func.count(Reading.id)).scalar()
    assert total == 7200


def test_simulator_five_zones_represented(populated_sim_db):
    """2. Verify that exactly 5 zones are represented in the readings."""
    session = populated_sim_db["session"]
    distinct_zones = session.query(Reading.zone_id).distinct().count()
    assert distinct_zones == 5


def test_each_zone_has_1440_readings(populated_sim_db):
    """3. Verify that each zone has exactly 1,440 readings (60 days * 24 hrs)."""
    session = populated_sim_db["session"]
    zones = session.query(Zone).all()
    for zone in zones:
        zone_readings = (
            session.query(func.count(Reading.id))
            .filter(Reading.zone_id == zone.id)
            .scalar()
        )
        assert zone_readings == 1440, f"Zone {zone.name} has {zone_readings} readings, expected 1440"


def test_simulation_duration_covers_60_days(populated_sim_db):
    """4. Verify that the simulation covers exactly 60 distinct calendar days."""
    session = populated_sim_db["session"]
    min_time = session.query(func.min(Reading.timestamp)).scalar()
    max_time = session.query(func.max(Reading.timestamp)).scalar()

    # In Python/SQLite, min_time to max_time spans 59 days and 23 hours = 1,439 hours delta (1,440 hourly points)
    hours_diff = (max_time - min_time).total_seconds() / 3600.0
    assert hours_diff == 1439.0
    # Exactly 60 calendar days represented
    distinct_dates = session.query(func.date(Reading.timestamp)).distinct().count()
    assert distinct_dates == 60


def test_seed_42_deterministic_results(test_db):
    """5. Verify that seed 42 produces identical readings across independent runs."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]
    session = test_db["session"]

    # Run 1
    simulate_dataset(days=10, seed=42, engine=engine, session_factory=session_factory)
    readings_run1 = [r.litres for r in session.query(Reading).order_by(Reading.id).all()]

    # Run 2
    simulate_dataset(days=10, seed=42, engine=engine, session_factory=session_factory)
    readings_run2 = [r.litres for r in session.query(Reading).order_by(Reading.id).all()]

    assert len(readings_run1) == len(readings_run2)
    assert readings_run1 == readings_run2


def test_reset_and_rerun_identical_anomalies(test_db):
    """6. Verify that running reset and re-simulating produces identical anomaly records."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]
    session = test_db["session"]

    simulate_dataset(days=60, seed=42, engine=engine, session_factory=session_factory)
    anomalies_1 = [
        (a.zone_id, str(a.timestamp), a.anomaly_type)
        for a in session.query(InjectedAnomaly).order_by(InjectedAnomaly.id).all()
    ]

    reset_simulation_data(session=session)
    simulate_dataset(days=60, seed=42, engine=engine, session_factory=session_factory)
    anomalies_2 = [
        (a.zone_id, str(a.timestamp), a.anomaly_type)
        for a in session.query(InjectedAnomaly).order_by(InjectedAnomaly.id).all()
    ]

    assert anomalies_1 == anomalies_2


def test_exactly_four_slow_leaks_injected(populated_sim_db):
    """7. Verify exactly 4 slow leaks are injected into the ground-truth table."""
    session = populated_sim_db["session"]
    slow_leaks = (
        session.query(InjectedAnomaly)
        .filter(InjectedAnomaly.anomaly_type == "slow_leak")
        .count()
    )
    assert slow_leaks == 4


def test_exactly_three_bursts_injected(populated_sim_db):
    """8. Verify exactly 3 bursts are injected into the ground-truth table."""
    session = populated_sim_db["session"]
    bursts = (
        session.query(InjectedAnomaly)
        .filter(InjectedAnomaly.anomaly_type == "burst")
        .count()
    )
    assert bursts == 3


def test_exactly_three_wastage_days_injected(populated_sim_db):
    """9. Verify exactly 3 wastage days are injected into the ground-truth table."""
    session = populated_sim_db["session"]
    wastage = (
        session.query(InjectedAnomaly)
        .filter(InjectedAnomaly.anomaly_type == "wastage_day")
        .count()
    )
    assert wastage == 3


def test_total_ground_truth_anomaly_events_is_ten(populated_sim_db):
    """10. Verify total ground-truth anomaly events count is exactly 10."""
    session = populated_sim_db["session"]
    total = session.query(func.count(InjectedAnomaly.id)).scalar()
    assert total == 10


def test_no_negative_litres(populated_sim_db):
    """11. Verify that no generated consumption reading has negative litres."""
    session = populated_sim_db["session"]
    negatives = session.query(Reading).filter(Reading.litres < 0).count()
    assert negatives == 0


def test_normal_night_readings_are_low(populated_sim_db):
    """12. Verify normal night readings (1 AM to 4 AM) are generally low (< 2.5 L/hr)."""
    session = populated_sim_db["session"]
    # Days with slow leaks: 8, 24, 36, 51 (filter out these specific leak days)
    leak_days = {8, 24, 36, 51}
    leak_dates = [
        (DEFAULT_SIMULATION_START + timedelta(days=d)).date().isoformat()
        for d in leak_days
    ]

    normal_night_readings = (
        session.query(Reading.litres)
        .filter(func.strftime("%H", Reading.timestamp).in_(["01", "02", "03", "04"]))
        .filter(~func.date(Reading.timestamp).in_(leak_dates))
        .all()
    )

    avg_night_flow = sum(r[0] for r in normal_night_readings) / len(normal_night_readings)
    # Average normal night flow should be approx 0.5 to 1.5 L/h, well below 2.5 L/h
    assert avg_night_flow < 2.5, f"Normal night flow average was {avg_night_flow:.2f} L/h, expected < 2.5"


def test_morning_and_evening_usage_higher_than_night(populated_sim_db):
    """13. Verify peak morning/evening hours have higher consumption than night hours."""
    session = populated_sim_db["session"]
    # Household zone
    household = session.query(Zone).filter_by(name="Household").first()

    avg_night = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == household.id)
        .filter(func.strftime("%H", Reading.timestamp).in_(["01", "02", "03", "04"]))
        .scalar()
    )

    avg_morning = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == household.id)
        .filter(func.strftime("%H", Reading.timestamp).in_(["06", "07", "08"]))
        .scalar()
    )

    avg_evening = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == household.id)
        .filter(func.strftime("%H", Reading.timestamp).in_(["18", "19", "20"]))
        .scalar()
    )

    assert avg_morning > avg_night * 10
    assert avg_evening > avg_night * 10


def test_weekend_usage_approximately_higher_than_weekday(populated_sim_db):
    """14. Verify weekend consumption is approximately 20% higher than weekday consumption."""
    session = populated_sim_db["session"]
    household = session.query(Zone).filter_by(name="Household").first()

    # Exclude wastage day (Day 41) for pure comparison
    wastage_date = (DEFAULT_SIMULATION_START + timedelta(days=41)).date().isoformat()

    # strftime %w: 0=Sunday, 6=Saturday
    weekday_avg = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == household.id)
        .filter(~func.strftime("%w", Reading.timestamp).in_(["0", "6"]))
        .filter(func.date(Reading.timestamp) != wastage_date)
        .scalar()
    )

    weekend_avg = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == household.id)
        .filter(func.strftime("%w", Reading.timestamp).in_(["0", "6"]))
        .filter(func.date(Reading.timestamp) != wastage_date)
        .scalar()
    )

    ratio = weekend_avg / weekday_avg
    # Expected approx 1.20 (between 1.12 and 1.28)
    assert 1.12 <= ratio <= 1.28, f"Weekend/Weekday ratio was {ratio:.3f}, expected ~1.20"


def test_garden_shows_stronger_morning_evening_irrigation(populated_sim_db):
    """15. Verify Garden exhibits high morning/evening irrigation and low midday usage."""
    session = populated_sim_db["session"]
    garden = session.query(Zone).filter_by(name="Garden").first()

    # Midday hours (10 AM to 2 PM)
    avg_midday = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == garden.id)
        .filter(func.strftime("%H", Reading.timestamp).in_(["10", "11", "12", "13"]))
        .scalar()
    )

    # Morning irrigation (6 AM to 8 AM)
    avg_morning = (
        session.query(func.avg(Reading.litres))
        .filter(Reading.zone_id == garden.id)
        .filter(func.strftime("%H", Reading.timestamp).in_(["06", "07", "08"]))
        .scalar()
    )

    # Morning irrigation should be at least 10x higher than midday lull
    assert avg_morning > avg_midday * 10


def test_simulator_does_not_create_duplicate_anomalies(populated_sim_db):
    """16. Verify running the simulator again does not create duplicate anomaly records."""
    engine = populated_sim_db["engine"]
    session_factory = populated_sim_db["session_factory"]
    session = populated_sim_db["session"]

    simulate_dataset(days=60, seed=42, engine=engine, session_factory=session_factory)
    total_anomalies = session.query(func.count(InjectedAnomaly.id)).scalar()
    assert total_anomalies == 10


def test_reset_preserves_zones(populated_sim_db):
    """17. Verify that reset deletes readings and anomalies while keeping zones intact."""
    session = populated_sim_db["session"]

    res = reset_simulation_data(session=session)
    assert res["deleted_readings"] == 7200
    assert res["deleted_anomalies"] == 10

    # Zones must remain exactly 5
    zones_count = session.query(func.count(Zone.id)).scalar()
    assert zones_count == 5


def test_csv_export_contains_expected_rows(populated_sim_db, tmp_path):
    """18. Verify that CSV export produces exactly 7,201 lines (1 header + 7,200 readings)."""
    session = populated_sim_db["session"]
    csv_file = tmp_path / "readings_test.csv"

    exported_path = export_readings_to_csv(output_path=str(csv_file), session=session)
    assert Path(exported_path).exists()

    with open(exported_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 7201
    assert lines[0].strip() == "zone_id,zone_name,timestamp,litres"
