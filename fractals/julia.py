"""
Julia sets.

THE IDEA
--------
Same formula as Mandelbrot, z = z*z + c, but the roles are swapped:

  * Mandelbrot: z starts at 0, and c changes from pixel to pixel.
  * Julia:      c is ONE fixed number for the whole picture, and z starts
                at the pixel's own position.

Every value of c gives a different Julia set, so there are infinitely many.
A nice fact: if c is inside the Mandelbrot set, its Julia set is one connected
shape. If c is outside, the Julia set breaks into "dust". Try Shift+clicking
on the Mandelbrot view to see the Julia set for that exact point.
"""

from PIL import Image

from colors import colorize
from .base import Fractal, Param, complex_grid
from .mandelbrot import julia_counts


class Julia(Fractal):
    name = "Julia"
    zoomable = True
    params = {
        "c_real": Param("c (real part)", -0.8, -2.0, 2.0, 0.001),
        "c_imag": Param("c (imaginary part)", 0.156, -2.0, 2.0, 0.001),
        "max_iter": Param("Max iterations", 300, 50, 5000, 10),
    }
    presets = {
        "Dendrite swirl": {"c_real": -0.8, "c_imag": 0.156},
        "Douady rabbit": {"c_real": -0.123, "c_imag": 0.745},
        "San Marco": {"c_real": -0.75, "c_imag": 0.0},
        "Siegel disk": {"c_real": -0.391, "c_imag": -0.587},
        "Dragon": {"c_real": 0.36, "c_imag": 0.1},
        "Lightning": {"c_real": -0.7269, "c_imag": 0.1889},
        "Dust (disconnected)": {"c_real": 0.3, "c_imag": 0.5},
    }

    def default_view(self):
        return (0.0, 0.0, 3.5)

    def render(self, width, height, view, settings):
        z = complex_grid(width, height, view)  # z starts at each pixel
        c = complex(settings["c_real"], settings["c_imag"])
        counts = julia_counts(z, c, settings["max_iter"])
        return Image.fromarray(colorize(counts, settings["palette"]))
