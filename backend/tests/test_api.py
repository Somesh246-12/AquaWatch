"""AquaWatch API End-to-End and Integration Tests (Task 5).

Verifies all REST API endpoints:
- GET /health
- GET /zones, GET /zones/{zone_id}
- GET /readings, GET /readings/{reading_id}, POST /readings
- GET /alerts, GET /alerts/{alert_id}, PATCH /alerts/{alert_id}/resolve
- GET /summary
- POST /detection/run (Pipeline execution, alert persistence, duplicate prevention)
"""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.alert import Alert
from app.models.reading import Reading
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
# 1. HEALTH ENDPOINT TESTS
# ==============================================================================

def test_health_endpoint_succeeds(client_with_db):
    """1. GET /health succeeds and returns 200 OK with expected fields."""
    client, _ = client_with_db
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "AquaWatch API"
    assert "version" in data


# ==============================================================================
# 2. ZONES ENDPOINT TESTS
# ==============================================================================

def test_get_zones_returns_exactly_five(client_with_db):
    """2. GET /zones returns exactly five zones ordered by id ascending."""
    client, _ = client_with_db
    response = client.get("/zones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    ids = [z["id"] for z in data]
    assert ids == sorted(ids)
    names = [z["name"] for z in data]
    assert "Household" in names
    assert "Hostel Block" in names


def test_get_zone_by_id_returns_valid_zone(client_with_db):
    """3. GET /zones/{id} returns a valid zone."""
    client, _ = client_with_db
    response = client.get("/zones/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Household"
    assert data["type"] == "residential"
    assert data["daily_budget_litres"] == 1500.0


def test_get_zone_invalid_id_returns_404(client_with_db):
    """4. GET /zones/{invalid_id} returns 404 Not Found."""
    client, _ = client_with_db
    response = client.get("/zones/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ==============================================================================
# 3. READINGS ENDPOINT TESTS
# ==============================================================================

def test_get_readings_returns_readings(client_with_db):
    """5. GET /readings returns readings."""
    client, session_factory = client_with_db
    db = session_factory()
    base_time = datetime(2026, 9, 1, 10, 0, 0)
    for i in range(5):
        db.add(Reading(zone_id=1, timestamp=base_time + timedelta(hours=i), litres=25.0 + i))
    db.commit()
    db.close()

    response = client.get("/readings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["zone_id"] == 1
    assert data[0]["litres"] == 25.0


def test_get_readings_filter_by_zone_id(client_with_db):
    """6. GET /readings filters by zone_id."""
    client, session_factory = client_with_db
    db = session_factory()
    base_time = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Reading(zone_id=1, timestamp=base_time, litres=30.0))
    db.add(Reading(zone_id=2, timestamp=base_time, litres=40.0))
    db.commit()
    db.close()

    response = client.get("/readings?zone_id=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["zone_id"] == 2
    assert data[0]["litres"] == 40.0


def test_get_readings_filter_by_timestamp(client_with_db):
    """7. GET /readings filters by start and end timestamps."""
    client, session_factory = client_with_db
    db = session_factory()
    base_time = datetime(2026, 9, 1, 0, 0, 0)
    for h in range(10):
        db.add(Reading(zone_id=1, timestamp=base_time + timedelta(hours=h), litres=10.0))
    db.commit()
    db.close()

    start_iso = (base_time + timedelta(hours=3)).isoformat()
    end_iso = (base_time + timedelta(hours=6)).isoformat()
    response = client.get(f"/readings?start={start_iso}&end={end_iso}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4  # hours 3, 4, 5, 6


def test_get_readings_aggregation_hourly(client_with_db):
    """8. GET /readings aggregation=hourly works."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=t, litres=50.0))
    db.commit()
    db.close()

    response = client.get("/readings?aggregation=hourly")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "timestamp" in data[0]
    assert data[0]["litres"] == 50.0


def test_get_readings_aggregation_daily(client_with_db):
    """9. GET /readings aggregation=daily works."""
    client, session_factory = client_with_db
    db = session_factory()
    day1 = datetime(2026, 9, 1, 8, 0, 0)
    day2 = datetime(2026, 9, 1, 14, 0, 0)
    db.add(Reading(zone_id=1, timestamp=day1, litres=50.0))
    db.add(Reading(zone_id=1, timestamp=day2, litres=70.0))
    db.commit()
    db.close()

    response = client.get("/readings?aggregation=daily")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-09-01"
    assert data[0]["zone_id"] == 1
    assert data[0]["litres"] == 120.0


def test_get_readings_invalid_aggregation_rejected(client_with_db):
    """10. GET /readings rejects invalid aggregation with 400 Bad Request."""
    client, _ = client_with_db
    response = client.get("/readings?aggregation=monthly")
    assert response.status_code == 400
    assert "invalid aggregation" in response.json()["detail"].lower()


def test_get_readings_invalid_date_range_rejected(client_with_db):
    """11. GET /readings rejects start > end with 400 Bad Request."""
    client, _ = client_with_db
    start_iso = "2026-09-20T12:00:00"
    end_iso = "2026-09-10T12:00:00"
    response = client.get(f"/readings?start={start_iso}&end={end_iso}")
    assert response.status_code == 400
    assert "start timestamp must be earlier" in response.json()["detail"].lower()


def test_get_readings_pagination(client_with_db):
    """12. GET /readings pagination limit and offset work properly."""
    client, session_factory = client_with_db
    db = session_factory()
    base_time = datetime(2026, 9, 1, 0, 0, 0)
    for i in range(10):
        db.add(Reading(zone_id=1, timestamp=base_time + timedelta(hours=i), litres=float(i)))
    db.commit()
    db.close()

    response = client.get("/readings?limit=3&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["litres"] == 2.0
    assert data[1]["litres"] == 3.0
    assert data[2]["litres"] == 4.0


def test_get_reading_by_id_works(client_with_db):
    """13. GET /readings/{id} returns the specific reading."""
    client, session_factory = client_with_db
    db = session_factory()
    r = Reading(zone_id=1, timestamp=datetime(2026, 9, 1, 10, 0, 0), litres=42.5)
    db.add(r)
    db.commit()
    reading_id = r.id
    db.close()

    response = client.get(f"/readings/{reading_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == reading_id
    assert data["litres"] == 42.5


def test_get_reading_missing_returns_404(client_with_db):
    """14. GET /readings/{id} returns 404 for nonexistent reading."""
    client, _ = client_with_db
    response = client.get("/readings/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_reading_accepts_valid_reading(client_with_db):
    """15. POST /readings creates and returns a new reading with 201 Created."""
    client, _ = client_with_db
    payload = {
        "zone_id": 1,
        "timestamp": "2026-09-05T14:30:00",
        "litres": 88.5,
    }
    response = client.post("/readings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["zone_id"] == 1
    assert data["litres"] == 88.5


def test_post_reading_rejects_negative_litres(client_with_db):
    """16. POST /readings rejects negative litres with 422 Unprocessable Entity."""
    client, _ = client_with_db
    payload = {
        "zone_id": 1,
        "timestamp": "2026-09-05T14:30:00",
        "litres": -10.0,
    }
    response = client.post("/readings", json=payload)
    assert response.status_code == 422


def test_post_reading_rejects_nonexistent_zone(client_with_db):
    """17. POST /readings rejects nonexistent zone with 404 Not Found."""
    client, _ = client_with_db
    payload = {
        "zone_id": 9999,
        "timestamp": "2026-09-05T14:30:00",
        "litres": 25.0,
    }
    response = client.post("/readings", json=payload)
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


# ==============================================================================
# 4. ALERTS ENDPOINT TESTS
# ==============================================================================

def test_get_alerts_works(client_with_db):
    """18. GET /alerts returns alerts ordered newest first."""
    client, session_factory = client_with_db
    db = session_factory()
    t1 = datetime(2026, 9, 1, 10, 0, 0)
    t2 = datetime(2026, 9, 2, 10, 0, 0)
    db.add(Alert(zone_id=1, timestamp=t1, alert_type="leak", severity="low", message="Leak 1"))
    db.add(Alert(zone_id=2, timestamp=t2, alert_type="spike", severity="high", message="Spike 1"))
    db.commit()
    db.close()

    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["message"] == "Spike 1"  # Newest first


def test_get_alerts_filter_by_severity(client_with_db):
    """19. GET /alerts filters by severity."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Alert(zone_id=1, timestamp=t, alert_type="leak", severity="low", message="Leak Low"))
    db.add(Alert(zone_id=1, timestamp=t, alert_type="leak", severity="high", message="Leak High"))
    db.commit()
    db.close()

    response = client.get("/alerts?severity=high")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["severity"] == "high"


def test_get_alerts_filter_by_zone(client_with_db):
    """20. GET /alerts filters by zone_id."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Alert(zone_id=1, timestamp=t, alert_type="leak", severity="low", message="Z1"))
    db.add(Alert(zone_id=3, timestamp=t, alert_type="spike", severity="medium", message="Z3"))
    db.commit()
    db.close()

    response = client.get("/alerts?zone_id=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["zone_id"] == 3


def test_get_alerts_filter_by_resolved(client_with_db):
    """21. GET /alerts filters by resolved status."""
    client, session_factory = client_with_db
    db = session_factory()
    t = datetime(2026, 9, 1, 10, 0, 0)
    db.add(Alert(zone_id=1, timestamp=t, alert_type="leak", severity="low", message="A1", resolved=True))
    db.add(Alert(zone_id=1, timestamp=t, alert_type="spike", severity="medium", message="A2", resolved=False))
    db.commit()
    db.close()

    response = client.get("/alerts?resolved=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["resolved"] is False
    assert data[0]["message"] == "A2"


def test_get_alert_by_id_works(client_with_db):
    """22. GET /alerts/{id} returns single alert."""
    client, session_factory = client_with_db
    db = session_factory()
    alert = Alert(zone_id=1, timestamp=datetime(2026, 9, 1, 10, 0, 0), alert_type="leak", severity="high", message="Test alert")
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    response = client.get(f"/alerts/{alert_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == alert_id
    assert data["message"] == "Test alert"


def test_get_alert_missing_returns_404(client_with_db):
    """23. GET /alerts/{id} returns 404 if not found."""
    client, _ = client_with_db
    response = client.get("/alerts/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_patch_alert_resolve_marks_resolved(client_with_db):
    """24. PATCH /alerts/{id}/resolve marks resolved=true without duplicating."""
    client, session_factory = client_with_db
    db = session_factory()
    alert = Alert(zone_id=1, timestamp=datetime(2026, 9, 1, 10, 0, 0), alert_type="leak", severity="high", message="To resolve", resolved=False)
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    response = client.patch(f"/alerts/{alert_id}/resolve")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == alert_id
    assert data["resolved"] is True

    # Check alert in database
    db = session_factory()
    updated = db.query(Alert).filter(Alert.id == alert_id).first()
    assert updated.resolved is True
    db.close()


# ==============================================================================
# 5. SUMMARY ENDPOINT TESTS
# ==============================================================================

def test_summary_returns_calculated_values(client_with_db):
    """25. GET /summary returns calculated usage metrics and trends."""
    client, session_factory = client_with_db
    db = session_factory()
    # Day 1: Yesterday
    yesterday = datetime(2026, 9, 1, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=yesterday, litres=100.0))
    # Day 2: Today (latest timestamp in db)
    today = datetime(2026, 9, 2, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=today, litres=150.0))
    db.commit()
    db.close()

    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["today_usage_litres"] == 150.0
    assert data["yesterday_usage_litres"] == 100.0
    assert data["change_percent"] == 50.0  # ((150 - 100) / 100) * 100
    assert data["weekly_usage_litres"] == 250.0
    assert len(data["zones"]) == 5


def test_summary_correctly_identifies_top_zone(client_with_db):
    """26. GET /summary correctly identifies top consuming zone."""
    client, session_factory = client_with_db
    db = session_factory()
    today = datetime(2026, 9, 5, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=today, litres=50.0))
    db.add(Reading(zone_id=2, timestamp=today, litres=250.0))  # Zone 2 is highest
    db.add(Reading(zone_id=3, timestamp=today, litres=30.0))
    db.commit()
    db.close()

    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    top_zone = data["top_zone"]
    assert top_zone is not None
    assert top_zone["id"] == 2
    assert top_zone["litres"] == 250.0


def test_summary_safely_handles_zero_yesterday(client_with_db):
    """27. GET /summary safely handles zero yesterday usage (change_percent = 0.0)."""
    client, session_factory = client_with_db
    db = session_factory()
    today = datetime(2026, 9, 10, 12, 0, 0)
    db.add(Reading(zone_id=1, timestamp=today, litres=80.0))
    db.commit()
    db.close()

    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["today_usage_litres"] == 80.0
    assert data["yesterday_usage_litres"] == 0.0
    assert data["change_percent"] == 0.0  # safe handling, no divide-by-zero


# ==============================================================================
# 6. DETECTION RUN ENDPOINT TESTS
# ==============================================================================

def test_post_detection_run_executes_successfully(client_with_sim_dataset):
    """28. POST /detection/run executes pipeline successfully."""
    client, _ = client_with_sim_dataset
    response = client.post("/detection/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "alerts_created" in data
    assert "alerts_existing" in data
    assert "detectors" in data
    assert "evaluation" in data


def test_detection_creates_alerts_when_appropriate(client_with_sim_dataset):
    """29. Detection creates alerts in the alerts table."""
    client, session_factory = client_with_sim_dataset
    response = client.post("/detection/run")
    assert response.status_code == 200
    data = response.json()
    alerts_created = data["alerts_created"]
    assert alerts_created > 0

    # Verify rows persisted in database
    db = session_factory()
    total_alerts = db.query(Alert).count()
    assert total_alerts == alerts_created
    db.close()


def test_running_detection_twice_does_not_create_duplicates(client_with_sim_dataset):
    """30. Running detection twice does not create duplicate alerts for the same event."""
    client, session_factory = client_with_sim_dataset

    # Run 1
    res1 = client.post("/detection/run")
    data1 = res1.json()
    created1 = data1["alerts_created"]
    assert created1 > 0

    db = session_factory()
    count_after_first = db.query(Alert).count()
    assert count_after_first == created1
    db.close()

    # Run 2
    res2 = client.post("/detection/run")
    data2 = res2.json()
    created2 = data2["alerts_created"]
    existing2 = data2["alerts_existing"]

    assert created2 == 0
    assert existing2 > 0

    db = session_factory()
    count_after_second = db.query(Alert).count()
    assert count_after_second == count_after_first
    db.close()


def test_detection_response_contains_all_three_detectors(client_with_sim_dataset):
    """31. Detection response contains findings for all three detectors."""
    client, _ = client_with_sim_dataset
    response = client.post("/detection/run")
    data = response.json()
    detectors = data["detectors"]
    assert "rule_based" in detectors
    assert "z_score" in detectors
    assert "isolation_forest" in detectors
    assert detectors["rule_based"]["mapped_alert_type"] == "leak"
    assert detectors["z_score"]["mapped_alert_type"] == "spike"
    assert detectors["isolation_forest"]["mapped_alert_type"] == "abnormal_usage"


def test_evaluation_metrics_are_actual_calculated_values(client_with_sim_dataset):
    """32. Evaluation metrics are actual calculated values against ground truth."""
    client, _ = client_with_sim_dataset
    response = client.post("/detection/run")
    data = response.json()
    evaluation = data["evaluation"]
    assert "rule_based" in evaluation
    assert "z_score" in evaluation
    assert "isolation_forest" in evaluation

    rule_eval = evaluation["rule_based"]
    assert rule_eval["precision"] == 1.0
    assert rule_eval["true_positives"] == 4
    assert rule_eval["false_positives"] == 0
    assert rule_eval["f1_score"] > 0.0
