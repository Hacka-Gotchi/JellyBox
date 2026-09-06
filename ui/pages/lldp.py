"""LLDP Discovery page (TOOLS).

Shows neighbors reported by lldpd (switch name, port, VLAN, mgmt IP). Needs the
``lldpd`` package running:  sudo apt install -y lldpd
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.lldp import parse_lldp
from ui.components.header import draw_header
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X


class _Mode(Enum):
    LOADING = auto()
    DONE = auto()
    ERROR = auto()


class LldpPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.mode = _Mode.LOADING
        self.view = ScrollView()
        self.task = None
        self.error_msg = ""

    def on_enter(self) -> None:
        self._scan()

    def _scan(self) -> None:
        self.mode = _Mode.LOADING
        self.task = self.ctx.commands.run_async(["lldpctl", "-f", "keyvalue"])

    def update(self) -> None:
        if self.task is None or not self.task.finished:
            return
        result = self.task.result
        self.task = None
        if result is not None and result.error:
            self.error_msg = "LLDPD NOT FOUND"
            self.mode = _Mode.ERROR
            return
        neighbors = parse_lldp(result.stdout if result else "")
        lines: list[str] = []
        for n in neighbors:
            lines.append(n.get("name", n["iface"]))
            if n.get("port"):
                lines.append("  port " + n["port"])
            if n.get("vlan"):
                lines.append("  vlan " + n["vlan"])
            if n.get("mgmt"):
                lines.append("  ip " + n["mgmt"])
            lines.append("")
        self.view.set_lines(lines or ["no neighbors", "(need lldpd + a wired link)"])
        self.mode = _Mode.DONE

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.CENTER:
            self._scan()
        elif btn is Button.DOWN:
            self.view.down()
        elif btn is Button.UP:
            self.view.up()

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "LLDP",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        if self.mode is _Mode.LOADING:
            display.text_center(CONTENT_TOP + 24, "LISTENING...", fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 10, self.error_msg, fg)
            display.text(PADDING_X, CONTENT_TOP + 24, "apt install lldpd", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
        else:
            self.view.draw(display, theme, CONTENT_TOP, display.HEIGHT - 10)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=RESCAN", fg)
