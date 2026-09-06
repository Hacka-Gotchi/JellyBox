"""WiFi connection status (for the header icons).

Reads Wi-Fi link quality from ``/proc/net/wireless`` and wired-link state from
sysfs, and caches the result (timestamped) so the header can show live signal
and Ethernet icons without stalling the render loop.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WifiStatus:
    connected: bool = False      # Wi-Fi associated
    quality: int = 0             # 0-100
    iface: str | None = None
    eth: bool = False            # a wired link is up


def is_wired_link(has_wireless: bool, has_device: bool, carrier: str) -> bool:
    """Decide whether a sysfs interface is a live wired link.

    Judged by characteristics rather than a name prefix, so predictable and
    USB names (enp2s0, enx0011...) are covered and Wi-Fi is never counted:
    a wired link is not wireless, is backed by real hardware (has a ``device``
    symlink, which excludes veth/bridges), and has carrier.

    >>> is_wired_link(has_wireless=False, has_device=True, carrier="1")
    True
    >>> is_wired_link(has_wireless=True, has_device=True, carrier="1")
    False
    >>> is_wired_link(has_wireless=False, has_device=False, carrier="1")
    False
    """
    if has_wireless or not has_device:
        return False
    return carrier.strip() == "1"


def eth_connected() -> bool:
    """True if any wired interface has a live link."""
    base = Path("/sys/class/net")
    try:
        entries = list(base.iterdir())
    except OSError:
        return False
    for p in entries:
        if p.name == "lo":
            continue
        has_wireless = (p / "wireless").exists() or (p / "phy80211").exists()
        has_device = (p / "device").exists()
        try:
            carrier = (p / "carrier").read_text()
        except OSError:
            continue
        if is_wired_link(has_wireless, has_device, carrier):
            return True
    return False


def parse_proc_wireless(text: str) -> WifiStatus:
    """Parse /proc/net/wireless -> WifiStatus (first associated interface).

    >>> parse_proc_wireless(
    ...   "Inter-| sta\\n face | sta\\n wlan0: 0000   65.  -45.  -256\\n").connected
    True
    """
    for line in text.splitlines()[2:]:  # skip two header rows
        if ":" not in line:
            continue
        name, _, rest = line.partition(":")
        fields = rest.split()
        if len(fields) < 2:
            continue
        try:
            link = float(fields[1].rstrip("."))
        except ValueError:
            continue
        return WifiStatus(
            connected=link > 0,
            quality=max(0, min(100, int(link / 70.0 * 100))),
            iface=name.strip(),
        )
    return WifiStatus()


class WifiProvider:
    def read(self) -> WifiStatus:
        raise NotImplementedError


class SysfsWifiProvider(WifiProvider):
    def read(self) -> WifiStatus:
        wired = eth_connected()
        try:
            wifi = parse_proc_wireless(Path("/proc/net/wireless").read_text())
        except OSError:
            wifi = WifiStatus()
        return WifiStatus(connected=wifi.connected, quality=wifi.quality,
                          iface=wifi.iface, eth=wired)


class WifiManager:
    def __init__(self, provider: WifiProvider, refresh_seconds: float = 5.0) -> None:
        self._provider = provider
        self._refresh = refresh_seconds
        self._cached = WifiStatus()
        self._last = 0.0
        self._primed = False

    @property
    def status(self) -> WifiStatus:
        now = time.monotonic()
        if not self._primed or (now - self._last) >= self._refresh:
            try:
                self._cached = self._provider.read()
            except Exception:
                log.warning("wifi read failed", exc_info=True)
                self._cached = WifiStatus()
            self._last = now
            self._primed = True
        return self._cached
