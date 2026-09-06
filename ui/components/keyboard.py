"""On-screen keyboard.

A grid of keys driven by the five buttons: arrows move the cursor, CENTER types
the highlighted key. Special keys: SPC (space), DEL (backspace), SHIFT (toggle
case), OK (finish). Reusable wherever free text is needed (SSH user/command,
DNS host, etc.). The editing logic is pure and unit-tested; only ``draw`` needs
a display.
"""
from __future__ import annotations

from hardware.buttons import Button
from hardware.display import Display
from ui.renderer import PADDING_X, truncate
from ui.theme import Theme

_ROWS: list[list[str]] = [
    list("abcdefghij"),
    list("klmnopqrst"),
    list("uvwxyz0123"),
    list("456789.-_@"),
    list("/:,=*|>~;?"),
    ["SPC", "DEL", "SHIFT", "OK"],
]


class Keyboard:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.shift = False
        self.row = 0
        self.col = 0
        self.done = False

    def _current_key(self) -> str:
        row = _ROWS[self.row]
        return row[min(self.col, len(row) - 1)]

    def move_h(self, dc: int) -> None:
        row = _ROWS[self.row]
        self.col = (min(self.col, len(row) - 1) + dc) % len(row)

    def move_v(self, dr: int) -> None:
        self.row = (self.row + dr) % len(_ROWS)
        self.col = min(self.col, len(_ROWS[self.row]) - 1)

    def press(self) -> None:
        key = self._current_key()
        if key == "OK":
            self.done = True
        elif key == "DEL":
            self.text = self.text[:-1]
        elif key == "SPC":
            self.text += " "
        elif key == "SHIFT":
            self.shift = not self.shift
        else:
            self.text += key.upper() if self.shift else key

    def value(self) -> str:
        return self.text

    def handle(self, button: Button) -> str | None:
        """Process one button. Returns 'done', 'cancel', or None.

        Directional buttons move the cursor; CENTER types the highlighted key;
        the aux keys are shortcuts -- KEY2 inserts a space, KEY3 backspaces --
        so common edits don't need cursor travel.
        """
        if button is Button.LEFT:
            self.move_h(-1)
        elif button is Button.RIGHT:
            self.move_h(1)
        elif button is Button.UP:
            self.move_v(-1)
        elif button is Button.DOWN:
            self.move_v(1)
        elif button is Button.KEY2:
            self.text += " "
        elif button is Button.KEY3:
            self.text = self.text[:-1]
        elif button is Button.BACK:
            return "cancel"
        elif button is Button.CENTER:
            self.press()
            if self.done:
                return "done"
        return None

    def draw(self, display: Display, theme: Theme, top_y: int) -> None:
        fg = theme.foreground
        display.text(PADDING_X, top_y, truncate(self.text + "_", 18), fg)
        display.text_right(display.WIDTH - PADDING_X, top_y,
                           "AB" if self.shift else "ab", fg)

        y = top_y + 14
        row_h = display.line_height + 3
        for ri, row in enumerate(_ROWS):
            labels = [k.upper() if (self.shift and len(k) == 1) else k for k in row]
            widths = [display.measure(l)[0] + 5 for l in labels]
            total = sum(widths) + (len(labels) - 1) * 1
            x = max(0, (display.WIDTH - total) // 2)
            for ci, (label, w) in enumerate(zip(labels, widths)):
                if ri == self.row and ci == self.col:
                    display.rect(x, y - 1, x + w, y + display.line_height, fg)
                display.text(x + 3, y, label, fg)
                x += w + 1
            y += row_h
