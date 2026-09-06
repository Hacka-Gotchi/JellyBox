"""Shared layout constants and text-fitting helpers.

Pixel coordinates are defined here once, as named constants, so no
page scatters magic numbers. Text helpers keep drawing inside the tiny 128x128
panel.
"""
from __future__ import annotations

SCREEN_W = 128
SCREEN_H = 128
HEADER_H = 16      # title + connection icons live here
FOOTER_H = 10      # reserved for hints / status
CONTENT_TOP = 19   # first pixel row of page content (below the separator)
CONTENT_BOTTOM = SCREEN_H - FOOTER_H
PADDING_X = 2

ELLIPSIS = "\u2026"  # single-glyph ellipsis to save pixels


def truncate(text: str, max_chars: int, ellipsis: str = ELLIPSIS) -> str:
    """Shorten ``text`` to ``max_chars`` characters, adding an ellipsis.

    >>> truncate("VERY_LONG_NETWORK_NAME", 12)
    'VERY_LONG_N\u2026'
    """
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= len(ellipsis):
        return text[:max_chars]
    return text[: max_chars - len(ellipsis)] + ellipsis


def wrap(text: str, max_chars: int) -> list[str]:
    """Word-wrap ``text`` to lines of at most ``max_chars`` characters."""
    if max_chars <= 0:
        return [text]
    lines: list[str] = []
    line = ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= max_chars:
            line += " " + word
        else:
            lines.append(line)
            line = word
        # a single word longer than the line gets hard-split
        while len(line) > max_chars:
            lines.append(line[:max_chars])
            line = line[max_chars:]
    if line:
        lines.append(line)
    return lines
