"""Ping helpers.

Builds a platform-appropriate ping command and parses its streaming output.
The command runs asynchronously via the shared ``CommandRunner`` in the page;
this module holds only the pure, testable pieces: command construction, line
parsing, and a small stats accumulator.
"""
from __future__ import annotations

import platform
import re
from dataclasses import dataclass, field

# matches "time=12.3 ms" and "time<1 ms" (Windows)
_RTT_RE = re.compile(r"time[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)
# matches the Linux/mac summary line "3 packets transmitted, 3 received, 0% packet loss"
_SUMMARY_RE = re.compile(
    r"(\d+)\s+packets? transmitted,\s*(\d+)\s+(?:packets? )?received.*?(\d+(?:\.\d+)?)%",
    re.IGNORECASE,
)


def build_ping_command(target: str, count: int = 10, timeout_s: int = 1) -> list[str]:
    """Return the argv for pinging ``target`` ``count`` times."""
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", str(count), "-w", str(int(timeout_s * 1000)), target]
    cmd = ["ping", "-c", str(count)]
    if system == "linux":
        cmd += ["-W", str(int(timeout_s))]  # per-reply timeout, seconds
    return cmd + [target]


def parse_rtt(line: str) -> float | None:
    """Extract a round-trip time in ms from a reply line, or None."""
    m = _RTT_RE.search(line)
    return float(m.group(1)) if m else None


def parse_summary(line: str) -> tuple[int, int, float] | None:
    """Extract (transmitted, received, loss_pct) from a summary line, or None."""
    m = _SUMMARY_RE.search(line)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), float(m.group(3))


@dataclass
class PingStats:
    target: str
    replies: list[float] = field(default_factory=list)
    transmitted: int = 0
    received: int = 0

    def add_reply(self, rtt: float) -> None:
        self.replies.append(rtt)

    def apply_summary(self, transmitted: int, received: int) -> None:
        self.transmitted = transmitted
        self.received = received

    @property
    def loss_pct(self) -> int:
        sent = self.transmitted or len(self.replies)
        recv = self.received or len(self.replies)
        if sent <= 0:
            return 0
        return round(100 * (sent - recv) / sent)

    @property
    def avg_ms(self) -> float | None:
        return round(sum(self.replies) / len(self.replies), 1) if self.replies else None

    @property
    def last_ms(self) -> float | None:
        return self.replies[-1] if self.replies else None
