import pytest


@pytest.mark.anyio
async def test_health_no_key(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_missing_api_key(client):
    resp = await client.get("/mcp")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_wrong_api_key(client):
    resp = await client.get("/mcp", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_valid_api_key_passes(client, api_key):
    # SSE endpoint returns 200 with valid key (even if stream is incomplete in tests)
    resp = await client.get("/mcp", headers={"X-API-Key": api_key})
    assert resp.status_code != 401
