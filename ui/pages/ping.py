"""Ping page.

Demonstrates the whole async command layer end to end: pinging runs on a
background worker, replies stream in live, and BACK cancels a run in progress. If ping isn't installed the page shows a clean error instead of
crashing.

Target selection: START pings the current target; EDIT opens a small picker of
sensible presets (the detected gateway plus public resolvers). Free-text entry
is done with the on-screen keyboard.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import default_route
from network.ping import PingStats, build_ping_command, parse_rtt, parse_summary
from ui.components.header import draw_header
from ui.components.ip_editor import IpEditor
from ui.components.menu import Menu
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X

PING_COUNT = 10


class _Mode(Enum):
    MENU = auto()
    EDIT = auto()
    RUNNING = auto()
    RESULT = auto()
    ERROR = auto()


class PingPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        gateway, _ = default_route()
        self.target = gateway or "8.8.8.8"
        self.mode = _Mode.MENU
        self.action_menu = Menu(["START", "EDIT"], wrap=True)
        self.editor = IpEditor(self.target)
        self.stats: PingStats | None = None
        self.task = None
        self.error_msg = ""

    def on_exit(self) -> None:
        self._cancel_task()

    def _cancel_task(self) -> None:
        if self.task is not None and not self.task.finished:
            self.task.cancel()
        self.task = None

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.MENU:
            if btn is Button.UP:
                self.action_menu.up()
            elif btn is Button.DOWN:
                self.action_menu.down()
            elif btn is Button.CENTER:
                if self.action_menu.current == "START":
                    self._start_ping()
                else:
                    self.editor.set(self.target)
                    self.mode = _Mode.EDIT
            elif btn is Button.BACK:
                self.ctx.pages.pop()

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

        elif self.mode is _Mode.RUNNING:
            if btn is Button.BACK:  # cancel
                self._cancel_task()
                self.mode = _Mode.RESULT

        elif self.mode in (_Mode.RESULT, _Mode.ERROR):
            if btn is Button.BACK:
                self.mode = _Mode.MENU
            elif btn is Button.CENTER and self.mode is _Mode.RESULT:
                self._start_ping()  # run again

    def _start_ping(self) -> None:
        if not self.ctx.deps.has("ping"):
            self.error_msg = "PING NOT FOUND"
            self.mode = _Mode.ERROR
            return
        self.stats = PingStats(target=self.target)
        cmd = build_ping_command(self.target, count=PING_COUNT)
        self.task = self.ctx.commands.run_async(cmd)
        self.mode = _Mode.RUNNING

    def update(self) -> None:
        if self.mode is not _Mode.RUNNING or self.task is None or self.stats is None:
            return
        for line in self.task.drain_lines():
            rtt = parse_rtt(line)
            if rtt is not None:
                self.stats.add_reply(rtt)
            summary = parse_summary(line)
            if summary is not None:
                self.stats.apply_summary(summary[0], summary[1])
        if self.task.finished:
            result = self.task.result
            self.task = None
            if result is not None and result.error:
                self.error_msg = "PING FAILED"
                self.mode = _Mode.ERROR
            else:
                self.mode = _Mode.RESULT

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(
            display, theme, "PING",
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        fg = theme.foreground
        if self.mode is _Mode.MENU:
            display.text(PADDING_X, CONTENT_TOP, "TARGET", fg)
            display.text(PADDING_X, CONTENT_TOP + 12, self.target, fg)
            self.action_menu.draw(display, theme, top_y=CONTENT_TOP + 30)
        elif self.mode is _Mode.EDIT:
            display.text_center(CONTENT_TOP, "SET TARGET", fg)
            self.editor.draw(display, theme, CONTENT_TOP + 18)
            display.text_center(display.HEIGHT - 22, "UP/DN LR", fg)
            display.text_center(display.HEIGHT - 10, "OK=SET", fg)
        elif self.mode is _Mode.RUNNING:
            self._draw_running(display, fg)
        elif self.mode is _Mode.RESULT:
            self._draw_result(display, fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 6, self.error_msg, fg)
            display.text(PADDING_X, CONTENT_TOP + 20, "INSTALL PING", fg)
            display.text(PADDING_X, display.HEIGHT - 12, "BACK", fg)

    def _draw_running(self, display: Display, fg) -> None:
        assert self.stats is not None
        display.text(PADDING_X, CONTENT_TOP, self.stats.target, fg)
        line_h = display.line_height + 1
        y = CONTENT_TOP + 12
        footer_y = display.HEIGHT - 10
        max_rows = max(1, (footer_y - y) // line_h)
        for rtt in self.stats.replies[-max_rows:]:
            display.text(PADDING_X, y, f"{rtt:g} ms", fg)
            y += line_h
        display.hline(footer_y - 2, fg)
        display.text(PADDING_X, footer_y, "BACK CANCEL", fg)

    def _draw_result(self, display: Display, fg) -> None:
        assert self.stats is not None
        display.text(PADDING_X, CONTENT_TOP, self.stats.target, fg)
        avg = self.stats.avg_ms
        display.text(PADDING_X, CONTENT_TOP + 14,
                     f"AVG {avg:g} ms" if avg is not None else "NO REPLY", fg)
        display.text(PADDING_X, CONTENT_TOP + 26, f"LOSS {self.stats.loss_pct}%", fg)
        display.text(PADDING_X, display.HEIGHT - 10, "CENTER AGAIN  BACK", fg)
