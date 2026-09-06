"""Scrollable, word-wrapped text view.

Fixes the two ways output gets cut on a 128x128 screen: long lines are wrapped
(not truncated) so nothing is lost horizontally, and content taller than the
view scrolls with Up/Down, with ^/v arrows showing there's more above/below.

Set ``follow=True`` for log-style views (terminal) that should stick to the
newest line unless the user scrolls up; leave it False for result lists that
should start at the top.
"""
from __future__ import annotations

from hardware.display import Display
from ui.renderer import PADDING_X, wrap
from ui.theme import Theme


class ScrollView:
    def __init__(self, follow: bool = False) -> None:
        self.lines: list[str] = []
        self.top = 0          # index into the wrapped lines
        self.follow = follow

    def set_lines(self, lines: list[str]) -> None:
        self.lines = list(lines)
        self.top = 0

    def append(self, line: str) -> None:
        self.lines.append(line)

    def clear(self) -> None:
        self.lines = []
        self.top = 0

    def up(self) -> None:
        self.follow = False
        self.top = max(0, self.top - 1)

    def down(self) -> None:
        self.top += 1  # clamped at draw time

    def page_up(self, rows: int = 4) -> None:
        self.follow = False
        self.top = max(0, self.top - rows)

    def _wrapped(self, max_chars: int) -> list[str]:
        out: list[str] = []
        for ln in self.lines:
            if ln == "":
                out.append("")
            else:
                pieces = wrap(ln, max_chars)
                out.extend(pieces if pieces else [""])
        return out

    def draw(self, display: Display, theme: Theme, top_y: int, bottom_y: int) -> None:
        fg = theme.foreground
        char_w = max(1, display.measure("0")[0])
        # reserve a couple of px on the right for the scroll arrows
        max_chars = max(1, (display.WIDTH - PADDING_X - 6) // char_w)
        wrapped = self._wrapped(max_chars)

        line_h = display.line_height
        rows = max(1, (bottom_y - top_y) // line_h)
        total = len(wrapped)
        max_off = max(0, total - rows)

        if self.follow:
            self.top = max_off
        self.top = min(max(0, self.top), max_off)
        if self.top >= max_off:      # reached the bottom -> re-stick (for logs)
            self.follow = True

        y = top_y
        for line in wrapped[self.top:self.top + rows]:
            display.text(PADDING_X, y, line, fg)
            y += line_h

        if self.top > 0:
            display.text_right(display.WIDTH - 1, top_y, "^", fg)
        if self.top + rows < total:
            display.text_right(display.WIDTH - 1, bottom_y - line_h, "v", fg)
