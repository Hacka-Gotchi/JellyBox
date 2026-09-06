"""TOOLS submenu.

A home for smaller utilities that don't each need a top-level menu slot. Uses
the same list/navigation pattern as the main menu, so adding a tool is one entry
plus its page.
"""
from __future__ import annotations

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from ui.components.header import draw_header
from ui.components.menu import Menu
from ui.page_manager import Page
from ui.pages.lldp import LldpPage
from ui.pages.mac_spoof import MacSpoofPage
from ui.pages.nmap_scan import NmapScanPage
from ui.pages.ping import PingPage
from ui.pages.saved_scans import SavedScansPage
from ui.pages.traceroute import TraceroutePage
from ui.pages.vlan import VlanPage
from ui.pages.wifi_scan import WifiScanPage
from ui.pages.wireguard import WireGuardPage
from ui.renderer import CONTENT_TOP

TOOL_ITEMS = ["WIFI SCAN", "PING", "TRACEROUTE", "NMAP", "LLDP", "VLAN",
              "MAC SPOOF", "WIREGUARD", "RESULTS"]


class ToolsPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.menu = Menu(TOOL_ITEMS, wrap=True)

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if btn is Button.UP:
            self.menu.up()
        elif btn is Button.DOWN:
            self.menu.down()
        elif btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.CENTER:
            self._open(self.menu.current)

    def _open(self, item: str | None) -> None:
        page = {
            "WIFI SCAN": lambda: WifiScanPage(self.ctx),
            "PING": lambda: PingPage(self.ctx),
            "TRACEROUTE": lambda: TraceroutePage(self.ctx),
            "NMAP": lambda: NmapScanPage(self.ctx),
            "LLDP": lambda: LldpPage(self.ctx),
            "VLAN": lambda: VlanPage(self.ctx),
            "MAC SPOOF": lambda: MacSpoofPage(self.ctx),
            "WIREGUARD": lambda: WireGuardPage(self.ctx),
            "RESULTS": lambda: SavedScansPage(self.ctx),
        }.get(item or "")
        if page:
            self.ctx.pages.push(page())

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(display, theme, "TOOLS",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        self.menu.draw(display, theme, top_y=CONTENT_TOP)
