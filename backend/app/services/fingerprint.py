"""Match nmap scan results against service_signatures.json."""
import json
import re
from pathlib import Path

_SIGNATURES: list[dict] | None = None


def _load() -> list[dict]:
    global _SIGNATURES
    if _SIGNATURES is None:
        path = Path(__file__).parent.parent.parent / "data" / "service_signatures.json"
        with open(path) as f:
            _SIGNATURES = json.load(f)
    return _SIGNATURES


def match_port(port: int, protocol: str, banner: str | None = None) -> dict | None:
    """Return the first signature matching port+protocol, optionally banner."""
    for sig in _load():
        if sig["port"] != port or sig["protocol"] != protocol:
            continue
        if sig.get("banner_regex") and banner and not re.search(sig["banner_regex"], banner, re.IGNORECASE):
            continue
        return sig
    return None


def fingerprint_ports(open_ports: list[dict]) -> list[dict]:
    """
    Given a list of {port, protocol, banner?} dicts, return matched services.
    Unknown ports are included as unknown_service.
    """
    results = []
    for p in open_ports:
        sig = match_port(p["port"], p.get("protocol", "tcp"), p.get("banner"))
        if sig:
            results.append({
                "port": p["port"],
                "protocol": p.get("protocol", "tcp"),
                "service_name": sig["service_name"],
                "icon": sig.get("icon"),
                "category": sig.get("category"),
            })
        else:
            results.append({
                "port": p["port"],
                "protocol": p.get("protocol", "tcp"),
                "service_name": "unknown_service",
                "icon": None,
                "category": None,
            })
    return results


def suggest_node_type(open_ports: list[dict]) -> str:
    """Suggest a node type based on the most specific matched signature."""
    priority = ["proxmox", "nas", "router", "lxc", "vm", "server", "ap", "iot", "switch"]
    found: set[str] = set()
    for p in open_ports:
        sig = match_port(p["port"], p.get("protocol", "tcp"))
        if sig and sig.get("suggested_node_type"):
            found.add(sig["suggested_node_type"])
    for t in priority:
        if t in found:
            return t
    return "generic"
