"""Tests for background scheduler: _load_interval, _run_status_checks, lifecycle."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.scheduler import _load_interval, _run_status_checks, start_scheduler, stop_scheduler
from app.db.database import Base
from app.db.models import Node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(**kwargs) -> Node:
    defaults = dict(
        id=str(uuid.uuid4()),
        type="server",
        label="Test",
        status="unknown",
        pos_x=0.0,
        pos_y=0.0,
    )
    return Node(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# _load_interval
# ---------------------------------------------------------------------------

def test_load_interval_reads_from_config(tmp_path):
    """_load_interval returns the value set in config.yml."""
    cfg = tmp_path / "config.yml"
    cfg.write_text("status_checker:\n  interval_seconds: 30\n")
    with patch("app.core.scheduler.settings") as mock_settings:
        mock_settings.config_path = str(cfg)
        assert _load_interval() == 30


def test_load_interval_defaults_to_60_when_key_missing(tmp_path):
    """_load_interval returns 60 when status_checker section is absent."""
    cfg = tmp_path / "config.yml"
    cfg.write_text("auth:\n  username: admin\n")
    with patch("app.core.scheduler.settings") as mock_settings:
        mock_settings.config_path = str(cfg)
        assert _load_interval() == 60


def test_load_interval_defaults_to_60_on_missing_file():
    """_load_interval returns 60 when config file does not exist."""
    with patch("app.core.scheduler.settings") as mock_settings:
        mock_settings.config_path = "/nonexistent/path/config.yml"
        assert _load_interval() == 60


# ---------------------------------------------------------------------------
# _run_status_checks
# ---------------------------------------------------------------------------

@pytest.fixture
async def mem_db():
    """In-memory SQLite DB with Node table created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_run_status_checks_skips_nodes_without_check_method(mem_db):
    """Nodes with no check_method are skipped; check_node is never called."""
    async with mem_db() as session:
        node = _make_node(check_method=None, ip="10.0.0.1")
        session.add(node)
        await session.commit()

    with patch("app.core.scheduler.AsyncSessionLocal", mem_db), \
         patch("app.core.scheduler.check_node", new_callable=AsyncMock) as mock_check:
        await _run_status_checks()
        mock_check.assert_not_called()


@pytest.mark.asyncio
async def test_run_status_checks_updates_node_status(mem_db):
    """check_node result is persisted to the DB and broadcast via WebSocket."""
    async with mem_db() as session:
        node = _make_node(check_method="ping", ip="10.0.0.1")
        session.add(node)
        await session.commit()
        node_id = node.id

    check_result = {"status": "online", "response_time_ms": 5}

    with patch("app.core.scheduler.AsyncSessionLocal", mem_db), \
         patch("app.core.scheduler.check_node", new_callable=AsyncMock, return_value=check_result), \
         patch("app.api.routes.status.broadcast_status", new_callable=AsyncMock) as mock_broadcast:
        await _run_status_checks()

    # Verify DB updated
    async with mem_db() as session:
        updated = await session.get(Node, node_id)
        assert updated is not None
        assert updated.status == "online"
        assert updated.response_time_ms == 5

    # Verify WebSocket broadcast
    mock_broadcast.assert_awaited_once()
    _, kwargs = mock_broadcast.call_args
    assert kwargs["node_id"] == node_id
    assert kwargs["status"] == "online"


@pytest.mark.asyncio
async def test_run_status_checks_sets_last_seen_only_when_online(mem_db):
    """last_seen is updated only when status is 'online'."""
    async with mem_db() as session:
        node = _make_node(check_method="ping", ip="10.0.0.1", last_seen=None)
        session.add(node)
        await session.commit()
        node_id = node.id

    check_result = {"status": "offline", "response_time_ms": None}

    with patch("app.core.scheduler.AsyncSessionLocal", mem_db), \
         patch("app.core.scheduler.check_node", new_callable=AsyncMock, return_value=check_result), \
         patch("app.api.routes.status.broadcast_status", new_callable=AsyncMock):
        await _run_status_checks()

    async with mem_db() as session:
        updated = await session.get(Node, node_id)
        assert updated is not None
        assert updated.last_seen is None  # not set for offline


@pytest.mark.asyncio
async def test_run_status_checks_handles_check_error_gracefully(mem_db):
    """An exception from check_node is logged and does not abort other nodes."""
    async with mem_db() as session:
        n1 = _make_node(check_method="ping", ip="10.0.0.1")
        n2 = _make_node(check_method="ping", ip="10.0.0.2")
        session.add_all([n1, n2])
        await session.commit()

    call_count = 0
    async def flaky_check(method, target, ip):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("timeout")
        return {"status": "online", "response_time_ms": 1}

    with patch("app.core.scheduler.AsyncSessionLocal", mem_db), \
         patch("app.core.scheduler.check_node", side_effect=flaky_check), \
         patch("app.api.routes.status.broadcast_status", new_callable=AsyncMock):
        await _run_status_checks()  # must not raise

    assert call_count == 2


# ---------------------------------------------------------------------------
# start_scheduler / stop_scheduler
# ---------------------------------------------------------------------------

def test_start_and_stop_scheduler():
    """Scheduler can be started and stopped without errors."""
    mock_sched = MagicMock()
    with patch("app.core.scheduler._load_interval", return_value=3600), \
         patch("app.core.scheduler.AsyncIOScheduler", return_value=mock_sched):
        start_scheduler()
        stop_scheduler()
        mock_sched.add_job.assert_called_once()
        mock_sched.start.assert_called_once()
        mock_sched.shutdown.assert_called_once()


def test_start_scheduler_uses_configured_interval():
    """Scheduler registers the status_checks job with the correct interval."""
    mock_sched = MagicMock()
    with patch("app.core.scheduler._load_interval", return_value=120) as mock_interval, \
         patch("app.core.scheduler.AsyncIOScheduler", return_value=mock_sched):
        start_scheduler()
        mock_interval.assert_called_once()
        mock_sched.add_job.assert_called_once()
        _, kwargs = mock_sched.add_job.call_args
        assert kwargs.get("seconds") == 120
        mock_sched.start.assert_called_once()
