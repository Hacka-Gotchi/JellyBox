"""Persistent application settings.

All settings live in a single JSON file. Pages and services must go through
``Settings`` rather than reading or writing the JSON directly, and
writes are atomic so a power loss mid-write cannot corrupt the file or the SD
card.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Defaults live here, in one place. Anything missing from settings.json is
# filled in from these, so upgrading the app never breaks an old config.
DEFAULTS: dict[str, Any] = {
    "theme": "green",
    "brightness": 70,
    "wifi_interface": None,  # None = let the OS choose; else a specific interface
    "ssh_host": "",
    "ssh_user": "",
    "ssh_cmd": "uptime",
    "nmap_args": "-Pn -F -T4",
}


@dataclass
class Settings:
    """Loads, exposes, and persists user settings.

    Use :meth:`load` to construct from disk. Values survive reboot because
    :meth:`save` writes them back to ``path``.
    """

    path: Path
    _values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Settings":
        p = Path(path)
        values = dict(DEFAULTS)
        try:
            with p.open("r", encoding="utf-8") as fh:
                on_disk = json.load(fh)
            if isinstance(on_disk, dict):
                values.update({k: v for k, v in on_disk.items() if k in DEFAULTS})
            else:
                log.warning("settings file %s is not a JSON object; using defaults", p)
        except FileNotFoundError:
            log.info("no settings file at %s; using defaults", p)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("could not read settings (%s); using defaults", exc)
        return cls(path=p, _values=values)

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Update a value in memory. Call :meth:`save` to persist it."""
        self._values[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def save(self) -> None:
        """Write settings atomically (temp file + rename)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp = tempfile.mkstemp(
                dir=str(self.path.parent), prefix=".settings-", suffix=".tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._values, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)  # atomic on POSIX
            log.debug("settings saved to %s", self.path)
        except OSError as exc:
            log.error("failed to save settings: %s", exc)
