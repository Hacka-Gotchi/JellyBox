"""Octet-based IP address editor.

A full on-screen keyboard is overkill for entering an IP with five buttons.
This editor shows the four octets; Left/Right picks an octet, Up/Down changes
it (wrapping 0-255). It's reused by Ping and Nmap so any target can be typed,
not just picked from a list.
"""
from __future__ import annotations

from hardware.display import Display
from ui.theme import Theme


class IpEditor:
    def __init__(self, ip: str = "192.168.1.1") -> None:
        self.octets = [192, 168, 1, 1]
        self.set(ip)
        self.pos = 0

    def set(self, ip: str | None) -> None:
        try:
            parts = [int(x) for x in (ip or "").split(".")]
            if len(parts) == 4 and all(0 <= p <= 255 for p in parts):
                self.octets = parts
        except (ValueError, AttributeError):
            pass  # keep whatever we had / the default

    def value(self) -> str:
        return ".".join(str(o) for o in self.octets)

    def left(self) -> None:
        self.pos = (self.pos - 1) % 4

    def right(self) -> None:
        self.pos = (self.pos + 1) % 4

    def inc(self, step: int = 1) -> None:
        self.octets[self.pos] = (self.octets[self.pos] + step) % 256

    def dec(self, step: int = 1) -> None:
        self.octets[self.pos] = (self.octets[self.pos] - step) % 256

    def draw(self, display: Display, theme: Theme, y: int) -> None:
        fg = theme.foreground
        parts = [str(o) for o in self.octets]
        full = ".".join(parts)
        x = (display.WIDTH - display.measure(full)[0]) // 2
        cx = x
        for i, part in enumerate(parts):
            w = display.measure(part)[0]
            display.text(cx, y, part, fg)
            if i == self.pos:  # underline the selected octet
                display.hline(y + display.line_height, fg, cx, cx + w)
            cx += w
            if i < 3:
                dot_w = display.measure(".")[0]
                display.text(cx, y, ".", fg)
                cx += dot_w
