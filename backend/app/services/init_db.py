"""AquaWatch Database Initialization Service.

Handles table creation and idempotent seeding of the five monitoring zones.
"""

import logging
from typing import List, Optional
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import settings
from app.database import Base, engine as default_engine, SessionLocal as default_session_factory
from app.models import Zone, Reading, Alert, InjectedAnomaly

logger = logging.getLogger("aquawatch.init_db")


def init_db(
    engine_override: Optional[Engine] = None,
    session_factory_override: Optional[sessionmaker] = None,
    auto_seed_data: bool = False,
) -> List[Zone]:
    """Idempotently initialize database tables and insert default monitoring zones.

    If tables already exist, this function does not drop or re-create them.
    If default zones already exist, no duplicates are inserted.
    If auto_seed_data is True and the readings table is empty (such as on a fresh cloud deployment),
    it generates the 60-day baseline telemetry and initial detection alerts.

    Args:
        engine_override: Optional SQLAlchemy engine to use (useful for test databases).
        session_factory_override: Optional session factory to use.
        auto_seed_data: If True, populates 60-day baseline data if readings table is empty.

    Returns:
        List of all Zone records present in the database.
    """
    target_engine = engine_override or default_engine
    target_session_factory = session_factory_override or default_session_factory

    logger.info("Creating database tables if not present...")
    Base.metadata.create_all(bind=target_engine)

    session: Session = target_session_factory()
    try:
        existing_zones = session.query(Zone).all()
        existing_names = {z.name for z in existing_zones}

        added_any = False
        for zone_data in settings.DEFAULT_ZONES:
            if zone_data["name"] not in existing_names:
                new_zone = Zone(
                    name=zone_data["name"],
                    type=zone_data["type"],
                    daily_budget_litres=float(zone_data["daily_budget_litres"]),
                )
                session.add(new_zone)
                added_any = True
                logger.info(
                    f"Seeding default zone: {zone_data['name']} "
                    f"({zone_data['daily_budget_litres']} L/day)"
                )

        if added_any:
            session.commit()
            logger.info("Default zones committed successfully.")
        else:
            logger.info("All default zones already exist; skipping insertion.")

        # Fresh cloud deployment auto-seeding (idempotent: only runs if readings table is empty)
        if auto_seed_data:
            reading_count = session.query(Reading).count()
            if reading_count == 0:
                logger.info(
                    "Empty readings table detected on fresh deployment. "
                    "Auto-seeding 60-day baseline telemetry (7,200 readings) and initial alerts..."
                )
                from app.services.simulator import simulate_dataset
                from app.services.detection.evaluator import run_detection_and_persist_alerts

                simulate_dataset(
                    days=60,
                    seed=42,
                    persist=True,
                    session_factory=target_session_factory,
                    engine=target_engine,
                )
                run_detection_and_persist_alerts(session=session)
                logger.info("Auto-seeding completed: 7,200 baseline readings and detection alerts initialized.")
            else:
                logger.info(f"Database already populated ({reading_count} readings); skipping auto-seeding.")

        return session.query(Zone).order_by(Zone.id).all()
    except Exception as exc:
        session.rollback()
        logger.error(f"Error during database initialization: {exc}")
        raise
    finally:
        session.close()
