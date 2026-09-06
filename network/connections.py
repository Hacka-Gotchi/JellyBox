"""Saved NetworkManager connections (list + delete)."""
from __future__ import annotations

from network.wifi import split_terse


def build_list_connections_command() -> list[str]:
    return ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]


def build_delete_connection_command(name: str) -> list[str]:
    return ["nmcli", "connection", "delete", name]


def parse_wifi_connections(text: str) -> list[str]:
    """Names of saved Wi-Fi connections."""
    out = []
    for line in text.splitlines():
        parts = split_terse(line)
        if len(parts) >= 2 and "wireless" in parts[1].lower():
            out.append(parts[0])
    return out
