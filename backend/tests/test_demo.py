"""Tests for AquaWatch Live Demo mode and Simulated Leak Injection (Task 8).

Verifies:
- GET /demo/status
- POST /demo/start
- POST /demo/inject (valid/invalid zones, leak types, severity, detector execution)
- Duplicate prevention during active injection
- Safe alert resolution integration
- POST /demo/reset (safe rollback of session readings and alerts, data preservation)
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Alert, Reading, Zone
from app.services.simulator import simulate_dataset


@pytest.fixture
def demo_test_env(test_db):
    """Sets up a seeded test database and provides TestClient with get_db override."""
    session_factory = test_db["session_factory"]
    engine = test_db["engine"]

    # Seed baseline readings and ground truth anomalies
    simulate_dataset(
        days=10,  # 10 days for fast test execution
        seed=42,
        engine=engine,
        session_factory=session_factory,
    )

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


def test_demo_status_initial(demo_test_env):
    """1. Verify GET /demo/status returns ready status with initial timeline."""
    client, _ = demo_test_env
    res = client.get("/demo/status")
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["status"] in ["idle", "ready"]
    assert len(data["timeline"]) >= 1


def test_demo_start_session(demo_test_env):
    """2. Verify POST /demo/start initializes a fresh session."""
    client, _ = demo_test_env
    res = client.post("/demo/start?session_id=test_sess_01")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "test_sess_01"
    assert data["status"] == "ready"


def test_demo_inject_invalid_zone(demo_test_env):
    """3. Verify POST /demo/inject rejects nonexistent zone ID with 404."""
    client, _ = demo_test_env
    res = client.post(
        "/demo/inject",
        json={"zone_id": 9999, "leak_type": "slow_leak", "severity": "high"},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_demo_inject_invalid_parameters(demo_test_env):
    """4. Verify POST /demo/inject validates leak_type and severity."""
    client, _ = demo_test_env
    # Invalid leak type
    res1 = client.post(
        "/demo/inject",
        json={"zone_id": 1, "leak_type": "invalid_leak", "severity": "high"},
    )
    assert res1.status_code == 422

    # Invalid severity
    res2 = client.post(
        "/demo/inject",
        json={"zone_id": 1, "leak_type": "slow_leak", "severity": "extreme"},
    )
    assert res2.status_code == 422


def test_demo_inject_slow_night_leak_success(demo_test_env):
    """5. Verify slow night leak injection triggers RuleBasedDetector and persists alert."""
    client, session_factory = demo_test_env

    # Record pre-injection counts
    with session_factory() as session:
        initial_readings_count = session.query(Reading).count()
        initial_alerts_count = session.query(Alert).count()

    res = client.post(
        "/demo/inject",
        json={
            "zone_id": 1,
            "leak_type": "slow_leak",
            "severity": "high",
            "session_id": "test_slow_leak",
        },
    )
    assert res.status_code == 201
    data = res.json()

    assert data["success"] is True
    assert data["zone_id"] == 1
    assert data["leak_type"] == "slow_leak"
    assert data["severity"] == "high"
    assert data["leak_flow_lph"] == 22.0
    assert data["readings_injected"] > 0

    # Verify detector was genuinely evaluated
    assert "Rule-Based" in data["detector"]["name"]
    assert data["detector"]["score"] >= 20.0

    # Verify created alert
    alert = data["alert"]
    assert alert["alert_type"] == "leak"
    assert alert["resolved"] is False
    assert "[SIMULATED DEMO:" in alert["message"]

    # Verify database counts increased
    with session_factory() as session:
        new_readings_count = session.query(Reading).count()
        new_alerts_count = session.query(Alert).count()
        assert new_readings_count > initial_readings_count
        assert new_alerts_count == initial_alerts_count + 1


def test_demo_duplicate_injection_conflict(demo_test_env):
    """6. Verify attempting a second injection without resolving/resetting raises 409 Conflict."""
    client, _ = demo_test_env
    client.post("/demo/start?session_id=conflict_session")

    res1 = client.post(
        "/demo/inject",
        json={
            "zone_id": 2,
            "leak_type": "slow_leak",
            "severity": "medium",
            "session_id": "conflict_session",
        },
    )
    assert res1.status_code == 201

    # Attempt second injection while alert unresolved
    res2 = client.post(
        "/demo/inject",
        json={
            "zone_id": 2,
            "leak_type": "slow_leak",
            "severity": "high",
            "session_id": "conflict_session",
        },
    )
    assert res2.status_code == 409
    assert "already in progress" in res2.json()["detail"].lower()


def test_demo_alert_resolution_updates_status(demo_test_env):
    """7. Verify resolving the demo alert transitions status to resolved."""
    client, _ = demo_test_env
    client.post("/demo/start?session_id=resolve_session")

    res_inject = client.post(
        "/demo/inject",
        json={
            "zone_id": 3,
            "leak_type": "slow_leak",
            "severity": "low",
            "session_id": "resolve_session",
        },
    )
    assert res_inject.status_code == 201
    alert_id = res_inject.json()["alert"]["id"]

    # Resolve alert via standard API
    res_resolve = client.patch(f"/alerts/{alert_id}/resolve")
    assert res_resolve.status_code == 200
    assert res_resolve.json()["resolved"] is True

    # Check demo status
    res_status = client.get("/demo/status?session_id=resolve_session")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "resolved"
    assert data["alert_resolved"] is True
    assert any(t["step"] == "alert_resolved" for t in data["timeline"])


def test_demo_inject_burst_triggers_zscore(demo_test_env):
    """8. Verify high-volume burst injection triggers Statistical Z-Score detector."""
    client, session_factory = demo_test_env
    client.post("/demo/start?session_id=burst_session")

    res = client.post(
        "/demo/inject",
        json={
            "zone_id": 4,
            "leak_type": "burst",
            "severity": "high",
            "session_id": "burst_session",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "Z-Score" in data["detector"]["name"]
    assert data["alert"]["alert_type"] == "spike"
    assert data["leak_flow_lph"] == 550.0


def test_demo_reset_safe_cleanup(demo_test_env):
    """9. Verify POST /demo/reset cleans only session readings and alerts, preserving baseline."""
    client, session_factory = demo_test_env

    with session_factory() as session:
        baseline_readings = session.query(Reading).count()
        baseline_alerts = session.query(Alert).count()

    client.post("/demo/start?session_id=cleanup_session")
    inject_res = client.post(
        "/demo/inject",
        json={
            "zone_id": 1,
            "leak_type": "slow_leak",
            "severity": "high",
            "session_id": "cleanup_session",
        },
    )
    assert inject_res.status_code == 201

    with session_factory() as session:
        assert session.query(Reading).count() > baseline_readings
        assert session.query(Alert).count() > baseline_alerts

    # Reset demo
    reset_res = client.post("/demo/reset?session_id=cleanup_session")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "reset"
    assert reset_data["readings_cleaned"] > 0
    assert reset_data["alerts_cleaned"] >= 1
    assert reset_data["original_data_preserved"] is True

    # Verify database returned to baseline counts
    with session_factory() as session:
        assert session.query(Reading).count() == baseline_readings
        assert session.query(Alert).count() == baseline_alerts
