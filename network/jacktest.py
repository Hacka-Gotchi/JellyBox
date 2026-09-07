"""JACK TEST helpers.

Collects a one-shot picture of an unknown Ethernet jack: link, speed/duplex,
IP/gateway/DHCP, LLDP switch name/port, and observed VLAN IDs. The pure parsers
and command builders live here; the page runs the (short-timeout) commands on a
background thread and fills a :class:`JackResult`.

Nothing here changes network or switch configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from network.lldp import parse_lldp

_NET = Path("/sys/class/net")


@dataclass
class JackResult:
    interface: str | None = None
    link: bool = False
    speed_mbps: int | None = None
    duplex: str | None = None            # "full" / "half"
    dhcp: str = "?"                       # YES / STATIC / NONE / ?
    ip: str | None = None
    gateway: str | None = None
    switch_name: str | None = None       # from LLDP
    switch_port: str | None = None       # from LLDP
    vlans: list[int] = field(default_factory=list)


def format_speed(mbps: int | None) -> str:
    """Human speed label.

    >>> format_speed(100)
    '100M'
    >>> format_speed(1000)
    '1G'
    >>> format_speed(2500)
    '2.5G'
    >>> format_speed(None)
    '?'
    """
    if not mbps or mbps <= 0:
        return "?"
    if mbps >= 1000:
        return f"{mbps / 1000:g}G"
    return f"{mbps}M"


def parse_nmcli_device(text: str) -> dict:
    """Parse ``nmcli -t -f IP4.ADDRESS,IP4.GATEWAY,DHCP4.OPTION device show``.

    Returns ``{"ip", "gateway", "dhcp"}`` where ``dhcp`` is True when the device
    holds a DHCP lease (DHCP4 options are present).
    """
    ip = gateway = None
    dhcp = False
    for line in text.splitlines():
        key, _, value = line.partition(":")
        key = key.strip().upper()
        value = value.strip()
        if key.startswith("IP4.ADDRESS") and value and ip is None:
            ip = value.split("/")[0]
        elif key == "IP4.GATEWAY" and value:
            gateway = value
        elif key.startswith("DHCP4.OPTION"):
            dhcp = True
    return {"ip": ip, "gateway": gateway, "dhcp": dhcp}


def dhcp_status(ip: str | None, dhcp_lease: bool) -> str:
    if dhcp_lease:
        return "YES"
    return "STATIC" if ip else "NONE"


def lldp_switch_info(lldp_text: str, interface: str | None) -> tuple[str | None, str | None]:
    """Switch name and port for ``interface`` from lldpctl output, if advertised."""
    neighbors = parse_lldp(lldp_text)
    for neighbor in neighbors:
        if interface is None or neighbor.get("iface") == interface:
            return neighbor.get("name"), neighbor.get("port")
    if neighbors:  # fall back to the first neighbor if the interface didn't match
        return neighbors[0].get("name"), neighbors[0].get("port")
    return None, None


def summary_line(result: "JackResult", label: str = "") -> str:
    """One-line summary for a saved result.

    With a label it reads like 'Room 205 / SW-03 / Gi1/0/17 / VLAN 120'; the
    switch/port/VLAN fields are included when advertised and fall back to the IP
    so the line is still meaningful on jacks without LLDP.
    """
    parts: list[str] = []
    if label.strip():
        parts.append(label.strip())
    if result.switch_name:
        parts.append(result.switch_name)
    if result.switch_port:
        parts.append(result.switch_port)
    if result.vlans:
        parts.append("VLAN " + ",".join(str(v) for v in result.vlans))
    if result.ip and not (result.switch_name or result.switch_port or result.vlans):
        parts.append(result.ip)
    if not parts:
        parts.append("LINK UP" if result.link else "LINK DOWN")
    return " / ".join(parts)


def build_device_show_command(interface: str) -> list[str]:
    return ["nmcli", "-t", "-f", "IP4.ADDRESS,IP4.GATEWAY,DHCP4.OPTION",
            "device", "show", interface]


def build_lldp_command() -> list[str]:
    return ["lldpctl", "-f", "keyvalue"]


def build_vlan_command(interface: str,
                       helper: str = "/usr/local/sbin/jellybox-sniff") -> list[str]:
    return ["sudo", "-n", helper, "vlan", interface]


# --- sysfs reads (unprivileged, no external tools) ---

def _read(interface: str, attr: str) -> str:
    try:
        return (_NET / interface / attr).read_text().strip()
    except OSError:
        return ""


def read_link(interface: str) -> bool:
    return _read(interface, "carrier") == "1"


def read_speed(interface: str) -> int | None:
    try:
        speed = int(_read(interface, "speed"))
    except ValueError:
        return None
    return speed if speed > 0 else None


def read_duplex(interface: str) -> str | None:
    duplex = _read(interface, "duplex")
    return duplex if duplex in ("full", "half") else None


def wired_interface() -> str | None:
    """The wired interface to test: an ethernet port with a live link if any,
    otherwise the first ethernet port, otherwise None."""
    from system.devices import list_network_interfaces

    ethernet = [i.name for i in list_network_interfaces() if i.kind == "ethernet"]
    for name in ethernet:
        if read_link(name):
            return name
    return ethernet[0] if ethernet else None
