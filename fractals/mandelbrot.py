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
If the `numba` library is installed, the loop below is compiled to machine
code and spread across all CPU cores, which is often 20-50x faster than plain
numpy. Without numba, we fall back to a numpy version that gives the same
picture, only slower.
"""

import math

import numpy as np
from PIL import Image

from colors import colorize
from .base import Fractal, Param, complex_grid

ESCAPE_RADIUS_SQ = 256.0 ** 2
LOG2 = math.log(2.0)

try:
    from numba import njit, prange
    ACCELERATED = True
except ImportError:
    ACCELERATED = False


# ---------------------------------------------------------------------------
# Fast version (numba). Written as plain loops, one pixel at a time. That
# would be very slow in normal Python, but numba compiles it to machine code.
# ---------------------------------------------------------------------------

if ACCELERATED:

    @njit(cache=True, nogil=True, inline="always")
    def _iterate(z, c, max_iter):
        """Run z = z*z + c on ONE point. Returns a smooth escape count, or
        NaN if the point never escaped (inside the set)."""
        for n in range(max_iter):
            z = z * z + c
            mag_sq = z.real * z.real + z.imag * z.imag
            if mag_sq > ESCAPE_RADIUS_SQ:
                # Smooth colouring: add a fraction based on how far past the
                # escape radius z got, so colour bands blend smoothly.
                return n + 1 - math.log(math.log(math.sqrt(mag_sq))) / LOG2
        return math.nan

    # parallel=True + prange: rows are shared out between CPU cores.
    # nogil=True: lets the GUI thread keep running while we compute.
    @njit(parallel=True, cache=True, nogil=True)
    def _mandelbrot_kernel(c, max_iter):
        height, width = c.shape
        out = np.empty((height, width))
        for row in prange(height):
            for col in range(width):
                out[row, col] = _iterate(0j, c[row, col], max_iter)
        return out

    @njit(parallel=True, cache=True, nogil=True)
    def _julia_kernel(z, c, max_iter):
        height, width = z.shape
        out = np.empty((height, width))
        for row in prange(height):
            for col in range(width):
                out[row, col] = _iterate(z[row, col], c, max_iter)
        return out


# ---------------------------------------------------------------------------
# Fallback version (numpy only). Works on the whole image at once.
# ---------------------------------------------------------------------------

def _escape_time_numpy(z, c, max_iter):
    shape = z.shape
    z = z.ravel().copy()
    c = np.broadcast_to(c, shape).ravel().copy()
    result = np.full(z.size, np.nan)

    # `idx` remembers where each still-running point belongs in `result`.
    # Escaped points are dropped from z/c/idx, so later steps only do
    # work on the points that are still undecided.
    idx = np.arange(z.size)

    for n in range(max_iter):
        z = z * z + c
        escaped = (z.real * z.real + z.imag * z.imag) > ESCAPE_RADIUS_SQ
        if escaped.any():
            zi = np.abs(z[escaped])
            result[idx[escaped]] = n + 1 - np.log2(np.log(zi))
            keep = ~escaped
            z, c, idx = z[keep], c[keep], idx[keep]
            if z.size == 0:
                break

    return result.reshape(shape)


# ---------------------------------------------------------------------------
# Public helpers used by Mandelbrot and Julia
# ---------------------------------------------------------------------------

def mandelbrot_counts(c, max_iter):
    """Escape counts for a grid of c values, with z starting at 0."""
    if ACCELERATED:
        return _mandelbrot_kernel(c, max_iter)
    return _escape_time_numpy(np.zeros_like(c), c, max_iter)


def julia_counts(z, c, max_iter):
    """Escape counts for a grid of starting z values and one fixed c."""
    if ACCELERATED:
        return _julia_kernel(z, complex(c), max_iter)
    return _escape_time_numpy(z, c, max_iter)


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
