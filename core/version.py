"""JellyBox version.

Deployed devices sit on a release tag (detached HEAD); development is on main.
current_version() prefers the git tag so a deployed unit reports its release,
falling back to the VERSION file so it still works offline or in a non-git copy.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"


def read_version_file(path: Path = VERSION_FILE) -> str | None:
    try:
        return path.read_text().strip() or None
    except OSError:
        return None


def _git_describe(repo_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "describe", "--tags", "--exact-match"],
            capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    tag = result.stdout.strip()
    return tag if result.returncode == 0 and tag else None


def current_version() -> str:
    return _git_describe(VERSION_FILE.parent) or read_version_file() or "unknown"
