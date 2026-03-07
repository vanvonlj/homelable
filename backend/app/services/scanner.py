"""Network scanner: ARP sweep + nmap service detection."""
import asyncio
import logging
import socket
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PendingDevice, ScanRun
from app.services.fingerprint import fingerprint_ports, suggest_node_type

logger = logging.getLogger(__name__)

try:
    import nmap
    _NMAP_AVAILABLE = True
except ImportError:
    _NMAP_AVAILABLE = False
    logger.warning("python-nmap not available — scanner will run in mock mode")


def _nmap_scan(target: str) -> list[dict[str, Any]]:
    """Run nmap -sV --open on target, return list of host dicts."""
    if not _NMAP_AVAILABLE:
        return _mock_scan(target)

    nm = nmap.PortScanner()
    try:
        nm.scan(hosts=target, arguments="-sV --open -T4 --host-timeout 30s")
    except Exception as exc:
        logger.error("nmap scan failed: %s", exc)
        raise RuntimeError(str(exc)) from exc

    hosts = []
    for host in nm.all_hosts():
        if nm[host].state() != "up":
            continue
        open_ports = []
        for proto in nm[host].all_protocols():
            for port, info in nm[host][proto].items():
                if info["state"] == "open":
                    open_ports.append({
                        "port": port,
                        "protocol": proto,
                        "banner": info.get("product", "") + " " + info.get("version", ""),
                    })
        hosts.append({
            "ip": host,
            "hostname": _resolve_hostname(host),
            "mac": nm[host].get("addresses", {}).get("mac"),
            "os": _extract_os(nm, host),
            "open_ports": open_ports,
        })
    return hosts


def _resolve_hostname(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _extract_os(nm: object, host: str) -> str | None:
    try:
        osmatch = nm[host].get("osmatch", [])  # type: ignore[index]
        if osmatch:
            return str(osmatch[0]["name"])
    except Exception:
        pass
    return None


def _mock_scan(target: str) -> list[dict[str, Any]]:
    """Return fake results for dev/test environments without nmap."""
    return [
        {
            "ip": "192.168.1.99",
            "hostname": "unknown-device.lan",
            "mac": "AA:BB:CC:DD:EE:FF",
            "os": None,
            "open_ports": [
                {"port": 80, "protocol": "tcp", "banner": "nginx"},
                {"port": 22, "protocol": "tcp", "banner": "OpenSSH 9.0"},
            ],
        }
    ]


async def run_scan(ranges: list[str], db: AsyncSession, run_id: str) -> None:
    """Execute scan for given CIDR ranges and populate pending_devices."""
    # Avoid circular import
    from sqlalchemy import select

    from app.api.routes.status import broadcast_scan_update

    devices_found = 0
    try:
        for cidr in ranges:
            # Run nmap in a thread pool — does not block the event loop
            hosts = await asyncio.to_thread(_nmap_scan, cidr)

            for host in hosts:
                services = fingerprint_ports(host["open_ports"])
                suggested_type = suggest_node_type(host["open_ports"])

                # Skip if already pending (by IP)
                existing = await db.execute(
                    select(PendingDevice).where(
                        PendingDevice.ip == host["ip"],
                        PendingDevice.status == "pending",
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                device = PendingDevice(
                    ip=host["ip"],
                    mac=host.get("mac"),
                    hostname=host.get("hostname"),
                    os=host.get("os"),
                    services=services,
                    suggested_type=suggested_type,
                    status="pending",
                )
                db.add(device)
                devices_found += 1

                # Commit immediately so the device is visible right away
                await db.commit()

                # Update running count on the scan run record
                run = await db.get(ScanRun, run_id)
                if run:
                    run.devices_found = devices_found
                    await db.commit()

                # Push WS event so the frontend refreshes pending panel
                await broadcast_scan_update(run_id=run_id, devices_found=devices_found)

        # Mark scan as done
        run = await db.get(ScanRun, run_id)
        if run:
            run.status = "done"
            run.devices_found = devices_found
            run.finished_at = datetime.now(UTC)
            await db.commit()

    except Exception as exc:
        logger.error("Scan failed: %s", exc)
        run = await db.get(ScanRun, run_id)
        if run:
            run.status = "error"
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            await db.commit()
