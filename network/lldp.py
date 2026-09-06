"""LLDP neighbor parsing (from ``lldpctl -f keyvalue``)."""
from __future__ import annotations


def parse_lldp(text: str) -> list[dict]:
    """Group lldpctl keyvalue output into one dict per neighbor interface."""
    neighbors: dict[str, dict] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip()
        parts = key.split(".")
        if len(parts) < 3 or parts[0] != "lldp":
            continue
        iface = parts[1]
        n = neighbors.setdefault(iface, {"iface": iface})
        low = key.lower()
        if "chassis.name" in low:
            n["name"] = val
        elif "port.descr" in low or "port.ifname" in low:
            n.setdefault("port", val)
        elif "vlan-id" in low:
            n["vlan"] = val
        elif "mgmt-ip" in low or "mgmt.ip" in low:
            n.setdefault("mgmt", val)
    return list(neighbors.values())
