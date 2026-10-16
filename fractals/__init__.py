"""
All available fractals. The GUI builds its dropdown from REGISTRY, so adding
a new fractal only takes one new line here (see README.md).
"""

from .julia import Julia
from .mandelbrot import Mandelbrot

REGISTRY = {
    Mandelbrot.name: Mandelbrot,
    Julia.name: Julia,
}
