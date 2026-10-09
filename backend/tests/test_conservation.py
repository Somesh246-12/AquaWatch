"""AquaWatch Conservation Intelligence Tests (Task 6).

Verifies:
- Water-budget status calculations (<80%, exactly 80%, 80-100%, exactly 100%, >100%)
- Zero and missing readings safety
- Multi-zone and historical date selection
- Data-driven conservation recommendations (leak repairs, budget exceeded, budget warning, top consumer, general tip)
- Duplicate recommendation prevention
- Savings estimator formulas, configurable tariffs, configurable leak durations
- Graceful handling of missing flow metadata (explicitly unavailable)
- Parameter validation (tariffs, leak hours, dates)
- Alert count decomposition (candidate detections vs newly created vs existing duplicates)
"""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.alert import Alert
from app.models.reading import Reading
from app.models.zone import Zone
from app.services.simulator import simulate_dataset


@pytest.fixture
def client_with_db(test_db):
    """Provides a TestClient with get_db dependency overridden to the test SQLite database."""
    session_factory = test_db["session_factory"]

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, test_db["session_factory"]
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_sim_dataset(test_db):
    """Provides a TestClient with full 60-day simulated dataset seeded in test database."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]
    simulate_dataset(days=60, seed=42, persist=True, engine=engine, session_factory=session_factory)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()


# ==============================================================================
# 1. WATER BUDGET SERVICE TESTS
# ==============================================================================

def test_budget_status_below_80_percent(client_with_db):
    """1. Consumption below 80% yields status 'normal' and is_exceeded=False."""
    client, session_factory = client_with_db
    db = session_factory()
    # Zone 1 (Household) has budget 1500.0 L. 79% = 1185.0 L.
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=1185.0))
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    assert z1["consumed_percent"] == 79.0
    assert z1["status"] == "normal"
    assert z1["is_exceeded"] is False
    assert z1["remaining_budget_litres"] == 315.0


def test_budget_status_exactly_80_percent(client_with_db):
    """2. Consumption at exactly 80.0% yields status 'warning' and is_exceeded=False."""
    client, session_factory = client_with_db
    db = session_factory()
    # Zone 1 budget 1500.0 L. Exactly 80% = 1200.0 L.
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=1200.0))
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    assert z1["consumed_percent"] == 80.0
    assert z1["status"] == "warning"
    assert z1["is_exceeded"] is False
    assert z1["remaining_budget_litres"] == 300.0


def test_budget_status_between_80_and_100_percent(client_with_db):
    """3. Consumption between 80% and 100% yields status 'warning'."""
    client, session_factory = client_with_db
    db = session_factory()
    # Zone 1 budget 1500.0 L. 90% = 1350.0 L.
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=1350.0))
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    assert z1["consumed_percent"] == 90.0
    assert z1["status"] == "warning"
    assert z1["is_exceeded"] is False
    assert z1["remaining_budget_litres"] == 150.0


def test_budget_status_exactly_100_percent(client_with_db):
    """4. Consumption at exactly 100.0% yields status 'exceeded' and is_exceeded=True."""
    client, session_factory = client_with_db
    db = session_factory()
    # Zone 1 budget 1500.0 L. Exactly 100% = 1500.0 L.
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=1500.0))
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    assert z1["consumed_percent"] == 100.0
    assert z1["status"] == "exceeded"
    assert z1["is_exceeded"] is True
    assert z1["remaining_budget_litres"] == 0.0


def test_budget_status_above_100_percent(client_with_db):
    """5. Consumption above 100.0% yields status 'exceeded' and negative remaining budget."""
    client, session_factory = client_with_db
    db = session_factory()
    # Zone 1 budget 1500.0 L. 120% = 1800.0 L.
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=1800.0))
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    assert z1["consumed_percent"] == 120.0
    assert z1["status"] == "exceeded"
    assert z1["is_exceeded"] is True
    assert z1["remaining_budget_litres"] == -300.0


def test_budget_zero_readings_safe(client_with_db):
    """6. Zones with zero consumption on target date return status 'normal' safely."""
    client, _ = client_with_db
    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    assert data["total_actual_litres"] == 0.0
    assert data["overall_consumed_percent"] == 0.0
    assert data["overall_status"] == "normal"
    for z in data["zones"]:
        assert z["actual_consumption_litres"] == 0.0
        assert z["consumed_percent"] == 0.0
        assert z["status"] == "normal"
        assert z["is_exceeded"] is False
        assert z["remaining_budget_litres"] == z["daily_budget_litres"]


def test_budget_missing_readings_and_multiple_zones(client_with_db):
    """7. Handles multiple zones with uneven readings across historical dates."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=500.0))
    db.add(Reading(zone_id=2, timestamp=t, litres=4500.0))  # 90% of 5000 -> warning
    db.add(Reading(zone_id=4, timestamp=t, litres=2500.0))  # 125% of 2000 -> exceeded
    # Zones 3 and 5 have 0 readings
    db.commit()
    db.close()

    response = client.get("/conservation/budgets?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    assert len(data["zones"]) == 5

    z1 = next(z for z in data["zones"] if z["zone_id"] == 1)
    z2 = next(z for z in data["zones"] if z["zone_id"] == 2)
    z3 = next(z for z in data["zones"] if z["zone_id"] == 3)
    z4 = next(z for z in data["zones"] if z["zone_id"] == 4)

    assert z1["status"] == "normal"
    assert z2["status"] == "warning"
    assert z3["status"] == "normal"
    assert z4["status"] == "exceeded"


def test_budget_historical_date_selection(client_with_db):
    """8. Historical date query parameter retrieves the correct date's data."""
    client, session_factory = client_with_db
    db = session_factory()
    t_aug = datetime(2026, 8, 15, 12, 0, 0)
    t_sep = datetime(2026, 9, 15, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t_aug, litres=300.0))
    db.add(Reading(zone_id=1, timestamp=t_sep, litres=800.0))
    db.commit()
    db.close()

    res_aug = client.get("/conservation/budgets?date=2026-08-15")
    assert res_aug.status_code == 200
    data_aug = res_aug.json()
    assert data_aug["date"] == "2026-08-15"
    z_aug = next(z for z in data_aug["zones"] if z["zone_id"] == 1)
    assert z_aug["actual_consumption_litres"] == 300.0

    res_sep = client.get("/conservation/budgets?date=2026-09-15")
    assert res_sep.status_code == 200
    data_sep = res_sep.json()
    assert data_sep["date"] == "2026-09-15"
    z_sep = next(z for z in data_sep["zones"] if z["zone_id"] == 1)
    assert z_sep["actual_consumption_litres"] == 800.0


def test_budget_invalid_date_format_rejected(client_with_db):
    """9. Rejects invalid date strings with 400 Bad Request."""
    client, _ = client_with_db
    response = client.get("/conservation/budgets?date=invalid-date")
    assert response.status_code == 400
    assert "invalid date format" in response.json()["detail"].lower()


# ==============================================================================
# 2. CONSERVATION RECOMMENDATIONS (TIPS) TESTS
# ==============================================================================

def test_recommendation_leak_based(client_with_db):
    """10. Unresolved leak alerts produce urgent leak repair recommendations."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 2, 0, 0)
    db.add(
        Alert(
            zone_id=1,
            timestamp=t,
            alert_type="leak",
            severity="high",
            message="Continuous night leak detected in Household: average flow of 4.5 L/h.",
            resolved=False,
        )
    )
    db.commit()
    db.close()

    response = client.get("/conservation/tips?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]
    assert any(r["category"] == "leak_repair" and r["zone_id"] == 1 and r["priority"] == "critical" for r in recs)


def test_recommendation_budget_based(client_with_db):
    """11. Exceeded budgets produce high priority curtailment recommendations."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 12, 0, 0)
    # Zone 1 budget 1500 -> 1800 L (exceeded)
    # Zone 2 budget 5000 -> 4500 L (warning)
    db.add(Reading(zone_id=1, timestamp=t, litres=1800.0))
    db.add(Reading(zone_id=2, timestamp=t, litres=4500.0))
    db.commit()
    db.close()

    response = client.get("/conservation/tips?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]

    assert any(r["category"] == "budget_exceeded" and r["zone_id"] == 1 and r["priority"] == "high" for r in recs)
    assert any(r["category"] == "budget_warning" and r["zone_id"] == 2 and r["priority"] == "medium" for r in recs)


def test_recommendation_general_tip_when_no_alerts(client_with_db):
    """12. Clean system with no leaks or over-budget conditions provides general tip."""
    client, session_factory = client_with_db
    db = session_factory()
    # Readings well below budget (<80%)
    t = datetime(2026, 9, 1, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=100.0))
    db.commit()
    db.close()

    response = client.get("/conservation/tips?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]
    # Should include high_consumption or general_tip
    assert len(recs) >= 1
    assert not any(r["category"] in ("leak_repair", "budget_exceeded") for r in recs)


def test_recommendations_no_duplicates(client_with_db):
    """13. Recommendations list contains unique stable IDs without duplicate entries."""
    client, session_factory = client_with_db
    db = session_factory()
    t1 = datetime(2026, 9, 1, 2, 0, 0)
    t2 = datetime(2026, 9, 1, 3, 0, 0)
    # 2 alerts in same zone
    db.add(Alert(zone_id=1, timestamp=t1, alert_type="leak", severity="high", message="Leak 1", resolved=False))
    db.add(Alert(zone_id=1, timestamp=t2, alert_type="leak", severity="medium", message="Leak 2", resolved=False))
    db.commit()
    db.close()

    response = client.get("/conservation/tips?date=2026-09-01")
    assert response.status_code == 200
    data = response.json()
    rec_ids = [r["id"] for r in data["recommendations"]]
    assert len(rec_ids) == len(set(rec_ids)), "Duplicate recommendation IDs found!"


# ==============================================================================
# 3. SAVINGS ESTIMATOR TESTS
# ==============================================================================

def test_savings_calculation_exact_formulas(client_with_db):
    """14. Verifies exact mathematical formula for daily/monthly loss and monetary savings."""
    client, session_factory = client_with_db
    db = session_factory()
    # Flow = 5.0 L/h, hours = 24.0, tariff = 2.50
    # daily = 5.0 * 24.0 = 120.0 L
    # monthly = 120.0 * 30 = 3600.0 L
    # monthly savings = (3600 / 1000) * 2.50 = 9.00
    t = datetime(2026, 9, 1, 2, 0, 0)
    db.add(
        Alert(
            zone_id=1,
            timestamp=t,
            alert_type="leak",
            severity="medium",
            message="Continuous night leak detected in Household: average flow of 5.00 L/h across 3 hours.",
            resolved=False,
        )
    )
    db.commit()
    db.close()

    response = client.get("/conservation/savings?tariff_per_kl=2.50&hours_per_day=24.0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_leaks_evaluated"] == 1
    assert data["actionable_leaks_count"] == 1
    assert data["total_daily_wasted_litres"] == 120.0
    assert data["total_monthly_wasted_litres"] == 3600.0
    assert data["total_monthly_savings"] == 9.00

    est = data["leak_estimates"][0]
    assert est["leak_flow_lph"] == 5.0
    assert est["daily_wasted_litres"] == 120.0
    assert est["monthly_wasted_litres"] == 3600.0
    assert est["monthly_savings"] == 9.00
    assert est["status"] == "estimated"
    assert est["is_estimate"] is True


def test_savings_configurable_tariff(client_with_db):
    """15. Configurable water tariff scales monetary savings correctly."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 2, 0, 0)
    db.add(
        Alert(
            zone_id=1,
            timestamp=t,
            alert_type="leak",
            severity="high",
            message="Leak with average flow of 10.0 L/h.",
            resolved=False,
        )
    )
    db.commit()
    db.close()

    # Flow 10 L/h * 24h = 240 L/day * 30 = 7200 L/month.
    # At tariff = $4.00 / kL: savings = 7.2 * 4.00 = 28.80
    response = client.get("/conservation/savings?tariff_per_kl=4.00&hours_per_day=24.0")
    assert response.status_code == 200
    data = response.json()
    assert data["tariff_per_kl"] == 4.0
    assert data["total_monthly_savings"] == 28.80


def test_savings_configurable_leak_duration(client_with_db):
    """16. Configurable leak duration adjusts daily waste and savings proportionally."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 2, 0, 0)
    db.add(
        Alert(
            zone_id=1,
            timestamp=t,
            alert_type="leak",
            severity="medium",
            message="Night leak average flow of 4.0 L/h.",
            resolved=False,
        )
    )
    db.commit()
    db.close()

    # 4 L/h * 12 hours = 48 L/day * 30 = 1440 L/month.
    # At tariff = $2.50 / kL: savings = 1.44 * 2.50 = 3.60
    response = client.get("/conservation/savings?tariff_per_kl=2.50&hours_per_day=12.0")
    assert response.status_code == 200
    data = response.json()
    assert data["assumed_hours_per_day"] == 12.0
    assert data["total_daily_wasted_litres"] == 48.0
    assert data["total_monthly_wasted_litres"] == 1440.0
    assert data["total_monthly_savings"] == 3.60


def test_savings_missing_flow_metadata_explicit_unavailable(client_with_db):
    """17. Leaks without measurable flow rate return status 'unavailable' without guessing."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 2, 0, 0)
    db.add(
        Alert(
            zone_id=1,
            timestamp=t,
            alert_type="leak",
            severity="medium",
            message="Unspecified leak detected via manual inspection without sensor telemetry.",
            resolved=False,
        )
    )
    db.commit()
    db.close()

    response = client.get("/conservation/savings")
    assert response.status_code == 200
    data = response.json()
    assert data["total_leaks_evaluated"] == 1
    assert data["actionable_leaks_count"] == 0
    assert data["total_daily_wasted_litres"] == 0.0
    assert data["total_monthly_savings"] == 0.0

    est = data["leak_estimates"][0]
    assert est["status"] == "unavailable"
    assert est["leak_flow_lph"] is None
    assert est["daily_wasted_litres"] is None
    assert est["monthly_savings"] is None


def test_savings_invalid_tariff_rejected(client_with_db):
    """18. Non-positive water tariff is rejected with 400 Bad Request."""
    client, _ = client_with_db
    response = client.get("/conservation/savings?tariff_per_kl=0")
    assert response.status_code == 400

    response_neg = client.get("/conservation/savings?tariff_per_kl=-2.5")
    assert response_neg.status_code == 400


def test_savings_invalid_hours_per_day_rejected(client_with_db):
    """19. Leak duration <= 0 or > 24 is rejected with 400 Bad Request."""
    client, _ = client_with_db
    res_zero = client.get("/conservation/savings?hours_per_day=0")
    assert res_zero.status_code == 400

    res_excess = client.get("/conservation/savings?hours_per_day=25")
    assert res_excess.status_code == 400


def test_savings_nonexistent_zone_rejected(client_with_db):
    """20. Nonexistent zone filter returns 404 Not Found."""
    client, _ = client_with_db
    response = client.get("/conservation/savings?zone_id=9999")
    assert response.status_code == 404


# ==============================================================================
# 4. ALERT COUNT DECOMPOSITION REGRESSION TEST
# ==============================================================================

def test_alert_count_decomposition_and_duplicate_prevention(client_with_sim_dataset):
    """21. Accurately distinguishes candidate detections, newly created alerts, and existing duplicates."""
    client, session_factory = client_with_sim_dataset

    # Run 1 on fresh simulated dataset
    res1 = client.post("/detection/run")
    assert res1.status_code == 200
    data1 = res1.json()

    candidates1 = data1["candidate_detections"]
    created1 = data1["alerts_created"]
    existing1 = data1["alerts_existing"]

    # Verify decomposition: total candidates = newly created + intra-batch skipped duplicates
    assert candidates1 == created1 + existing1
    assert candidates1 == 52
    assert created1 == 49
    assert existing1 == 3

    # Run 2: Rerun pipeline against populated database
    res2 = client.post("/detection/run")
    assert res2.status_code == 200
    data2 = res2.json()

    candidates2 = data2["candidate_detections"]
    created2 = data2["alerts_created"]
    existing2 = data2["alerts_existing"]

    assert candidates2 == 52
    assert created2 == 0
    assert existing2 == 52
    assert candidates2 == created2 + existing2

    # Database alert count unchanged
    db = session_factory()
    total_db_alerts = db.query(Alert).count()
    assert total_db_alerts == 49
    db.close()
