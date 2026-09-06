"""VLAN detection: parse 802.1Q tags out of tcpdump output."""
from __future__ import annotations

import re

_VLAN = re.compile(r"vlan\s+(\d+)", re.IGNORECASE)


def parse_vlan_ids(text: str) -> list[int]:
    ids = {int(m.group(1)) for m in _VLAN.finditer(text)}
    return sorted(ids)
