"""
Colour palettes: turn escape counts (numbers) into RGB colours.

Each palette is a list of colour "stops". We blend smoothly between them to
build a lookup table (LUT) of 256 colours. The first and last stops are the
same colour, so the palette loops around without a visible seam. That
matters because deep zooms can go through the palette many times.
"""

import math

import numpy as np

try:
    from numba import njit, prange
    ACCELERATED = True
except ImportError:
    ACCELERATED = False

PALETTES = {
    "Classic": [(0, 7, 100), (32, 107, 203), (237, 255, 255),
                (255, 170, 0), (0, 2, 0), (0, 7, 100)],
    "Fire": [(0, 0, 0), (128, 0, 0), (255, 80, 0),
             (255, 200, 0), (255, 255, 210), (0, 0, 0)],
    "Ocean": [(0, 10, 30), (0, 80, 120), (0, 180, 200),
              (200, 255, 255), (0, 10, 30)],
    "Psychedelic": [(255, 0, 0), (255, 255, 0), (0, 255, 0),
                    (0, 255, 255), (0, 0, 255), (255, 0, 255), (255, 0, 0)],
    "Grayscale": [(0, 0, 0), (255, 255, 255), (0, 0, 0)],
}

INSIDE_COLOR = (0, 0, 0)  # points inside the set are drawn black

LUT_SIZE = 256
# How quickly we move through the palette. Bigger = more colour bands.
COLOR_DENSITY = 24.0


def build_lut(stops):
    """Blend between colour stops to make a (256, 3) array of colours."""
    stops = np.array(stops, dtype=float)
    stop_positions = np.linspace(0, LUT_SIZE - 1, len(stops))
    positions = np.arange(LUT_SIZE)
    lut = np.empty((LUT_SIZE, 3))
    for channel in range(3):  # red, green, blue
        lut[:, channel] = np.interp(positions, stop_positions, stops[:, channel])
    return lut.astype(np.uint8)


_LUTS = {name: build_lut(stops) for name, stops in PALETTES.items()}


def colorize(counts, palette_name):
    """Turn a 2D array of escape counts into a (height, width, 3) RGB image.

    counts -- floats from escape_time(); NaN means "inside the set"
    """
    lut = _LUTS[palette_name]
    if ACCELERATED:
        return _colorize_fast(counts, lut.astype(np.float64))

    inside = np.isnan(counts)
    values = np.where(inside, 0.0, np.maximum(counts, 0.0))

    # Square root squashes large counts, so colours still change at deep
    # zooms where counts can be in the thousands.
    position = (np.sqrt(values) * COLOR_DENSITY) % LUT_SIZE

    # `position` usually falls between two table entries (e.g. 41.3), so
    # blend the two neighbours (70% of entry 41, 30% of entry 42). This
    # avoids visible stripes where the colours change.
    low = position.astype(np.int64)
    high = (low + 1) % LUT_SIZE
    frac = (position - low)[..., np.newaxis]
    rgb = (lut[low] * (1 - frac) + lut[high] * frac).astype(np.uint8)

    rgb[inside] = INSIDE_COLOR
    return rgb


if ACCELERATED:

    # The same steps as the numpy code in colorize(), done one pixel at a
    # time with numba (see fractals/mandelbrot.py). Much faster on big images.
    @njit(parallel=True, cache=True, nogil=True)
    def _colorize_fast(counts, lut):
        height, width = counts.shape
        rgb = np.zeros((height, width, 3), dtype=np.uint8)  # zeros = black inside
        for row in prange(height):
            for col in range(width):
                value = counts[row, col]
                if math.isnan(value):
                    continue
                position = (math.sqrt(max(value, 0.0)) * COLOR_DENSITY) % LUT_SIZE
                low = int(position)
                high = (low + 1) % LUT_SIZE
                frac = position - low
                for ch in range(3):
                    rgb[row, col, ch] = int(lut[low, ch] * (1 - frac) + lut[high, ch] * frac)
        return rgb
