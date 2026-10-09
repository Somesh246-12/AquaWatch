"""AquaWatch Deterministic Water Consumption Simulator.

Generates 60 days of realistic hourly water consumption readings across five zones
using diurnal consumption curves, weekend multipliers, random variation, and
injects 10 ground-truth anomaly events (4 slow leaks, 3 bursts, 3 wastage days).
"""

import csv
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import random
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import (
    engine as default_engine,
    SessionLocal as default_session_factory,
)
from app.models import Zone, Reading, InjectedAnomaly
from app.services.init_db import init_db

logger = logging.getLogger("aquawatch.simulator")

# Fixed default simulation start date to ensure cross-run determinism
DEFAULT_SIMULATION_START = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)

# 24-hour diurnal profiles (litres/hour) calibrated to daily budgets
# Hours: 00 to 23
HOUSEHOLD_HOURLY = [
    1.0, 0.8, 0.7, 0.8, 1.2, 5.0,        # 00-05 Night (0-2 L/h)
    110.0, 145.0, 130.0,                 # 06-08 Morning Peak (6-9 AM)
    60.0, 45.0, 40.0, 50.0, 45.0,        # 09-13 Midday
    40.0, 45.0, 60.0, 95.0,              # 14-17 Late Afternoon
    140.0, 155.0, 130.0,                 # 18-20 Evening Peak (6-9 PM)
    65.0, 40.0, 15.0                     # 21-23 Late Evening
]

HOSTEL_HOURLY = [
    1.5, 1.0, 0.9, 1.0, 1.5, 15.0,       # 00-05 Night
    420.0, 520.0, 460.0,                 # 06-08 Morning Peak
    250.0, 190.0, 180.0, 220.0, 200.0,   # 09-13 Midday
    180.0, 170.0, 210.0, 310.0,          # 14-17 Afternoon
    480.0, 540.0, 460.0,                 # 18-20 Evening Peak
    240.0, 140.0, 40.0                   # 21-23 Late Evening
]

GARDEN_HOURLY = [
    0.5, 0.4, 0.4, 0.4, 0.5, 5.0,        # 00-05 Night
    380.0, 450.0, 350.0,                 # 06-08 Morning Irrigation Peak
    40.0, 15.0, 10.0, 10.0, 10.0,        # 09-13 Minimal Midday Watering
    10.0, 15.0, 35.0,                    # 14-16 Afternoon
    360.0, 420.0, 310.0,                 # 17-19 Evening Irrigation Peak
    40.0, 20.0, 10.0, 2.0                # 20-23 Late Evening
]

KITCHEN_HOURLY = [
    0.8, 0.5, 0.5, 0.5, 1.0, 10.0,       # 00-05 Night
    120.0, 160.0, 140.0,                 # 06-08 Breakfast Service Peak
    110.0, 130.0, 160.0, 140.0, 80.0,    # 09-13 Lunch Service & Prep
    50.0, 60.0, 110.0, 150.0,            # 14-17 Afternoon Prep
    170.0, 160.0, 120.0,                 # 18-20 Dinner Service Peak
    60.0, 30.0, 10.0                     # 21-23 Cleaning & Shutdown
]

TANK_HOURLY = [
    2.0, 1.2, 1.0, 1.1, 2.5, 40.0,       # 00-05 Night
    620.0, 780.0, 690.0,                 # 06-08 Morning Peak
    420.0, 360.0, 350.0, 390.0, 370.0,   # 09-13 Steady Distribution
    340.0, 350.0, 410.0, 540.0,          # 14-17 Afternoon
    720.0, 790.0, 660.0,                 # 18-20 Evening Peak
    410.0, 220.0, 80.0                   # 21-23 Night Descent
]

ZONE_HOURLY_BASELINES: Dict[str, List[float]] = {
    "Household": HOUSEHOLD_HOURLY,
    "Hostel Block": HOSTEL_HOURLY,
    "Garden": GARDEN_HOURLY,
    "Kitchen": KITCHEN_HOURLY,
    "Community Tank": TANK_HOURLY,
}

for _zone_k, _prof in ZONE_HOURLY_BASELINES.items():
    assert len(_prof) == 24, f"Baseline profile for '{_zone_k}' must contain exactly 24 hours, got {len(_prof)}"

# Specification of exactly 10 anomaly events (4 slow leaks, 3 bursts, 3 wastage days)
ANOMALY_DEFINITIONS: List[Dict[str, Any]] = [
    # 4 Slow Leaks (continuous night flow > 3 L/h between 1 AM and 4 AM)
    {
        "zone_name": "Household",
        "day": 8,
        "start_hour": 1,
        "duration_hours": 4,  # hours 1, 2, 3, 4
        "anomaly_type": "slow_leak",
        "leak_additive": 11.5,
    },
    {
        "zone_name": "Kitchen",
        "day": 24,
        "start_hour": 1,
        "duration_hours": 4,  # hours 1, 2, 3, 4
        "anomaly_type": "slow_leak",
        "leak_additive": 10.0,
    },
    {
        "zone_name": "Hostel Block",
        "day": 36,
        "start_hour": 1,
        "duration_hours": 4,  # hours 1, 2, 3, 4
        "anomaly_type": "slow_leak",
        "leak_additive": 12.5,
    },
    {
        "zone_name": "Garden",
        "day": 51,
        "start_hour": 1,
        "duration_hours": 4,  # hours 1, 2, 3, 4
        "anomaly_type": "slow_leak",
        "leak_additive": 11.0,
    },
    # 3 Bursts (sudden multi-fold consumption spikes lasting 1-3 hours)
    {
        "zone_name": "Hostel Block",
        "day": 14,
        "start_hour": 14,
        "duration_hours": 2,  # hours 14, 15
        "anomaly_type": "burst",
        "burst_additive": 850.0,
    },
    {
        "zone_name": "Community Tank",
        "day": 31,
        "start_hour": 10,
        "duration_hours": 2,  # hours 10, 11
        "anomaly_type": "burst",
        "burst_additive": 1900.0,
    },
    {
        "zone_name": "Household",
        "day": 47,
        "start_hour": 19,
        "duration_hours": 2,  # hours 19, 20
        "anomaly_type": "burst",
        "burst_additive": 650.0,
    },
    # 3 Wastage Days (approximately 2x elevated usage across substantial daytime hours)
    {
        "zone_name": "Garden",
        "day": 19,
        "start_hour": 6,
        "duration_hours": 16,  # hours 6 to 21
        "anomaly_type": "wastage_day",
        "wastage_multiplier": 2.10,
    },
    {
        "zone_name": "Household",
        "day": 41,
        "start_hour": 6,
        "duration_hours": 16,  # hours 6 to 21
        "anomaly_type": "wastage_day",
        "wastage_multiplier": 2.05,
    },
    {
        "zone_name": "Community Tank",
        "day": 55,
        "start_hour": 6,
        "duration_hours": 16,  # hours 6 to 21
        "anomaly_type": "wastage_day",
        "wastage_multiplier": 1.95,
    },
]


def reset_simulation_data(
    session: Optional[Session] = None,
    engine_to_use: Optional[Engine] = None,
    session_factory: Optional[sessionmaker] = None,
) -> Dict[str, int]:
    """Safely reset simulated readings and injected anomalies without modifying zones.

    Args:
        session: Active SQLAlchemy session if provided.
        engine_to_use: SQLAlchemy engine to use if session is None.
        session_factory: Session maker to use if session is None.

    Returns:
        Dict with count of deleted readings and deleted injected anomalies.
    """
    should_close = False
    if session is None:
        target_factory = session_factory or (
            sessionmaker(autocommit=False, autoflush=False, bind=engine_to_use)
            if engine_to_use
            else default_session_factory
        )
        session = target_factory()
        should_close = True

    try:
        deleted_readings = session.query(Reading).delete()
        deleted_anomalies = session.query(InjectedAnomaly).delete()
        session.commit()
        logger.info(
            f"Reset simulation data: deleted {deleted_readings} readings, "
            f"{deleted_anomalies} anomalies."
        )
        return {
            "deleted_readings": deleted_readings,
            "deleted_anomalies": deleted_anomalies,
        }
    except Exception as exc:
        session.rollback()
        logger.error(f"Failed to reset simulation data: {exc}")
        raise
    finally:
        if should_close:
            session.close()


def simulate_dataset(
    days: int = 60,
    seed: int = 42,
    persist: bool = True,
    session_factory: Optional[sessionmaker] = None,
    engine: Optional[Engine] = None,
    start_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate deterministic water consumption readings and inject ground-truth anomalies.

    Args:
        days: Number of simulation days (default: 60).
        seed: Random seed for deterministic reproducibility (default: 42).
        persist: Whether to commit records to SQLite database (default: True).
        session_factory: Optional custom sessionmaker.
        engine: Optional custom SQLAlchemy engine.
        start_date: Fixed starting timestamp for the simulation.

    Returns:
        Summary dict containing generation metrics and counts.
    """
    target_engine = engine or default_engine
    target_factory = session_factory or (
        sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
        if engine
        else default_session_factory
    )

    # Ensure tables exist and default zones are present
    init_db(engine_override=target_engine, session_factory_override=target_factory)

    session: Session = target_factory()
    try:
        # Load zones
        zones = session.query(Zone).order_by(Zone.id).all()
        if not zones:
            raise RuntimeError("No zones found in database. Initialization required.")

        zone_by_name = {z.name: z for z in zones}

        # Reset any prior simulation data before inserting
        reset_simulation_data(session=session)

        # Initialize deterministic pseudo-random generator
        rng = random.Random(seed)
        sim_start = start_date or DEFAULT_SIMULATION_START

        # Build lookup for active anomaly injections: (zone_name, day, hour) -> anomaly_def
        anomaly_hour_map: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
        ground_truth_records: List[InjectedAnomaly] = []

        for anomaly_def in ANOMALY_DEFINITIONS:
            # Check if event falls within simulated days
            if anomaly_def["day"] < days:
                zone_name = anomaly_def["zone_name"]
                zone = zone_by_name.get(zone_name)
                if not zone:
                    continue

                event_timestamp = sim_start + timedelta(
                    days=anomaly_def["day"], hours=anomaly_def["start_hour"]
                )

                # Record 1 ground-truth event in injected_anomalies
                ground_truth_records.append(
                    InjectedAnomaly(
                        zone_id=zone.id,
                        timestamp=event_timestamp,
                        anomaly_type=anomaly_def["anomaly_type"],
                    )
                )

                # Map all affected hours for flow modification
                for h_offset in range(anomaly_def["duration_hours"]):
                    target_hour = anomaly_def["start_hour"] + h_offset
                    anomaly_hour_map[(zone_name, anomaly_def["day"], target_hour)] = anomaly_def

        readings_to_insert: List[Reading] = []

        # Generate hourly readings for each zone
        for day_idx in range(days):
            for hour_idx in range(24):
                current_time = sim_start + timedelta(days=day_idx, hours=hour_idx)
                is_weekend = current_time.weekday() >= 5
                weekend_mult = 1.20 if is_weekend else 1.0

                for zone in zones:
                    baseline_profile = ZONE_HOURLY_BASELINES.get(
                        zone.name, HOUSEHOLD_HOURLY
                    )
                    base_litres = baseline_profile[hour_idx] * weekend_mult

                    # Small deterministic noise
                    if hour_idx in (0, 1, 2, 3, 4):
                        # Night hours: minimal variance (0 to 2 L/h)
                        noise = rng.uniform(-0.15, 0.15)
                        litres = max(0.1, base_litres + noise)
                    else:
                        # Daytime / evening hours: proportional variance (~4%)
                        noise = rng.gauss(0.0, max(1.0, base_litres * 0.04))
                        litres = max(0.0, base_litres + noise)

                    # Check for injected anomaly modification
                    anomaly_hit = anomaly_hour_map.get((zone.name, day_idx, hour_idx))
                    if anomaly_hit:
                        atype = anomaly_hit["anomaly_type"]
                        if atype == "slow_leak":
                            litres += anomaly_hit["leak_additive"]
                        elif atype == "burst":
                            litres += anomaly_hit["burst_additive"]
                        elif atype == "wastage_day":
                            litres *= anomaly_hit["wastage_multiplier"]

                    litres = round(max(0.0, litres), 2)

                    readings_to_insert.append(
                        Reading(
                            zone_id=zone.id,
                            timestamp=current_time,
                            litres=litres,
                        )
                    )

        if persist:
            # Batch insertion for optimal SQLite performance
            session.add_all(ground_truth_records)
            session.add_all(readings_to_insert)
            session.commit()
            logger.info(
                f"Successfully persisted {len(readings_to_insert)} readings and "
                f"{len(ground_truth_records)} injected anomalies to database."
            )

        summary = get_simulation_summary(session=session)
        return summary
    except Exception as exc:
        session.rollback()
        logger.error(f"Failed during dataset simulation: {exc}")
        raise
    finally:
        session.close()


def get_simulation_summary(
    session: Optional[Session] = None,
    engine_to_use: Optional[Engine] = None,
    session_factory: Optional[sessionmaker] = None,
) -> Dict[str, Any]:
    """Calculates simulation metrics dynamically from the actual database records.

    Returns:
        Structured dictionary with counts, min/max/avg consumption, and anomaly counts.
    """
    should_close = False
    if session is None:
        target_factory = session_factory or (
            sessionmaker(autocommit=False, autoflush=False, bind=engine_to_use)
            if engine_to_use
            else default_session_factory
        )
        session = target_factory()
        should_close = True

    try:
        total_zones = session.query(func.count(Zone.id)).scalar() or 0
        total_readings = session.query(func.count(Reading.id)).scalar() or 0

        # Readings per zone breakdown
        zone_counts = (
            session.query(Zone.name, func.count(Reading.id))
            .join(Reading, Zone.id == Reading.zone_id)
            .group_by(Zone.name)
            .all()
        )
        readings_per_zone = {name: count for name, count in zone_counts}

        # Min, Max, Average litres
        stats = session.query(
            func.min(Reading.litres),
            func.max(Reading.litres),
            func.avg(Reading.litres),
        ).first()

        min_litres = round(float(stats[0]), 2) if stats and stats[0] is not None else 0.0
        max_litres = round(float(stats[1]), 2) if stats and stats[1] is not None else 0.0
        avg_litres = round(float(stats[2]), 2) if stats and stats[2] is not None else 0.0

        # Anomaly counts
        slow_leaks = (
            session.query(func.count(InjectedAnomaly.id))
            .filter(InjectedAnomaly.anomaly_type == "slow_leak")
            .scalar()
            or 0
        )
        bursts = (
            session.query(func.count(InjectedAnomaly.id))
            .filter(InjectedAnomaly.anomaly_type == "burst")
            .scalar()
            or 0
        )
        wastage_days = (
            session.query(func.count(InjectedAnomaly.id))
            .filter(InjectedAnomaly.anomaly_type == "wastage_day")
            .scalar()
            or 0
        )

        # Days covered
        days = total_readings // (24 * total_zones) if total_zones > 0 else 0

        return {
            "zones_count": total_zones,
            "days_count": days,
            "total_readings": total_readings,
            "readings_per_zone": readings_per_zone,
            "min_litres": min_litres,
            "max_litres": max_litres,
            "avg_litres": avg_litres,
            "slow_leaks_count": slow_leaks,
            "bursts_count": bursts,
            "wastage_days_count": wastage_days,
            "total_anomalies_count": slow_leaks + bursts + wastage_days,
        }
    finally:
        if should_close:
            session.close()


def export_readings_to_csv(
    output_path: str = "data/readings.csv",
    session: Optional[Session] = None,
    engine_to_use: Optional[Engine] = None,
    session_factory: Optional[sessionmaker] = None,
) -> str:
    """Export time-series readings from database to CSV.

    Args:
        output_path: Target destination path for CSV.
        session: Active SQLAlchemy session if provided.
        engine_to_use: SQLAlchemy engine to use if session is None.
        session_factory: Session maker to use if session is None.

    Returns:
        Absolute string path of the generated CSV file.
    """
    should_close = False
    if session is None:
        target_factory = session_factory or (
            sessionmaker(autocommit=False, autoflush=False, bind=engine_to_use)
            if engine_to_use
            else default_session_factory
        )
        session = target_factory()
        should_close = True

    try:
        csv_file = Path(output_path).resolve()
        csv_file.parent.mkdir(parents=True, exist_ok=True)

        query = (
            session.query(
                Reading.zone_id,
                Zone.name.label("zone_name"),
                Reading.timestamp,
                Reading.litres,
            )
            .join(Zone, Reading.zone_id == Zone.id)
            .order_by(Reading.timestamp, Reading.zone_id)
        )

        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["zone_id", "zone_name", "timestamp", "litres"])

            for row in query.yield_per(1000):
                writer.writerow([
                    row.zone_id,
                    row.zone_name,
                    row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                    row.litres,
                ])

        logger.info(f"Readings exported to CSV at: {csv_file}")
        return str(csv_file)
    finally:
        if should_close:
            session.close()
