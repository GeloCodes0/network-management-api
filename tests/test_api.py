
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db


# Use an isolated in-memory database for tests so they do not
# modify the application's normal local database.
@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Replace the production database dependency with our test DB.
    main.app.dependency_overrides[get_db] = override_get_db

    # Use a predictable key in tests; never use the real .env key.
    monkeypatch.setattr(main, "API_KEY", "test-only-api-key")

    # Give each test a fresh rate-limit window.
    main.request_timestamps.clear()

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    main.request_timestamps.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def auth_headers():
    """Return the test API key in the required header."""
    return {"X-API-Key": "test-only-api-key"}


@pytest.fixture
def sample_device():
    """Provide valid network-device data for API tests."""
    return {
        "hostname": "SW-CORE-01",
        "ip_address": "192.168.1.10",
        "device_type": "switch",
        "vendor": "Cisco",
        "model": "Catalyst 2960",
        "operating_system": "Cisco IOS",
        "location": "Test Lab",
        "status": "unknown",
    }


def test_health_endpoint(client):
    """The health endpoint should report API and database status."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


def test_device_endpoint_requires_api_key(client):
    """Requests without an API key should be rejected."""
    response = client.get("/devices/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_valid_api_key_can_list_devices(client, auth_headers):
    """A valid key should allow access to the device inventory."""
    response = client.get("/devices/", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_retrieve_device(
    client,
    auth_headers,
    sample_device,
):
    """A device can be created and retrieved by its database ID."""
    create_response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )

    assert create_response.status_code == 201

    created_device = create_response.json()
    assert created_device["hostname"] == "SW-CORE-01"
    assert created_device["ip_address"] == "192.168.1.10"
    assert "id" in created_device

    get_response = client.get(
        f"/devices/{created_device['id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["hostname"] == "SW-CORE-01"


def test_duplicate_device_is_rejected(
    client,
    auth_headers,
    sample_device,
):
    """Duplicate hostnames or IP addresses should return HTTP 409."""
    first_response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )

    assert duplicate_response.status_code == 409


def test_invalid_ip_address_is_rejected(client, auth_headers, sample_device):
    """Invalid IPv4 input should fail request validation."""
    sample_device["ip_address"] = "not-an-ip-address"

    response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )

    assert response.status_code == 422


def test_device_can_be_updated(
    client,
    auth_headers,
    sample_device,
):
    """A partial update should change only the supplied fields."""
    create_response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )
    device_id = create_response.json()["id"]

    update_response = client.patch(
        f"/devices/{device_id}",
        headers=auth_headers,
        json={"status": "online"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "online"
    assert update_response.json()["hostname"] == "SW-CORE-01"


def test_device_can_be_deleted(
    client,
    auth_headers,
    sample_device,
):
    """Deleted devices should no longer be retrievable."""
    create_response = client.post(
        "/devices/",
        headers=auth_headers,
        json=sample_device,
    )
    device_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/devices/{device_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/devices/{device_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


def test_rate_limit_blocks_excess_requests(client):
    """Requests above the configured limit should return HTTP 429."""
    responses = [
        client.get("/devices/")
        for _ in range(main.RATE_LIMIT_REQUESTS + 1)
    ]

    # Requests within the limit reach authentication and return 401.
    for response in responses[:main.RATE_LIMIT_REQUESTS]:
        assert response.status_code == 401

    # The next request is blocked by rate limiting.
    assert responses[-1].status_code == 429
    assert "Retry-After" in responses[-1].headers