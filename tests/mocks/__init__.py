"""Test doubles for JellyBox.

These fakes stand in for hardware and shared services so UI and logic can be
tested without a Raspberry Pi. Production code never imports from here.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.command_runner import CommandRunner
from core.dependencies import Dependencies
from core.settings import Settings
from hardware.buttons import InputSource
from network.wifi_status import WifiManager, WifiProvider, WifiStatus
from ui.page_manager import PageManager
from ui.theme import Theme


class FakeButtons(InputSource):
    """An input source that never produces events; tests drive pages directly."""

    def poll(self):
        return []


class FakeWifiProvider(WifiProvider):
    """A WifiProvider returning a fixed status."""

    def __init__(self, connected: bool = True, quality: int = 66,
                 eth: bool = False) -> None:
        self._status = WifiStatus(connected=connected, quality=quality,
                                  iface="wlan0", eth=eth)

    def read(self) -> WifiStatus:
        return self._status


def make_context(theme: str = "green", *, wifi: bool = False, eth: bool = False,
                 settings_path: str | None = None):
    """Build an AppContext backed by fakes and a throwaway settings file."""
    from core.app import AppContext

    path = settings_path or (Path(tempfile.mkdtemp()) / "settings.json")
    return AppContext(
        settings=Settings.load(path),
        theme=Theme(theme),
        buttons=FakeButtons(),
        pages=PageManager(),
        commands=CommandRunner(),
        deps=Dependencies(),
        wifi=WifiManager(FakeWifiProvider(connected=wifi, eth=eth)),
    )
