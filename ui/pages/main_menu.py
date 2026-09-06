"""The JellyBox main menu.

Lists the top-level areas and opens the selected one. A long press of CENTER
cycles the theme as a shortcut (the same setting is available under Settings).
"""
from __future__ import annotations

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from ui.components.header import draw_header
from ui.components.menu import Menu
from ui.page_manager import Page
from ui.pages.devices import DevicesPage
from ui.pages.network_info import NetworkInfoPage
from ui.pages.reboot import RebootPage
from ui.pages.settings import SettingsPage
from ui.pages.ssh import SshPage
from ui.pages.system_info import SystemInfoPage
from ui.pages.terminal import TerminalPage
from ui.pages.tools import ToolsPage

MENU_ITEMS = [
    "NETWORK INFO",
    "SSH",
    "SYSTEM INFO",
    "HARDWARE",
    "TERMINAL",
    "TOOLS",
    "SETTINGS",
    "REBOOT",
]


class MainMenuPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.menu = Menu(MENU_ITEMS, wrap=True)

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if btn is Button.UP:
            self.menu.up()
        elif btn is Button.DOWN:
            self.menu.down()
        elif btn is Button.CENTER:
            if event.is_long:
                name = self.ctx.theme.cycle()
                self.ctx.settings.set("theme", name)
                self.ctx.settings.save()
            else:
                self._open(self.menu.current)

    def _open(self, item: str | None) -> None:
        factory = {
            "NETWORK INFO": lambda: NetworkInfoPage(self.ctx),
            "SSH": lambda: SshPage(self.ctx),
            "SYSTEM INFO": lambda: SystemInfoPage(self.ctx),
            "HARDWARE": lambda: DevicesPage(self.ctx),
            "TERMINAL": lambda: TerminalPage(self.ctx),
            "TOOLS": lambda: ToolsPage(self.ctx),
            "SETTINGS": lambda: SettingsPage(self.ctx),
            "REBOOT": lambda: RebootPage(self.ctx),
        }.get(item or "")
        if factory:
            self.ctx.pages.push(factory())

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(display, theme, "JELLYBOX",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        self.menu.draw(display, theme)
