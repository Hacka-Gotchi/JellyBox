"""System information.

Reads live CPU load, temperature, memory, disk, uptime, and load average from
``/proc``, ``/sys``, and stdlib -- no external dependencies. Works on the Pi and
on a Linux desktop; anything a given machine can't provide (e.g. no thermal
sensor) comes back as ``None`` and the page shows it as unavailable.

Parsing is split into pure helpers so it's unit-testable without the real files.
CPU percentage needs two samples over time, so :class:`CpuSampler` holds the
previous reading between refreshes.
"""
from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path

_THERMAL = "/sys/class/thermal/thermal_zone0/temp"


def parse_cpu_line(line: str) -> tuple[int, int] | None:
    """Parse the aggregate ``cpu`` line of /proc/stat -> (idle, total).

    >>> parse_cpu_line("cpu  100 0 200 700 0 0 0 0 0 0")
    (700, 1000)
    """
    parts = line.split()
    if not parts or parts[0] != "cpu":
        return None
    try:
        nums = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    if len(nums) < 5:
        return None
    idle = nums[3] + nums[4]  # idle + iowait
    return idle, sum(nums)


def parse_meminfo(text: str) -> tuple[int, int] | None:
    """Parse /proc/meminfo text -> (total_kb, available_kb).

    >>> parse_meminfo("MemTotal: 4000 kB\\nMemAvailable: 1500 kB\\n")
    (4000, 1500)
    """
    total = avail = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            total = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail = int(line.split()[1])
    if total is None or avail is None:
        return None
    return total, avail


def format_uptime(seconds: float) -> str:
    """Human-friendly uptime.

    >>> format_uptime(90)
    '1m'
    >>> format_uptime(3700)
    '1h 1m'
    >>> format_uptime(90000)
    '1d 1h'
    """
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def read_cpu_temp() -> float | None:
    """SoC temperature in °C, or None if there's no sensor."""
    try:
        milli = int(Path(_THERMAL).read_text().strip())
        return round(milli / 1000.0, 1)
    except (OSError, ValueError):
        return None


def _read_cpu_times() -> tuple[int, int] | None:
    try:
        with open("/proc/stat") as fh:
            return parse_cpu_line(fh.readline())
    except OSError:
        return None


def _read_uptime() -> float | None:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


class CpuSampler:
    """Computes CPU-busy percentage from successive /proc/stat samples."""

    def __init__(self) -> None:
        self._prev: tuple[int, int] | None = None

    def sample(self) -> float | None:
        cur = _read_cpu_times()
        if cur is None:
            return None
        prev, self._prev = self._prev, cur
        if prev is None:
            return None  # need a baseline first
        idle_d = cur[0] - prev[0]
        total_d = cur[1] - prev[1]
        if total_d <= 0:
            return None
        return round(100.0 * (1.0 - idle_d / total_d), 1)


@dataclass
class SystemSnapshot:
    cpu_pct: float | None = None
    temp_c: float | None = None
    mem_used_mb: int | None = None
    mem_total_mb: int | None = None
    mem_pct: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    disk_pct: float | None = None
    uptime_s: float | None = None
    load1: float | None = None
    hostname: str | None = None


def get_system_info(sampler: CpuSampler) -> SystemSnapshot:
    snap = SystemSnapshot()
    snap.cpu_pct = sampler.sample()
    snap.temp_c = read_cpu_temp()

    try:
        with open("/proc/meminfo") as fh:
            mem = parse_meminfo(fh.read())
        if mem:
            total_kb, avail_kb = mem
            used_kb = max(0, total_kb - avail_kb)
            snap.mem_total_mb = total_kb // 1024
            snap.mem_used_mb = used_kb // 1024
            snap.mem_pct = round(100.0 * used_kb / total_kb, 1) if total_kb else None
    except OSError:
        pass

    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        snap.disk_total_gb = round(total / 1e9, 1)
        snap.disk_used_gb = round(used / 1e9, 1)
        snap.disk_pct = round(100.0 * used / total, 1) if total else None
    except OSError:
        pass

    snap.uptime_s = _read_uptime()
    try:
        snap.load1 = round(os.getloadavg()[0], 2)
    except (OSError, AttributeError):
        snap.load1 = None
    try:
        snap.hostname = socket.gethostname()
    except OSError:
        snap.hostname = None
    return snap
