"""Settings page: change persisted settings on the device.

Up/Down selects a row, Left/Right (or Center) changes it, and every change is
applied live and saved. WIFI and NETWORKS are navigation rows that open the
Wi-Fi connect and saved-networks pages.
"""
from __future__ import annotations

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W
from ui.theme import THEMES

_ROW_H = 14
_BRIGHT_MIN = 10
_BRIGHT_MAX = 100
_BRIGHT_STEP = 10

_THEME = "theme"
_BRIGHT = "brightness"
_WIFI = "wifi"
_NETWORKS = "networks"
_ROWS = [_THEME, _BRIGHT, _WIFI, _NETWORKS]
_LABELS = {_THEME: "THEME", _BRIGHT: "BRIGHT", _WIFI: "WIFI", _NETWORKS: "NETWORKS"}
_NAV_ROWS = (_WIFI, _NETWORKS)


class SettingsPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._selected = 0

    def _value_str(self, key: str) -> str:
        if key == _THEME:
            return self.ctx.theme.name
        if key == _BRIGHT:
            return f"{int(self.ctx.settings.get(_BRIGHT, 70))}%"
        if key in _NAV_ROWS:
            return ">"
        return "?"

    def _change(self, key: str, direction: int) -> None:
        if key == _WIFI:
            from ui.pages.wifi_scan import WifiScanPage
            self.ctx.pages.push(WifiScanPage(self.ctx))
            return
        if key == _NETWORKS:
            from ui.pages.saved_networks import SavedNetworksPage
            self.ctx.pages.push(SavedNetworksPage(self.ctx))
            return
        if key == _THEME:
            names = list(THEMES)
            idx = names.index(self.ctx.theme.name) if self.ctx.theme.name in names else 0
            name = names[(idx + direction) % len(names)]
            self.ctx.theme.set(name)
            self.ctx.settings.set(_THEME, name)
        elif key == _BRIGHT:
            current = int(self.ctx.settings.get(_BRIGHT, 70))
            new = max(_BRIGHT_MIN, min(_BRIGHT_MAX, current + direction * _BRIGHT_STEP))
            self.ctx.settings.set(_BRIGHT, new)
        self.ctx.settings.save()

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if btn is Button.UP:
            self._selected = (self._selected - 1) % len(_ROWS)
        elif btn is Button.DOWN:
            self._selected = (self._selected + 1) % len(_ROWS)
        elif btn is Button.RIGHT:
            self._change(_ROWS[self._selected], +1)
        elif btn is Button.LEFT:
            self._change(_ROWS[self._selected], -1)
        elif btn is Button.CENTER:
            self._change(_ROWS[self._selected], +1)
        elif btn is Button.BACK:
            self.ctx.pages.pop()

    def draw(self, display: Display) -> None:
        # Brightness is applied live only when it changed, to avoid driving the
        # backlight PWM on every frame.
        want = int(self.ctx.settings.get(_BRIGHT, 70))
        if display.brightness != want:
            display.set_brightness(want)

        theme = self.ctx.theme
        draw_header(display, theme, "SETTINGS",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)
        fg = theme.foreground
        y = CONTENT_TOP + 2
        for i, key in enumerate(_ROWS):
            selected = i == self._selected
            display.text(PADDING_X, y, ("> " if selected else "  ") + _LABELS[key], fg)
            value = self._value_str(key)
            shown = f"<{value}>" if (selected and key not in _NAV_ROWS) else value
            display.text_right(SCREEN_W - PADDING_X, y, shown, fg)
            y += _ROW_H

        display.text(PADDING_X, display.HEIGHT - 10, "<> CHANGE", fg)
        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
