"""Per-device configuration, read from outside the source tree.

Calibration and per-unit settings live in /etc/jellybox/device.json rather than
in tracked source, so a software update can replace the whole application tree
without touching a device's display offsets. Example:

    {"display": {"x_offset": 1, "y_offset": 2, "rotate": 0}}
"""
from __future__ import annotations

import json
from pathlib import Path

DEVICE_CONFIG_PATH = Path("/etc/jellybox/device.json")


def load_device_config(path: Path = DEVICE_CONFIG_PATH) -> dict:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def display_overrides(config: dict) -> dict:
    """The 'display' section of the config, or an empty dict."""
    display = config.get("display") if isinstance(config, dict) else None
    return display if isinstance(display, dict) else {}
