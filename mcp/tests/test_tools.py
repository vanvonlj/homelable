import pytest
from unittest.mock import AsyncMock, patch
from app.tools import _dispatch


@pytest.fixture
def mock_backend():
    with patch("app.tools.backend") as m:
        m.post = AsyncMock(return_value={"id": "1"})
        m.patch = AsyncMock(return_value={"id": "1"})
        m.delete = AsyncMock(return_value={})
        yield m


@pytest.mark.anyio
async def test_create_node(mock_backend):
    result = await _dispatch("create_node", {"type": "server", "label": "Proxmox"})
    mock_backend.post.assert_called_once_with("/api/v1/nodes", {"type": "server", "label": "Proxmox"})
    assert result == {"id": "1"}


@pytest.mark.anyio
async def test_update_node(mock_backend):
    await _dispatch("update_node", {"id": "42", "label": "New name"})
    mock_backend.patch.assert_called_once_with("/api/v1/nodes/42", {"label": "New name"})


@pytest.mark.anyio
async def test_delete_node(mock_backend):
    await _dispatch("delete_node", {"id": "42"})
    mock_backend.delete.assert_called_once_with("/api/v1/nodes/42")


@pytest.mark.anyio
async def test_create_edge(mock_backend):
    await _dispatch("create_edge", {"source": "1", "target": "2", "type": "ethernet"})
    mock_backend.post.assert_called_once_with("/api/v1/edges", {"source": "1", "target": "2", "type": "ethernet"})


@pytest.mark.anyio
async def test_delete_edge(mock_backend):
    await _dispatch("delete_edge", {"id": "99"})
    mock_backend.delete.assert_called_once_with("/api/v1/edges/99")


@pytest.mark.anyio
async def test_trigger_scan_no_ranges(mock_backend):
    await _dispatch("trigger_scan", {})
    mock_backend.post.assert_called_once_with("/api/v1/scan/trigger", {})


@pytest.mark.anyio
async def test_trigger_scan_with_ranges(mock_backend):
    await _dispatch("trigger_scan", {"ranges": ["192.168.1.0/24"]})
    mock_backend.post.assert_called_once_with("/api/v1/scan/trigger", {"ranges": ["192.168.1.0/24"]})


@pytest.mark.anyio
async def test_approve_device(mock_backend):
    await _dispatch("approve_device", {"id": "5", "type": "server", "label": "MyServer"})
    mock_backend.post.assert_called_once_with("/api/v1/scan/pending/5/approve", {"type": "server", "label": "MyServer"})


@pytest.mark.anyio
async def test_hide_device(mock_backend):
    await _dispatch("hide_device", {"id": "5"})
    mock_backend.post.assert_called_once_with("/api/v1/scan/pending/5/hide", {})


@pytest.mark.anyio
async def test_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        await _dispatch("nonexistent", {})
