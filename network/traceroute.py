"""Traceroute helper: build the command; output is streamed as-is."""
from __future__ import annotations


def build_traceroute_command(target: str, max_hops: int = 20) -> list[str]:
    # -n numeric, -w 2s wait, -q 1 query/hop for speed. Default UDP mode is
    # unprivileged, so no root needed.
    return ["traceroute", "-n", "-w", "2", "-q", "1", "-m", str(max_hops), target]
