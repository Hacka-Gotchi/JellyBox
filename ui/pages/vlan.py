"""VLAN Detection page (TOOLS).

Sniffs 802.1Q-tagged frames on a chosen interface (via the root sniff helper)
and lists the VLAN IDs seen. Needs tcpdump and a link to a trunk port.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.vlan import parse_vlan_ids
from system.devices import list_network_interfaces
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W

_HELPER = "/usr/local/sbin/jellybox-sniff"


class _Mode(Enum):
    MENU = auto()
    SNIFFING = auto()
    RESULT = auto()
    ERROR = auto()


class VlanPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ifaces = [i.name for i in list_network_interfaces() if i.kind in ("wifi", "ethernet")]
        self._ifaces = ifaces or ["eth0"]
        self._i = 0
        self._sel = 0  # 0 = iface row, 1 = START
        self.mode = _Mode.MENU
        self.task = None
        self.vlans: list[int] = []
        self.error_msg = ""

    @property
    def iface(self) -> str:
        return self._ifaces[self._i]

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.MENU:
            if btn is Button.BACK:
                self.ctx.pages.pop()
            elif btn is Button.UP:
                self._sel = (self._sel - 1) % 2
            elif btn is Button.DOWN:
                self._sel = (self._sel + 1) % 2
            elif self._sel == 0 and btn in (Button.LEFT, Button.RIGHT):
                step = 1 if btn is Button.RIGHT else -1
                self._i = (self._i + step) % len(self._ifaces)
            elif btn is Button.CENTER and self._sel == 1:
                self._start()
        elif self.mode is _Mode.SNIFFING:
            if btn is Button.BACK:
                if self.task and not self.task.finished:
                    self.task.cancel()
                self.task = None
                self.mode = _Mode.MENU
        elif self.mode in (_Mode.RESULT, _Mode.ERROR):
            if btn is Button.BACK:
                self.mode = _Mode.MENU
            elif btn is Button.CENTER and self.mode is _Mode.RESULT:
                self._start()

    def _start(self) -> None:
        self.vlans = []
        self.task = self.ctx.commands.run_async(["sudo", "-n", _HELPER, "vlan", self.iface])
        self.mode = _Mode.SNIFFING

    def update(self) -> None:
        if self.task is None or not self.task.finished:
            return
        result = self.task.result
        self.task = None
        if result is not None and result.error:
            self.error_msg = "NEED SETUP (SSH)"
            self.mode = _Mode.ERROR
            return
        self.vlans = parse_vlan_ids(result.stdout if result else "")
        self.mode = _Mode.RESULT

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "VLAN",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        if self.mode is _Mode.MENU:
            m0 = "> " if self._sel == 0 else "  "
            display.text(PADDING_X, CONTENT_TOP, m0 + "IFACE", fg)
            display.text_right(SCREEN_W - PADDING_X, CONTENT_TOP,
                               f"<{self.iface}>" if self._sel == 0 else self.iface, fg)
            m1 = "> " if self._sel == 1 else "  "
            display.text(PADDING_X, CONTENT_TOP + 16, m1 + "START", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "trunk port needed", fg)
        elif self.mode is _Mode.SNIFFING:
            display.text_center(CONTENT_TOP + 24, "SNIFFING 8s...", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK CANCEL", fg)
        elif self.mode is _Mode.RESULT:
            display.text(PADDING_X, CONTENT_TOP, self.iface + " VLANS:", fg)
            if not self.vlans:
                display.text(PADDING_X, CONTENT_TOP + 14, "NONE SEEN", fg)
            else:
                y = CONTENT_TOP + 14
                for v in self.vlans[:6]:
                    display.text(PADDING_X, y, f"VLAN {v}", fg)
                    y += 12
                if len(self.vlans) > 6:
                    display.text(PADDING_X, y, f"+{len(self.vlans)-6} more", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=AGAIN BACK", fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 10, self.error_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
