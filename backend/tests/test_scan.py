"""Tests for scan routes: trigger, pending devices, approve/hide/ignore."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.models import PendingDevice


@pytest.fixture
async def headers(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def pending_device(db_session):
    import uuid
    device = PendingDevice(
        id=str(uuid.uuid4()),
        ip="192.168.1.100",
        mac="aa:bb:cc:dd:ee:ff",
        hostname="my-server",
        os="Linux",
        services=[{"port": 22, "name": "ssh"}],
        suggested_type="server",
        status="pending",
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


# --- Trigger scan ---

@pytest.mark.asyncio
async def test_trigger_scan_requires_auth(client: AsyncClient):
    res = await client.post("/api/v1/scan/trigger")
    # FastAPI's OAuth2PasswordBearer returns 403 when no token is provided
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_trigger_scan_creates_run(client: AsyncClient, headers):
    with (
        patch("app.api.routes.scan._background_scan", new_callable=AsyncMock),
        patch("app.api.routes.scan._load_ranges", return_value=["192.168.1.0/24"]),
    ):
        res = await client.post("/api/v1/scan/trigger", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert data["ranges"] == ["192.168.1.0/24"]
    assert "id" in data


# --- Pending devices ---

@pytest.mark.asyncio
async def test_list_pending_empty(client: AsyncClient, headers):
    res = await client.get("/api/v1/scan/pending", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_pending_returns_device(client: AsyncClient, headers, pending_device):
    res = await client.get("/api/v1/scan/pending", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["ip"] == "192.168.1.100"
    assert data[0]["hostname"] == "my-server"


# --- Approve device ---

@pytest.mark.asyncio
async def test_approve_device(client: AsyncClient, headers, pending_device):
    node_payload = {
        "label": "My Server",
        "type": "server",
        "ip": "192.168.1.100",
        "hostname": "my-server",
        "status": "unknown",
        "services": [],
    }
    res = await client.post(
        f"/api/v1/scan/pending/{pending_device.id}/approve",
        json=node_payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["approved"] is True
    assert "node_id" in data

    # Device should no longer appear in pending list
    pending_res = await client.get("/api/v1/scan/pending", headers=headers)
    assert pending_res.json() == []


@pytest.mark.asyncio
async def test_approve_nonexistent_device(client: AsyncClient, headers):
    node_payload = {
        "label": "Ghost",
        "type": "generic",
        "ip": "10.0.0.1",
        "status": "unknown",
        "services": [],
    }
    res = await client.post(
        "/api/v1/scan/pending/nonexistent-id/approve",
        json=node_payload,
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["approved"] is False


# --- Hide device ---

@pytest.mark.asyncio
async def test_hide_device(client: AsyncClient, headers, pending_device):
    res = await client.post(f"/api/v1/scan/pending/{pending_device.id}/hide", headers=headers)
    assert res.status_code == 200
    assert res.json()["hidden"] is True

    # Should no longer appear in pending
    pending_res = await client.get("/api/v1/scan/pending", headers=headers)
    assert pending_res.json() == []

    # Should appear in hidden
    hidden_res = await client.get("/api/v1/scan/hidden", headers=headers)
    assert len(hidden_res.json()) == 1


# --- Ignore device ---

@pytest.mark.asyncio
async def test_ignore_device(client: AsyncClient, headers, pending_device):
    res = await client.post(f"/api/v1/scan/pending/{pending_device.id}/ignore", headers=headers)
    assert res.status_code == 200
    assert res.json()["ignored"] is True

    # Device should be gone from both pending and hidden
    pending_res = await client.get("/api/v1/scan/pending", headers=headers)
    assert pending_res.json() == []
    hidden_res = await client.get("/api/v1/scan/hidden", headers=headers)
    assert hidden_res.json() == []


# --- Scan runs ---

@pytest.mark.asyncio
async def test_list_runs_empty(client: AsyncClient, headers):
    res = await client.get("/api/v1/scan/runs", headers=headers)
    assert res.status_code == 200
    assert res.json() == []
