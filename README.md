# Fractal Maker

Explore the Mandelbrot and Julia sets with Python + tkinter.

📖 **Curious about the maths? Read [The Maths Behind Fractal Maker](docs/HOW_IT_WORKS.md):**
complex numbers, why the escape radius is 2, smooth colouring, Julia sets,
the anatomy of the Mandelbrot set (and where π shows up), all from scratch.

## Run it

```bash
python3 main.py
```

Needs Python 3 with tkinter, plus:

```bash
pip install --user -r requirements.txt   # numpy, pillow, numba
```

numba compiles the per-pixel maths to machine code, which makes rendering
20-50x faster than plain Python.

## Controls

| Action | What it does |
|---|---|
| Left-click | Zoom in ×2, centred on the click |
| Right-click | Zoom out ×2 |
| Scroll wheel | Zoom in/out, keeping the point under the cursor fixed |
| Drag a box | Zoom into the box |
| Shift+click (Mandelbrot) | Open the Julia set for that point |
| Max iterations slider | Raise it when deep zooms look blurry or blobby |

Very deep zooms (about 10¹³×) eventually go blocky. That's the limit of
ordinary 64-bit floating-point numbers, not a bug.

## Why it's fast

Three tricks keep the app smooth, even full-screen:

1. **numba** (`fractals/mandelbrot.py`, `colors.py`). The per-pixel loops are
   compiled to machine code and their rows are shared across all CPU cores.
   On first launch the compiling takes a few seconds; after that it's cached
   in `__pycache__`.
2. **A background thread** (`app.py`, `render_worker`). Rendering happens
   off the GUI thread, so the window never freezes. Every request gets a
   *generation* number, and finished pictures from outdated requests are
   thrown away.
3. **Instant zoom previews** (`app.py`, `show_zoom_preview`). When you zoom,
   the last picture is stretched to the new view at once. It's blurry for a
   moment, then the sharp version replaces it.

## How it's organised

```
main.py              starts the app
app.py               the window, sliders and mouse handling
colors.py            colour palettes
fractals/
  base.py            Fractal base class + Param (one slider) + helpers
  mandelbrot.py      Mandelbrot set + the shared escape_count() loop
  julia.py           Julia sets
  __init__.py        REGISTRY: the list of fractals in the dropdown
```

The window never needs to know how a fractal is calculated. It asks
`fractal.render(width, height, view, settings)` for a PIL image and shows it.
It builds a slider automatically for every `Param` in the fractal's `params`.

## Adding a new fractal

1. Create `fractals/my_fractal.py` with a subclass of `Fractal` that returns a
   PIL image from `render()`.
2. Add it to `REGISTRY` in `fractals/__init__.py`.

That's all. It appears in the dropdown with its own sliders.

Example: a recursive **fractal tree**. Set `zoomable = False`, because it's
drawn line by line rather than per pixel.

```python
# fractals/tree.py
import math
from PIL import Image, ImageDraw
from .base import Fractal, Param


class Tree(Fractal):
    name = "Fractal tree"
    zoomable = False
    params = {
        "depth": Param("Depth", 10, 1, 14, 1),
        "angle": Param("Branch angle", 25.0, 0.0, 90.0, 1.0),
    }

    def render(self, width, height, view, settings):
        img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img)

        def branch(x, y, length, direction, depth):
            if depth == 0:
                return
            x2 = x + length * math.cos(math.radians(direction))
            y2 = y - length * math.sin(math.radians(direction))
            draw.line([(x, y), (x2, y2)], fill=(120, 220, 120), width=max(1, depth // 2))
            # Each branch splits into two smaller branches: that's the recursion.
            branch(x2, y2, length * 0.7, direction + settings["angle"], depth - 1)
            branch(x2, y2, length * 0.7, direction - settings["angle"], depth - 1)

        branch(width / 2, height, height / 4, 90, settings["depth"])
        return img
```

```python
# fractals/__init__.py
from .tree import Tree
REGISTRY = {..., Tree.name: Tree}
```

You can build the **Barnsley fern** the same way: loop many times, pick one of
four simple transformations at random each step, and set a pixel with
`img.putpixel` (or with a numpy array, for speed).
