"""APScheduler setup for background scan and status check jobs."""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Node
from app.services.status_checker import check_node

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler = AsyncIOScheduler()


async def _check_single_node(node: Node) -> tuple[str, dict[str, object] | None]:
    """Run a single node check; returns (node_id, result_or_None)."""
    from app.api.routes.status import broadcast_status  # avoid circular import

    try:
        check_result = await check_node(node.check_method or "", node.check_target, node.ip)
        async with AsyncSessionLocal() as db:
            n = await db.get(Node, node.id)
            if n:
                n.status = check_result["status"]
                n.response_time_ms = check_result["response_time_ms"]
                if check_result["status"] == "online":
                    n.last_seen = datetime.now(timezone.utc)
                await db.commit()
        await broadcast_status(
            node_id=node.id,
            status=check_result["status"],
            checked_at=datetime.now(timezone.utc).isoformat(),
            response_time_ms=check_result["response_time_ms"],
        )
        return node.id, check_result
    except Exception as exc:
        logger.error("Status check failed for node %s: %s", node.id, exc)
        return node.id, None


async def _run_status_checks() -> None:
    """Check all nodes concurrently and broadcast results via WebSocket."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Node))
        nodes = result.scalars().all()

    checkable = [n for n in nodes if n.check_method]
    if not checkable:
        return

    await asyncio.gather(*[_check_single_node(n) for n in checkable])


def start_scheduler() -> None:
    global scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_status_checks,
        "interval",
        seconds=settings.status_checker_interval,
        id="status_checks",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started — status checks every %ds", settings.status_checker_interval)


def reschedule_status_checks(interval_seconds: int) -> None:
    """Update the status check interval on the running scheduler."""
    if not scheduler.running:
        logger.warning("Scheduler not running, skipping reschedule")
        return
    scheduler.reschedule_job("status_checks", trigger="interval", seconds=interval_seconds)
    logger.info("Status checks rescheduled to every %ds", interval_seconds)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
