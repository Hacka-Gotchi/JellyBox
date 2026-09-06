"""Theme management.

The display is monochrome: a black background with a single foreground colour
chosen from a small preset list. Every UI element must ask the
theme for its colour -- pages must never hard-code ``(0, 255, 0)``.
"""
from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]

BLACK: RGB = (0, 0, 0)

THEMES: dict[str, RGB] = {
    "green": (0, 255, 0),
    "red": (255, 0, 0),
    "orange": (255, 128, 0),
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
}

DEFAULT_THEME = "green"


@dataclass
class Theme:
    """The currently active colour scheme."""

    name: str = DEFAULT_THEME

    @property
    def foreground(self) -> RGB:
        return THEMES.get(self.name, THEMES[DEFAULT_THEME])

    @property
    def background(self) -> RGB:
        return BLACK

    def set(self, name: str) -> bool:
        """Switch theme. Returns True if the name was valid."""
        if name in THEMES:
            self.name = name
            return True
        return False

    def cycle(self) -> str:
        """Advance to the next preset theme and return its name."""
        names = list(THEMES)
        idx = names.index(self.name) if self.name in names else 0
        self.name = names[(idx + 1) % len(names)]
        return self.name
