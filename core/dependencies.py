"""Optional dependency detection.

Detects which external tools are available so pages can degrade gracefully
("NMAP NOT INSTALLED") instead of crashing. Detection happens once
at startup via ``shutil.which`` and is cached.
"""
from __future__ import annotations

import logging
import shutil

log = logging.getLogger(__name__)

OPTIONAL_TOOLS = ("nmap", "nmcli", "iw", "ping", "ssh", "traceroute", "lldpctl", "tcpdump")


class Dependencies:
    def __init__(self, tools: tuple[str, ...] = OPTIONAL_TOOLS) -> None:
        self._paths: dict[str, str | None] = {t: shutil.which(t) for t in tools}
        present = [t for t, p in self._paths.items() if p]
        missing = [t for t, p in self._paths.items() if not p]
        log.info("dependencies present: %s", ", ".join(present) or "(none)")
        if missing:
            log.info("dependencies missing: %s", ", ".join(missing))

    def has(self, tool: str) -> bool:
        if tool not in self._paths:
            self._paths[tool] = shutil.which(tool)
        return self._paths[tool] is not None

    def path(self, tool: str) -> str | None:
        return self._paths.get(tool) or shutil.which(tool)

    def missing(self) -> list[str]:
        return [t for t, p in self._paths.items() if not p]

    def as_dict(self) -> dict[str, bool]:
        return {t: p is not None for t, p in self._paths.items()}
