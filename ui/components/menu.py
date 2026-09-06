"""Scrolling menu component.

Handles selection, wrapping, and a scrolling viewport so long lists work on a
128x128 screen. The selected row is marked with ``>``. The scrolling
maths lives here and is unit-tested without any display.
"""
from __future__ import annotations

from hardware.display import Display
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate
from ui.theme import Theme

MARKER = "> "
INDENT = "  "


class Menu:
    def __init__(self, items: list[str], wrap: bool = True) -> None:
        self.items = list(items)
        self.wrap = wrap
        self.selected = 0
        self._top = 0  # index of the first visible row

    @property
    def current(self) -> str | None:
        return self.items[self.selected] if self.items else None

    def move(self, delta: int) -> None:
        if not self.items:
            return
        n = len(self.items)
        if self.wrap:
            self.selected = (self.selected + delta) % n
        else:
            self.selected = max(0, min(n - 1, self.selected + delta))

    def up(self) -> None:
        self.move(-1)

    def down(self) -> None:
        self.move(1)

    def visible_slice(self, max_rows: int) -> tuple[int, list[str]]:
        """Return (top_index, rows) scrolled to keep ``selected`` visible."""
        if max_rows <= 0 or not self.items:
            return 0, []
        n = len(self.items)
        max_rows = min(max_rows, n)
        if self.selected < self._top:
            self._top = self.selected
        elif self.selected >= self._top + max_rows:
            self._top = self.selected - max_rows + 1
        self._top = max(0, min(self._top, n - max_rows))
        return self._top, self.items[self._top:self._top + max_rows]

    def draw(self, display: Display, theme: Theme, top_y: int = CONTENT_TOP) -> None:
        fg = theme.foreground
        line_h = display.line_height + 1
        avail = display.HEIGHT - top_y
        max_rows = max(1, avail // line_h)
        top, rows = self.visible_slice(max_rows)
        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X) // char_w - len(MARKER)

        y = top_y
        for i, label in enumerate(rows):
            idx = top + i
            prefix = MARKER if idx == self.selected else INDENT
            display.text(PADDING_X, y, prefix + truncate(label, max_chars), fg)
            y += line_h
