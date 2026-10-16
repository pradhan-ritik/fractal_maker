"""
The "contract" every fractal must follow.

The GUI (app.py) only ever talks to fractals through this interface, so it
never needs to know *how* a particular fractal is drawn. To add a new kind of
fractal, subclass `Fractal`, implement `render()`, and register it in
fractals/__init__.py.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Param:
    """One adjustable setting. The sidebar turns each Param into a slider.
    If `default` is a whole number (e.g. 300, not 300.0), the slider gives
    whole numbers."""
    label: str
    default: float
    min: float
    max: float
    step: float = 1


class Fractal:
    # Name shown in the dropdown.
    name = "Base"

    # Settings the user can tweak: {key: Param(...)}.
    # The values arrive in render() as settings[key].
    params = {}

    # Optional named starting points: {"Preset name": {key: value, ...}}.
    presets = {}

    # True if clicking/scrolling should zoom. Escape-time fractals like
    # Mandelbrot have infinite detail, so zooming is the whole point.
    zoomable = False

    def default_view(self):
        """Return (center_x, center_y, width): which part of the maths plane
        to show. Height follows from the window's shape."""
        return (0.0, 0.0, 4.0)

    def render(self, width, height, view, settings):
        """Draw the fractal and return a PIL.Image of size (width, height).

        view     -- (center_x, center_y, width) in maths coordinates
        settings -- dict with one value per entry in `params`, plus
                    "palette" (the name of the colour palette to use)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers for converting between screen pixels and points on the maths plane.
# On screen, y grows downwards; in maths, y (the "imaginary" axis) grows up.
# ---------------------------------------------------------------------------

def pixel_to_point(px, py, width, height, view):
    """Convert a pixel position to an (x, y) point on the maths plane.
    Works on single numbers and on whole numpy arrays of pixels."""
    cx, cy, w = view
    h = w * height / width
    x = cx - w / 2 + (px / width) * w
    y = cy + h / 2 - (py / height) * h
    return x, y


def complex_grid(width, height, view):
    """Return a (height, width) numpy array of complex numbers, one per pixel.

    Each pixel becomes the complex number x + y*i at its spot on the plane.
    """
    columns = np.arange(width)[np.newaxis, :]  # a row of x pixel positions
    rows = np.arange(height)[:, np.newaxis]    # a column of y pixel positions
    x, y = pixel_to_point(columns, rows, width, height, view)
    return x + 1j * y
