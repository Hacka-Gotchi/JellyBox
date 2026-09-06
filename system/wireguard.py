"""WireGuard helpers.

Pure parsers for the privileged helper's output (tunnel list, active interfaces
from ``wg show``, and a short status summary). Bringing tunnels up/down happens
via the root helper (scripts/jellybox-wg).
"""
from __future__ import annotations


def parse_tunnel_list(text: str) -> list[str]:
    """One tunnel name per line -> sorted list."""
    return sorted(l.strip() for l in text.splitlines() if l.strip())


def parse_active_interfaces(text: str) -> set[str]:
    """From ``wg show`` output, the set of up tunnel names.

    >>> parse_active_interfaces("interface: wg0\\n  public key: x\\ninterface: home\\n")
    {'home', 'wg0'}
    """
    active = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("interface:"):
            active.add(line.split(":", 1)[1].strip())
    return active


def parse_handshake(text: str, name: str) -> str | None:
    """Latest-handshake line for a given tunnel, if present."""
    current = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("interface:"):
            current = s.split(":", 1)[1].strip()
        elif s.startswith("latest handshake:") and current == name:
            return s.split(":", 1)[1].strip()
    return None
