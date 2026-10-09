"""Tests for the /health endpoint and basic root status."""


def test_health_check_status_code(client):
    """Ensure the /health endpoint responds with HTTP 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload_structure(client):
    """Ensure the /health payload matches expected service details and status."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AquaWatch API"
    assert data["database"] == "connected"
    assert "version" in data


def test_root_endpoint(client):
    """Ensure the root endpoint returns a valid welcome response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["health"] == "/health"
    assert data["docs"] == "/docs"
