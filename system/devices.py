"""Connected-device discovery.

Enumerates network interfaces and USB devices from ``/sys`` -- no external
commands, no root. Everything degrades gracefully: on a machine without a USB
sysfs tree (e.g. a container) the USB list is simply empty.

The interface classifier (wifi / ethernet / loopback) is a pure function so it's
unit-testable without real hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_NET = Path("/sys/class/net")
_USB = Path("/sys/bus/usb/devices")


def _read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


@dataclass
class NetIface:
    name: str
    kind: str          # "wifi" | "ethernet" | "loopback" | "other"
    state: str         # operstate: up / down / unknown
    mac: str | None = None

    @property
    def is_wifi(self) -> bool:
        return self.kind == "wifi"


def classify_iface(name: str, has_wireless: bool, has_device: bool) -> str:
    """Pure classifier for an interface .

    >>> classify_iface("lo", False, False)
    'loopback'
    >>> classify_iface("wlan1", True, True)
    'wifi'
    >>> classify_iface("eth0", False, True)
    'ethernet'
    """
    if name == "lo":
        return "loopback"
    if has_wireless:
        return "wifi"
    if has_device:
        return "ethernet"
    return "other"


def list_network_interfaces(include_loopback: bool = False) -> list[NetIface]:
    out: list[NetIface] = []
    if not _NET.exists():
        return out
    for p in sorted(_NET.iterdir()):
        name = p.name
        has_wireless = (p / "wireless").exists() or (p / "phy80211").exists()
        has_device = (p / "device").exists()
        kind = classify_iface(name, has_wireless, has_device)
        if kind == "loopback" and not include_loopback:
            continue
        out.append(NetIface(
            name=name,
            kind=kind,
            state=_read(p / "operstate") or "unknown",
            mac=_read(p / "address") or None,
        ))
    # wifi first, then ethernet, then others; stable by name within a kind
    order = {"wifi": 0, "ethernet": 1, "other": 2, "loopback": 3}
    return sorted(out, key=lambda i: (order.get(i.kind, 9), i.name))


def mode_from_arphrd(type_str: str) -> str:
    """Map an interface's /sys ARPHRD type to a mode name.

    1 = ARPHRD_ETHER (managed), 803 = ARPHRD_IEEE80211_RADIOTAP (monitor).

    >>> mode_from_arphrd("803")
    'monitor'
    >>> mode_from_arphrd("1")
    'managed'
    """
    return "monitor" if type_str.strip() == "803" else "managed"


def iface_mode(name: str) -> str:
    """Current mode of an interface ('managed' or 'monitor'), read from sysfs."""
    return mode_from_arphrd(_read(_NET / name / "type"))


def iface_driver(name: str) -> str | None:
    """Kernel driver bound to an interface, e.g. 'brcmfmac' or '8821au'."""
    import os
    link = _NET / name / "device" / "driver"
    try:
        return os.path.basename(os.readlink(link))
    except OSError:
        return None


@dataclass
class UsbDevice:
    name: str
    vid: str
    pid: str


def list_usb_devices() -> list[UsbDevice]:
    """USB end-devices (root/hub devices are filtered out to reduce noise)."""
    out: list[UsbDevice] = []
    if not _USB.exists():
        return out
    for p in sorted(_USB.iterdir()):
        if ":" in p.name:          # interface entries, not devices
            continue
        if not (p / "idVendor").exists():
            continue
        if _read(p / "bDeviceClass") == "09":  # hub
            continue
        vid = _read(p / "idVendor")
        pid = _read(p / "idProduct")
        name = _read(p / "product") or _read(p / "manufacturer") or f"{vid}:{pid}"
        out.append(UsbDevice(name=name, vid=vid, pid=pid))
    return out
