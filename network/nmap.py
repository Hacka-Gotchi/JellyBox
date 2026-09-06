"""Nmap helpers.

Builds a fast, unprivileged nmap command and parses its output for open ports.
Runs unprivileged, so nmap uses a TCP connect scan automatically -- no root
needed. The scan runs asynchronously via the shared CommandRunner in the page;
this module holds only the pure, testable pieces.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# "22/tcp   open  ssh"  /  "80/tcp open http"
_PORT_RE = re.compile(r"^(\d+)/(tcp|udp)\s+(\S+)\s*(.*)$", re.IGNORECASE)


@dataclass
class Port:
    number: int
    proto: str
    state: str
    service: str = ""


DEFAULT_ARGS = "-Pn -F -T4"


def build_nmap_command(target: str, args: str = DEFAULT_ARGS) -> list[str]:
    """nmap with user-supplied flags. Args are split on spaces (no shell), so
    there's no injection surface. -Pn in the default keeps ping-blocking hosts
    scannable; the user can change any of it."""
    parts = (args or DEFAULT_ARGS).split()
    return ["nmap"] + parts + [target]


def parse_port_line(line: str) -> Port | None:
    m = _PORT_RE.match(line.strip())
    if not m:
        return None
    return Port(int(m.group(1)), m.group(2).lower(), m.group(3).lower(),
                m.group(4).strip())


def parse_open_ports(text: str) -> list[Port]:
    ports = [p for line in text.splitlines()
             if (p := parse_port_line(line)) and p.state == "open"]
    return sorted(ports, key=lambda p: p.number)


def host_is_up(text: str) -> bool:
    return "host is up" in text.lower()


# Phrases nmap prints when the *arguments* are wrong (bad flag, bad port spec…).
_ARG_ERR_MARKERS = (
    "unrecognized option",
    "port specification",
    "ports specified",
    "illegal",
    "invalid argument",
    "requires an argument",
    "error #",
    "quitting",
)


def scan_error(text: str, returncode: int | None) -> str | None:
    """Return a short error label if the scan failed, else None.

    Distinguishes a bad target from bad arguments so the user knows what to fix.
    """
    low = text.lower()
    if "failed to resolve" in low or "could not resolve" in low:
        return "BAD HOST"
    if any(m in low for m in _ARG_ERR_MARKERS):
        return "ARG ERROR!"
    if returncode not in (0, None) and "nmap scan report" not in low:
        return "SCAN ERROR"
    return None
