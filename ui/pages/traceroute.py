"""Traceroute page (TOOLS)."""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import default_route
from network.traceroute import build_traceroute_command
from ui.components.header import draw_header
from ui.components.ip_editor import IpEditor
from ui.components.menu import Menu
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W


class _Mode(Enum):
    MENU = auto()
    EDIT = auto()
    OUTPUT = auto()
    ERROR = auto()


class TraceroutePage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        gw, _ = default_route()
        self.target = gw or "8.8.8.8"
        self.mode = _Mode.MENU
        self.menu = Menu(["START", "EDIT"], wrap=True)
        self.editor = IpEditor(self.target)
        self.view = ScrollView(follow=True)
        self.task = None
        self.error_msg = ""
        self._saved = ""

    def on_exit(self) -> None:
        self._cancel()

    def _cancel(self) -> None:
        if self.task is not None and not self.task.finished:
            self.task.cancel()
        self.task = None

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.MENU:
            if btn is Button.UP:
                self.menu.up()
            elif btn is Button.DOWN:
                self.menu.down()
            elif btn is Button.BACK:
                self.ctx.pages.pop()
            elif btn is Button.CENTER:
                if self.menu.current == "START":
                    self._start()
                else:
                    self.editor.set(self.target)
                    self.mode = _Mode.EDIT
        elif self.mode is _Mode.EDIT:
            if btn is Button.LEFT:
                self.editor.left()
            elif btn is Button.RIGHT:
                self.editor.right()
            elif btn is Button.UP:
                self.editor.inc()
            elif btn is Button.DOWN:
                self.editor.dec()
            elif btn is Button.CENTER:
                self.target = self.editor.value()
                self.mode = _Mode.MENU
            elif btn is Button.BACK:
                self.mode = _Mode.MENU
        elif self.mode is _Mode.OUTPUT:
            running = self.task is not None
            if btn is Button.BACK:
                if running:
                    self._cancel()
                else:
                    self.mode = _Mode.MENU
            elif btn is Button.UP:
                self.view.up()
            elif btn is Button.DOWN:
                self.view.down()
            elif btn is Button.CENTER and not running:
                self._start()
            elif btn is Button.LEFT and not running:
                from system.scanstore import save_scan
                try:
                    name = save_scan("trace", self.target, self.view.lines)
                    self._saved = "SAVED " + name.split("_")[0]
                except Exception:
                    self._saved = "SAVE FAILED"
        elif self.mode is _Mode.ERROR:
            if btn is Button.BACK:
                self.mode = _Mode.MENU

    def _start(self) -> None:
        if not self.ctx.deps.has("traceroute"):
            self.error_msg = "TRACEROUTE MISSING"
            self.mode = _Mode.ERROR
            return
        self.view.set_lines([self.target])
        self._saved = ""
        self.task = self.ctx.commands.run_async(build_traceroute_command(self.target))
        self.mode = _Mode.OUTPUT

    def update(self) -> None:
        if self.task is None:
            return
        for line in self.task.drain_lines():
            self.view.append(line)
            self.view.follow = True
        if self.task.finished:
            for line in self.task.drain_lines():
                self.view.append(line)
            self.task = None

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "TRACERT",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        if self.mode is _Mode.MENU:
            display.text(PADDING_X, CONTENT_TOP, "TARGET", fg)
            display.text(PADDING_X, CONTENT_TOP + 12, self.target, fg)
            self.menu.draw(display, theme, top_y=CONTENT_TOP + 30)
        elif self.mode is _Mode.EDIT:
            display.text_center(CONTENT_TOP, "SET TARGET", fg)
            self.editor.draw(display, theme, CONTENT_TOP + 18)
            display.text_center(display.HEIGHT - 22, "UP/DN LR", fg)
            display.text_center(display.HEIGHT - 10, "OK=SET", fg)
        elif self.mode is _Mode.OUTPUT:
            footer_y = display.HEIGHT - 10
            self.view.draw(display, theme, CONTENT_TOP, footer_y)
            if self.task is not None:
                display.text(PADDING_X, footer_y, "BACK=STOP", fg)
            elif self._saved:
                display.text_center(footer_y, self._saved, fg)
            else:
                display.text(PADDING_X, footer_y, "L=SAVE OK=AGAIN", fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 10, self.error_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
