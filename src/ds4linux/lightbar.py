"""Reading and writing the lightbar color through the kernel LED interface."""

from __future__ import annotations

import colorsys
import os
from dataclasses import dataclass

from ds4linux.device import Lightbar


@dataclass(frozen=True)
class Color:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for channel in (self.red, self.green, self.blue):
            if not 0 <= channel <= 255:
                raise ValueError(f"color channel out of range: {channel}")

    @classmethod
    def from_hex(cls, value: str) -> Color:
        value = value.lstrip("#")
        if len(value) != 6:
            raise ValueError(f"invalid hex color: {value!r}")
        return cls(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))

    @classmethod
    def from_hsv(cls, hue: float, saturation: float, value: float) -> Color:
        """Build a color from hue, saturation and value, each in 0.0-1.0."""
        red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
        return cls(round(red * 255), round(green * 255), round(blue * 255))

    def to_hex(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"

    def to_hsv(self) -> tuple[float, float, float]:
        return colorsys.rgb_to_hsv(self.red / 255, self.green / 255, self.blue / 255)


# "Off" is the dimmest non-zero color, not black. While the controller is
# charging over USB, exact black makes its firmware take over the lightbar and
# pulse orange (the charging animation). A color of 1 in each channel is
# practically invisible and does not trigger it. Observed on a DualShock 4 v2.
OFF = Color(1, 1, 1)


def avoid_black(color: Color) -> Color:
    """Replace pure black by OFF, so the charging animation never starts."""
    return OFF if color == Color(0, 0, 0) else color


def can_write(lightbar: Lightbar) -> bool:
    """Whether the current user may change the lightbar."""
    return all(
        os.access(path, os.W_OK) for path in (lightbar.red, lightbar.green, lightbar.blue)
    )


def read_color(lightbar: Lightbar) -> Color | None:
    """Return the current color, or None if it cannot be read."""
    try:
        return Color(*(int(path.read_text()) for path in (lightbar.red, lightbar.green, lightbar.blue)))
    except (OSError, ValueError):
        return None


def set_color(lightbar: Lightbar, color: Color) -> None:
    """Set the lightbar color.

    Raises PermissionError when the udev rule is not installed, and OSError if
    the controller was unplugged.
    """
    for path, channel in (
        (lightbar.red, color.red),
        (lightbar.green, color.green),
        (lightbar.blue, color.blue),
    ):
        path.write_text(str(channel))


def turn_off(lightbar: Lightbar) -> None:
    set_color(lightbar, OFF)
