"""GitHub release checking for SYSTEM UPDATE.

Pure helpers: build the releases API URL, parse the latest release, validate a
release tag, and compare versions. The page does the HTTP fetch (short timeout,
offline-tolerant) and hands the response text here.
"""
from __future__ import annotations

import json
import re

OWNER = "Hacka-Gotchi"
REPO = "JellyBox"

_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
_PARTS_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def releases_api_url(owner: str = OWNER, repo: str = REPO) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"


def parse_latest_release(text: str) -> dict | None:
    """Return {'tag', 'notes'} from the releases/latest JSON, or None."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    tag = (data.get("tag_name") or "").strip()
    if not tag:
        return None
    return {"tag": tag, "notes": (data.get("body") or "").strip()}


def is_valid_tag(tag: str) -> bool:
    """Only accept vMAJOR.MINOR.PATCH, so an arbitrary string can't be checked out."""
    return bool(_TAG_RE.match(tag or ""))


def _parts(version: str):
    match = _PARTS_RE.match(version or "")
    return tuple(int(x) for x in match.groups()) if match else None


def is_newer(current: str, latest: str) -> bool:
    """True if ``latest`` is a newer release than ``current``.

    >>> is_newer("v1.0.0", "v1.1.0")
    True
    >>> is_newer("v1.2.0", "v1.2.0")
    False
    >>> is_newer("v1.3.0", "v1.2.0")
    False
    """
    current_parts = _parts(current)
    latest_parts = _parts(latest)
    if latest_parts is None:
        return False
    if current_parts is None:
        return True
    return latest_parts > current_parts
