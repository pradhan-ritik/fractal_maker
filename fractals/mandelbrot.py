"""
The Mandelbrot set.

THE IDEA
--------
Pick a complex number c (each pixel is one c). Start with z = 0 and repeat:

    z = z*z + c

For some c, z stays small forever. Those c are *in* the Mandelbrot set
(drawn black). For others, z grows towards infinity. We colour those by how
many steps it took to "escape", which produces the colourful bands around
the set.

Once |z| > 2, z is guaranteed to fly off to infinity, so we can stop early.
(We actually wait until |z| > 256: the answer is the same, and the extra steps
make the smooth colouring below look nicer.)

SPEED
-----
The loops below go over every pixel one at a time. In normal Python that
would be very slow, but the `@njit` decorator from the numba library compiles
them to machine code, and `prange` shares the rows out between all CPU cores.
"""

import math

import numpy as np
from numba import njit, prange
from PIL import Image

from colors import colorize
from .base import Fractal, Param, complex_grid

ESCAPE_RADIUS_SQ = 256.0 ** 2
LOG2 = math.log(2.0)


@njit(cache=True, nogil=True, inline="always")
def escape_count(z, c, max_iter):
    """Run z = z*z + c on ONE point. Returns a smooth escape count, or NaN
    if the point never escaped (inside the set). Also used by julia.py."""
    for n in range(max_iter):
        z = z * z + c
        mag_sq = z.real * z.real + z.imag * z.imag
        if mag_sq > ESCAPE_RADIUS_SQ:
            # Smooth colouring: add a fraction based on how far past the
            # escape radius z got, so colour bands blend smoothly.
            return n + 1 - math.log(math.log(math.sqrt(mag_sq))) / LOG2
    return math.nan


# nogil=True lets the GUI keep running while this computes in the background.
@njit(parallel=True, cache=True, nogil=True)
def mandelbrot_counts(c, max_iter):
    """Escape counts for a grid of c values, with z always starting at 0."""
    height, width = c.shape
    counts = np.empty((height, width))
    for row in prange(height):
        for col in range(width):
            counts[row, col] = escape_count(0j, c[row, col], max_iter)
    return counts


class Mandelbrot(Fractal):
    name = "Mandelbrot"
    zoomable = True
    params = {
        "max_iter": Param("Max iterations", 300, 50, 5000, 10),
    }

    def default_view(self):
        return (-0.5, 0.0, 3.5)

    def render(self, width, height, view, settings):
        c = complex_grid(width, height, view)
        counts = mandelbrot_counts(c, settings["max_iter"])
        return Image.fromarray(colorize(counts, settings["palette"]))
