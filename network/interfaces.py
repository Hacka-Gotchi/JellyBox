"""Network interface information.

Gathers the local interface, IPv4 address, default gateway, hostname, and MAC.
Written Linux-first (JellyBox runs on Raspberry Pi OS) but
degrades gracefully elsewhere so it is still useful during desktop development:
whatever can't be determined comes back as ``None`` and the page shows it as
unknown rather than failing.

The interface name is discovered, never assumed to be ``wlan0``.
Parsing is split into pure helpers so it can be unit-tested without a live
network.
"""
from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class NetInfo:
    hostname: str | None = None
    interface: str | None = None
    ipv4: str | None = None
    gateway: str | None = None
    mac: str | None = None

    def as_fields(self) -> list[tuple[str, str]]:
        """Ordered (label, value) pairs for display; unknowns show as '-'."""
        def v(x: str | None) -> str:
            return x if x else "-"
        return [
            ("HOST", v(self.hostname)),
            ("IFACE", v(self.interface)),
            ("IPV4", v(self.ipv4)),
            ("GATEWAY", v(self.gateway)),
            ("MAC", v(self.mac)),
        ]


def local_ipv4() -> str | None:
    """Best-effort primary IPv4 via a UDP socket (no packets are sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # only sets the socket's local endpoint
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


def parse_proc_net_route(text: str) -> tuple[str | None, str | None]:
    """Parse ``/proc/net/route`` text -> (gateway_ip, interface).

    Returns the gateway of the default route (destination 0.0.0.0 with the
    RTF_GATEWAY flag). Gateway/destination fields are little-endian hex.

    >>> parse_proc_net_route(
    ...     "Iface\\tDestination\\tGateway\\tFlags\\tRefCnt\\tUse\\tMetric\\tMask\\n"
    ...     "eth0\\t00000000\\t010200C0\\t0003\\t0\\t0\\t0\\t00000000\\t0\\t0\\t0\\n")
    ('192.0.2.1', 'eth0')
    """
    for line in text.splitlines()[1:]:  # skip header
        fields = line.split()
        if len(fields) < 4:
            continue
        iface, dest_hex, gw_hex, flags_hex = fields[0], fields[1], fields[2], fields[3]
        try:
            dest = int(dest_hex, 16)
            flags = int(flags_hex, 16)
        except ValueError:
            continue
        RTF_GATEWAY = 0x2
        if dest == 0 and (flags & RTF_GATEWAY):
            try:
                gw = socket.inet_ntoa(bytes.fromhex(gw_hex)[::-1])
            except (ValueError, OSError):
                gw = None
            return gw, iface
    return None, None


def default_route() -> tuple[str | None, str | None]:
    """Return (gateway_ip, interface) for the default route, or (None, None)."""
    try:
        text = Path("/proc/net/route").read_text()
    except OSError:
        return None, None
    return parse_proc_net_route(text)


def mac_of(interface: str) -> str | None:
    try:
        return Path(f"/sys/class/net/{interface}/address").read_text().strip() or None
    except OSError:
        return None


def get_network_info() -> NetInfo:
    """Assemble a best-effort snapshot of the current network state."""
    gateway, interface = default_route()
    try:
        hostname = socket.gethostname()
    except OSError:
        hostname = None
    return NetInfo(
        hostname=hostname,
        interface=interface,
        ipv4=local_ipv4(),
        gateway=gateway,
        mac=mac_of(interface) if interface else None,
    )
