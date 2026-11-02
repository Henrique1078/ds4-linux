"""A hue and saturation color wheel."""

from __future__ import annotations

import colorsys
import math

import cairo
from gi.repository import GObject, Gtk

_SIZE = 240
_MARGIN = 8


def _render_wheel(diameter: int, scale: int) -> cairo.ImageSurface:
    """Draw the wheel at full brightness, with an antialiased edge."""
    pixels = diameter * scale
    radius = pixels / 2
    stride = pixels * 4
    data = bytearray(stride * pixels)
    for y in range(pixels):
        dy = y + 0.5 - radius
        for x in range(pixels):
            dx = x + 0.5 - radius
            distance = math.hypot(dx, dy)
            alpha = min(1.0, radius - distance)
            if alpha <= 0.0:
                continue
            hue = (math.atan2(dy, dx) / math.tau) % 1.0
            red, green, blue = colorsys.hsv_to_rgb(hue, min(distance / radius, 1.0), 1.0)
            # Cairo expects premultiplied BGRA on little-endian machines.
            i = y * stride + x * 4
            data[i] = round(blue * alpha * 255)
            data[i + 1] = round(green * alpha * 255)
            data[i + 2] = round(red * alpha * 255)
            data[i + 3] = round(alpha * 255)
    surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, pixels, pixels, stride)
    surface.set_device_scale(scale, scale)
    return surface


class ColorWheel(Gtk.DrawingArea):
    """Pick a hue (angle) and a saturation (distance from the center).

    The ``changed`` signal is emitted only when the user moves the marker,
    never when the position is set from code.
    """

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self) -> None:
        super().__init__()
        self._hue = 0.0
        self._saturation = 1.0
        self._cache: tuple[tuple[int, int], cairo.ImageSurface] | None = None
        self._drag_start = (0.0, 0.0)
        self.set_content_width(_SIZE)
        self.set_content_height(_SIZE)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        self.add_controller(drag)

    @property
    def hue(self) -> float:
        return self._hue

    @property
    def saturation(self) -> float:
        return self._saturation

    def set_position(self, hue: float, saturation: float) -> None:
        self._hue = hue % 1.0
        self._saturation = max(0.0, min(1.0, saturation))
        self.queue_draw()

    def _geometry(self) -> tuple[float, float, float]:
        width, height = self.get_width(), self.get_height()
        return width / 2, height / 2, (min(width, height) - 2 * _MARGIN) / 2

    def _pick(self, x: float, y: float) -> None:
        center_x, center_y, radius = self._geometry()
        dx, dy = x - center_x, y - center_y
        self._hue = (math.atan2(dy, dx) / math.tau) % 1.0
        self._saturation = min(math.hypot(dx, dy) / radius, 1.0)
        self.queue_draw()
        self.emit("changed")

    def _on_drag_begin(self, _gesture, x: float, y: float) -> None:
        self._drag_start = (x, y)
        self._pick(x, y)

    def _on_drag_update(self, _gesture, offset_x: float, offset_y: float) -> None:
        self._pick(self._drag_start[0] + offset_x, self._drag_start[1] + offset_y)

    def _draw(self, _area, cr: cairo.Context, width: int, height: int) -> None:
        center_x, center_y, radius = self._geometry()
        diameter, scale = int(radius * 2), self.get_scale_factor()
        if self._cache is None or self._cache[0] != (diameter, scale):
            self._cache = ((diameter, scale), _render_wheel(diameter, scale))
        cr.set_source_surface(self._cache[1], center_x - radius, center_y - radius)
        cr.paint()
        angle = self._hue * math.tau
        marker_x = center_x + math.cos(angle) * self._saturation * radius
        marker_y = center_y + math.sin(angle) * self._saturation * radius
        cr.arc(marker_x, marker_y, 9, 0, math.tau)
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.set_line_width(5)
        cr.stroke_preserve()
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(3)
        cr.stroke()
