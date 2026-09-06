"""Wi-Fi helpers.

Builds nmcli commands and parses their output. The scan itself runs
asynchronously via the shared CommandRunner in the page; this module holds only
the pure, testable pieces. nmcli is used (rather than raw ``iw``) because it
lists networks without root and gives signal + security in one shot.

nmcli's terse mode (``-t``) is colon-separated and escapes literal colons inside
a field as ``\\:``, so the splitter below unescapes as it goes.
"""
from __future__ import annotations

from dataclasses import dataclass

_FIELDS = "IN-USE,SSID,SIGNAL,SECURITY"


@dataclass
class WifiNetwork:
    ssid: str
    signal: int          # 0-100
    security: str        # e.g. "WPA2", "" / "--" for open
    in_use: bool = False

    @property
    def secured(self) -> bool:
        return self.security not in ("", "--")


def build_scan_command(rescan: bool = False, iface: str | None = None) -> list[str]:
    cmd = ["nmcli", "-t", "-f", _FIELDS, "device", "wifi", "list"]
    if iface:
        cmd += ["ifname", iface]
    if rescan:
        cmd += ["--rescan", "yes"]
    return cmd


def build_active_command() -> list[str]:
    """Cheap query (no forced rescan) to read the current connection."""
    return ["nmcli", "-t", "-f", _FIELDS, "device", "wifi"]


def build_connect_command(ssid: str, password: str | None = None,
                          iface: str | None = None) -> list[str]:
    """nmcli command to join a network (saves the connection)."""
    cmd = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        cmd += ["password", password]
    if iface:
        cmd += ["ifname", iface]
    return cmd


def connect_ok(text: str) -> bool:
    return "successfully activated" in text.lower()


def split_terse(line: str) -> list[str]:
    """Split an nmcli ``-t`` line on unescaped colons, unescaping ``\\:``."""
    fields: list[str] = []
    cur = ""
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            cur += line[i + 1]
            i += 2
            continue
        if c == ":":
            fields.append(cur)
            cur = ""
            i += 1
            continue
        cur += c
        i += 1
    fields.append(cur)
    return fields


def parse_wifi_line(line: str) -> WifiNetwork | None:
    if not line.strip():
        return None
    f = split_terse(line)
    if len(f) < 4:
        return None
    try:
        signal = int(f[2])
    except ValueError:
        signal = 0
    return WifiNetwork(
        ssid=f[1],
        signal=signal,
        security=f[3].strip(),
        in_use=f[0].strip() == "*",
    )


def parse_scan_output(text: str) -> list[WifiNetwork]:
    """Parse a scan into a de-duplicated list, strongest signal first."""
    best: dict[str, WifiNetwork] = {}
    for line in text.splitlines():
        n = parse_wifi_line(line)
        if n is None or not n.ssid:  # skip hidden / empty SSIDs
            continue
        cur = best.get(n.ssid)
        if cur is None or n.signal > cur.signal:
            best[n.ssid] = n
    return sorted(best.values(), key=lambda n: (-n.signal, n.ssid.lower()))


def parse_active(text: str) -> tuple[str | None, int | None]:
    """Return (ssid, signal) of the in-use network, or (None, None)."""
    for line in text.splitlines():
        n = parse_wifi_line(line)
        if n and n.in_use and n.ssid:
            return n.ssid, n.signal
    return None, None
