"""MAC Spoof page (TOOLS).

Change a network interface's MAC address -- a standard pentest / privacy tool.
Pick an interface, then set a random MAC, type a custom one, or reset to the
permanent (factory) address. Uses the same root-owned helper as monitor mode.

Note: spoofing the interface you're connected over (e.g. the one carrying your
SSH session) will briefly drop that link, so prefer a spare adapter.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.devices import list_network_interfaces
from system.macaddr import current_mac, is_valid_mac, parse_ethtool_permanent, random_mac
from ui.components.header import draw_header
from ui.components.keyboard import Keyboard
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_HELPER = "/usr/local/sbin/jellybox-iface"
_ROW_H = 12
_ACTIONS = ["RANDOM", "CUSTOM", "RESET"]


class _Mode(Enum):
    MENU = auto()
    EDIT = auto()
    WORKING = auto()


class MacSpoofPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ifaces = [i.name for i in list_network_interfaces() if i.kind in ("wifi", "ethernet")]
        self._ifaces = ifaces or ["wlan0"]
        pref = self.ctx.settings.get("wifi_interface")
        self._i = self._ifaces.index(pref) if pref in self._ifaces else 0
        self._original = {name: current_mac(name) for name in self._ifaces}
        self._sel = 0                # 0 = IFACE row, 1..3 = actions
        self.mode = _Mode.MENU
        self.keyboard: Keyboard | None = None
        self.task = None
        self.status = ""

    @property
    def iface(self) -> str:
        return self._ifaces[self._i]

    def handle_input(self, event: ButtonEvent) -> None:
        if self.mode is _Mode.EDIT:
            self._edit_input(event.button)
            return
        if self.mode is _Mode.WORKING:
            return
        btn = event.button
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.UP:
            self._sel = (self._sel - 1) % (len(_ACTIONS) + 1)
        elif btn is Button.DOWN:
            self._sel = (self._sel + 1) % (len(_ACTIONS) + 1)
        elif self._sel == 0 and btn in (Button.LEFT, Button.RIGHT):
            step = 1 if btn is Button.RIGHT else -1
            self._i = (self._i + step) % len(self._ifaces)
            self.status = ""
        elif btn is Button.CENTER and self._sel > 0:
            self._run_action(_ACTIONS[self._sel - 1])

    def _edit_input(self, btn: Button) -> None:
        kb = self.keyboard
        if kb is None:
            self.mode = _Mode.MENU
            return
        status = kb.handle(btn)
        if status == "cancel":
            self.mode = _Mode.MENU
        elif status == "done":
            mac = kb.value().strip().lower()
            self.mode = _Mode.MENU
            if is_valid_mac(mac):
                self._apply(mac)
            else:
                self.status = "BAD MAC"

    def _run_action(self, action: str) -> None:
        if action == "RANDOM":
            self._apply(random_mac())
        elif action == "CUSTOM":
            self.keyboard = Keyboard(current_mac(self.iface) or "")
            self.mode = _Mode.EDIT
        elif action == "RESET":
            mac = self._permanent_mac() or self._original.get(self.iface)
            if mac:
                self._apply(mac)
            else:
                self.status = "NO PERM MAC"

    def _permanent_mac(self) -> str | None:
        res = self.ctx.commands.run(["ethtool", "-P", self.iface], timeout=3)
        return parse_ethtool_permanent(res.stdout) if res.ok else None

    def _apply(self, mac: str) -> None:
        self.status = "APPLYING..."
        self.task = self.ctx.commands.run_async(
            ["sudo", "-n", _HELPER, self.iface, "mac", mac])

    def update(self) -> None:
        if self.task is None or not self.task.finished:
            return
        result = self.task.result
        self.task = None
        if result is not None and result.ok:
            self.status = "OK"
        else:
            self.status = "FAILED (SETUP?)"

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        if self.mode is _Mode.EDIT and self.keyboard is not None:
            display.text(PADDING_X, 2, "MAC", fg)
            display.hline(14, fg)
            self.keyboard.draw(display, theme, 18)
            return

        draw_header(display, theme, "MAC SPOOF",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        y = CONTENT_TOP
        marker = "> " if self._sel == 0 else "  "
        display.text(PADDING_X, y, marker + "IFACE", fg)
        display.text_right(SCREEN_W - PADDING_X, y,
                           f"<{self.iface}>" if self._sel == 0 else self.iface, fg)
        y += _ROW_H
        display.text(PADDING_X, y, "MAC", fg)
        display.text(46, y, current_mac(self.iface) or "-", fg)
        y += _ROW_H + 2
        for i, action in enumerate(_ACTIONS):
            marker = "> " if self._sel == i + 1 else "  "
            display.text(PADDING_X, y, marker + action, fg)
            y += _ROW_H

        if self.status:
            display.text_center(display.HEIGHT - 20, self.status, fg)
        display.text(PADDING_X, display.HEIGHT - 10, "OK=DO", fg)
        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
