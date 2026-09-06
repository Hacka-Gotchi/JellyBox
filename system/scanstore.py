"""Saved-scan storage.

Persists scan results as timestamped text files under ``data/scans/`` so they
survive reboots and can be reviewed later (TOOLS -> SCANS). Kept dependency-free
and simple; filenames are sanitised so a target can't escape the folder.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

SCANS_DIR = Path(__file__).resolve().parents[1] / "data" / "scans"

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(text: str) -> str:
    return _SAFE.sub("_", text).strip("_") or "x"


def save_scan(kind: str, target: str, lines: list[str]) -> str:
    """Write a scan to disk; returns the filename saved."""
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}_{_safe(kind)}_{_safe(target)}.txt"
    header = f"# {kind} scan of {target}\n# {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    (SCANS_DIR / name).write_text(header + "\n".join(lines) + "\n")
    return name


def list_scans() -> list[str]:
    """Saved scan filenames, newest first."""
    try:
        files = [p.name for p in SCANS_DIR.glob("*.txt")]
    except OSError:
        return []
    return sorted(files, reverse=True)


def read_scan(name: str) -> list[str]:
    """Lines of a saved scan (safe: only reads within the scans folder)."""
    if "/" in name or "\\" in name or ".." in name:
        return []
    try:
        return (SCANS_DIR / name).read_text().splitlines()
    except OSError:
        return []
