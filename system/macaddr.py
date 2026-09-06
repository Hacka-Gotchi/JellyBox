"""MAC address helpers for the spoofing tool.

Generating and validating MACs is pure and unit-tested. Reading the current MAC
comes from sysfs (no root); the permanent (factory) MAC is read via ethtool,
which is unprivileged. Actually changing a MAC needs root and goes through the
privileged helper (see scripts/jellybox-iface).
"""
from __future__ import annotations

import random
import re
from pathlib import Path

_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def random_mac() -> str:
    """A random locally-administered, unicast MAC.

    The first octet has the locally-administered bit set (0x02) and the
    multicast bit cleared, which is the correct form for a spoofed address.
    """
    first = (random.randint(0, 255) & 0xFE) | 0x02
    octets = [first] + [random.randint(0, 255) for _ in range(5)]
    return ":".join(f"{o:02x}" for o in octets)


def is_valid_mac(value: str) -> bool:
    """>>> is_valid_mac("00:c0:ca:b9:a9:fc")
    True
    >>> is_valid_mac("00:c0:ca:b9:a9")
    False
    """
    return bool(_MAC_RE.match(value.strip()))


def current_mac(iface: str) -> str | None:
    try:
        return Path(f"/sys/class/net/{iface}/address").read_text().strip() or None
    except OSError:
        return None


def parse_ethtool_permanent(text: str) -> str | None:
    """Extract the permanent MAC from ``ethtool -P`` output."""
    for line in text.splitlines():
        if "permanent address" in line.lower():
            _, _, mac = line.partition(":")
            mac = mac.strip()
            return mac if is_valid_mac(mac) else None
    return None
