"""
The tkinter window: a canvas on the left showing the fractal, a sidebar on
the right with controls, and a status bar at the bottom.

This file knows nothing about how fractals are calculated. It just asks the
selected fractal to `render()` an image and shows it. Every fractal in
fractals.REGISTRY appears in the dropdown automatically.
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from colors import PALETTES
from fractals import REGISTRY
from fractals.base import pixel_to_point
from fractals.mandelbrot import ACCELERATED

RENDER_DELAY_MS = 40    # wait this long after the last change before redrawing
DRAG_THRESHOLD = 6      # pixels the mouse must move before a drag counts as a box
POLL_MS = 15            # how often the GUI checks for finished renders
PREVIEW_SCALE = 4       # quick preview is drawn at 1/4 width and height...
PREVIEW_IF_SLOWER_THAN = 0.15  # ...but only when full renders take this long (s)

HELP_TEXT = (
    "Mouse controls\n"
    "• Left-click: zoom in ×2\n"
    "• Right-click: zoom out\n"
    "• Scroll wheel: zoom at the cursor\n"
    "• Drag a box: zoom into the box\n"
    "• Shift+click (Mandelbrot):\n"
    "   show the Julia set for that point"
)


class FractalApp:
    def __init__(self, root):
        self.root = root
        root.title("Fractal Maker")
        root.geometry("1100x680")
        root.minsize(700, 450)

        self.fractal = None       # the current Fractal object
        self.view = None          # (center_x, center_y, width) in maths coords
        self.param_vars = {}      # param key -> tk variable behind its slider
        self.image = None         # last rendered PIL image (for saving)
        self.photo = None         # tkinter copy of it (must be kept alive!)
        self.pending_render = None
        self.drag_start = None
        self.canvas_size = (1, 1)
        self.last_render_info = ""

        # What is currently on the canvas (used for instant zoom previews).
        self.shown_image = None
        self.shown_view = None
        self.shown_fractal = None

        # Background rendering. The GUI puts jobs in `jobs`; a worker thread
        # renders them and puts pictures in `results`. Every request gets a
        # new `generation` number, so results of outdated requests can be
        # recognised and thrown away.
        self.generation = 0
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.last_full_time = 0.0
        threading.Thread(target=self._render_worker, daemon=True).start()

        self._build_layout()
        self._bind_mouse()
        self.switch_fractal(next(iter(REGISTRY)))
        self._poll_results()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self):
        self.status = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status, anchor="w",
                 relief="sunken", padx=6).pack(side="bottom", fill="x")

        sidebar = ttk.Frame(self.root, padding=10, width=260)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0,
                                cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True)

        ttk.Label(sidebar, text="Fractal").pack(anchor="w")
        self.fractal_choice = tk.StringVar()
        box = ttk.Combobox(sidebar, textvariable=self.fractal_choice,
                           values=list(REGISTRY), state="readonly")
        box.pack(fill="x", pady=(0, 10))
        box.bind("<<ComboboxSelected>>",
                 lambda e: self.switch_fractal(self.fractal_choice.get()))

        ttk.Label(sidebar, text="Colour palette").pack(anchor="w")
        self.palette_choice = tk.StringVar(value=next(iter(PALETTES)))
        box = ttk.Combobox(sidebar, textvariable=self.palette_choice,
                           values=list(PALETTES), state="readonly")
        box.pack(fill="x", pady=(0, 10))
        box.bind("<<ComboboxSelected>>", lambda e: self.schedule_render())

        # Filled in by switch_fractal(), because each fractal has its own
        # sliders and presets.
        self.params_frame = ttk.Frame(sidebar)
        self.params_frame.pack(fill="x")

        buttons = ttk.Frame(sidebar)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="Reset view",
                   command=self.reset_view).pack(side="left", expand=True, fill="x")
        ttk.Button(buttons, text="Save PNG…",
                   command=self.save_png).pack(side="left", expand=True, fill="x")

        ttk.Label(sidebar, text=HELP_TEXT, justify="left",
                  foreground="#555").pack(anchor="w", pady=(10, 0))

    def _build_param_controls(self):
        """Create one slider per fractal parameter, plus a preset menu."""
        for child in self.params_frame.winfo_children():
            child.destroy()
        self.param_vars = {}

        if self.fractal.presets:
            ttk.Label(self.params_frame, text="Presets").pack(anchor="w")
            preset = tk.StringVar(value="Choose a preset…")
            box = ttk.Combobox(self.params_frame, textvariable=preset,
                               values=list(self.fractal.presets), state="readonly")
            box.pack(fill="x", pady=(0, 10))
            box.bind("<<ComboboxSelected>>",
                     lambda e: self.apply_preset(preset.get()))

        for key, param in self.fractal.params.items():
            ttk.Label(self.params_frame, text=param.label).pack(anchor="w")
            var = tk.DoubleVar(value=param.default)
            tk.Scale(self.params_frame, variable=var, orient="horizontal",
                     from_=param.min, to=param.max, resolution=param.step,
                     command=lambda _value: self.schedule_render()
                     ).pack(fill="x", pady=(0, 6))
            self.param_vars[key] = var

    # ------------------------------------------------------------------
    # Switching fractals, presets and views
    # ------------------------------------------------------------------

    def switch_fractal(self, name):
        self.fractal = REGISTRY[name]()
        self.fractal_choice.set(name)
        self._build_param_controls()
        self.reset_view()

    def apply_preset(self, preset_name):
        for key, value in self.fractal.presets[preset_name].items():
            self.param_vars[key].set(value)
        self.reset_view()

    def reset_view(self):
        self.view = self.fractal.default_view()
        self.schedule_render()

    def current_settings(self):
        """Read every slider into a plain dict for Fractal.render()."""
        settings = {}
        for key, param in self.fractal.params.items():
            value = self.param_vars[key].get()
            settings[key] = int(round(value)) if param.is_int else value
        settings["palette"] = self.palette_choice.get()
        return settings

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def schedule_render(self):
        """Ask for a redraw soon. If more changes arrive first (for example
        while a slider is dragged), only the last one is actually drawn."""
        if self.pending_render is not None:
            self.root.after_cancel(self.pending_render)
        self.pending_render = self.root.after(RENDER_DELAY_MS, self.render)

    def render(self):
        """Hand a render job to the background thread and return at once,
        so the window never freezes."""
        self.pending_render = None
        width, height = self.canvas_size
        if width < 2 or height < 2:
            return

        self.generation += 1
        self.jobs.put((self.generation, self.fractal, width, height,
                       self.view, self.current_settings()))
        self.last_render_info = "Rendering…"
        self._update_status()

    def _render_worker(self):
        """Runs forever in a background thread.

        Important: this thread must NEVER touch tkinter widgets (tkinter is
        not thread-safe). It only computes images and puts them in a queue.
        """
        while True:
            job = self.jobs.get()             # wait for work
            while not self.jobs.empty():      # skip to the newest request
                job = self.jobs.get_nowait()
            generation, fractal, width, height, view, settings = job

            # If full renders are slow, show a blurry low-resolution version
            # first (16x fewer pixels, so it's almost instant), then the sharp one.
            if self.last_full_time > PREVIEW_IF_SLOWER_THAN:
                scales = [PREVIEW_SCALE, 1]
            else:
                scales = [1]

            for scale in scales:
                if generation != self.generation or not self.jobs.empty():
                    break  # a newer request arrived; stop wasting time on this one
                start = time.perf_counter()
                image = fractal.render(max(1, width // scale),
                                       max(1, height // scale), view, settings)
                elapsed = time.perf_counter() - start
                final = scale == 1
                if final:
                    self.last_full_time = elapsed
                else:
                    image = image.resize((width, height), Image.BILINEAR)
                self.results.put((generation, image, view, fractal, final, elapsed))

    def _poll_results(self):
        """Runs on the GUI thread every few ms: show any finished pictures."""
        try:
            while True:
                generation, image, view, fractal, final, elapsed = \
                    self.results.get_nowait()
                if generation == self.generation:  # ignore outdated pictures
                    self._show_image(image, view, fractal, final, elapsed)
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll_results)

    def _show_image(self, image, view, fractal, final, elapsed):
        self.shown_image, self.shown_view, self.shown_fractal = image, view, fractal
        self._display(image)
        if final:
            self.image = image  # this is what "Save PNG" saves
            self.last_render_info = f"Rendered in {elapsed:.2f} s"
            self._update_status()

    def _display(self, image):
        # tkinter only shows the picture while we hold a reference to it,
        # hence self.photo.
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete("image")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="image")
        self.canvas.tag_lower("image")  # keep the zoom box drawn on top

    def _show_zoom_preview(self):
        """Instantly stretch the picture already on screen to match the new
        view. It looks blurry for a moment until the real render arrives,
        but the zoom feels immediate."""
        if (self.shown_image is None or self.shown_fractal is not self.fractal
                or self.shown_image.size != self.canvas_size):
            return
        width, height = self.canvas_size
        old_cx, old_cy, old_w = self.shown_view
        new_cx, new_cy, new_w = self.view
        old_h, new_h = old_w * height / width, new_w * height / width

        # For each pixel of the new picture, work out which pixel of the old
        # picture shows the same maths point:  old = scale * new + offset.
        scale = new_w / old_w
        x_offset = ((new_cx - new_w / 2) - (old_cx - old_w / 2)) / old_w * width
        y_offset = ((old_cy + old_h / 2) - (new_cy + new_h / 2)) / old_h * height
        preview = self.shown_image.transform(
            self.canvas_size, Image.AFFINE,
            (scale, 0, x_offset, 0, scale, y_offset), resample=Image.BILINEAR)
        self._display(preview)

    def _update_status(self, point=None):
        parts = []
        if point is not None:
            parts.append(f"x = {point[0]:.10f}   y = {point[1]:.10f}")
        parts.append(self._zoom_text())
        parts.append(self.last_render_info)
        parts.append("numba: on" if ACCELERATED else "numba: off (slow mode)")
        self.status.set("  |  ".join(parts))

    def save_png(self):
        if self.image is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG image", "*.png")],
            initialfile=f"{self.fractal.name.lower()}.png")
        if path:
            self.image.save(path)
            self.status.set(f"Saved {path}")

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------

    def _bind_mouse(self):
        c = self.canvas
        c.bind("<Configure>", self.on_resize)
        c.bind("<ButtonPress-1>", self.on_left_press)
        c.bind("<B1-Motion>", self.on_left_drag)
        c.bind("<ButtonRelease-1>", self.on_left_release)
        c.bind("<Button-3>", lambda e: self.zoom_centered(e.x, e.y, 2.0))
        c.bind("<Motion>", self.on_mouse_move)
        # Scroll wheel: Linux sends Button-4/5, Windows and macOS send MouseWheel.
        c.bind("<Button-4>", lambda e: self.zoom_fixed(e.x, e.y, 0.8))
        c.bind("<Button-5>", lambda e: self.zoom_fixed(e.x, e.y, 1.25))
        c.bind("<MouseWheel>",
               lambda e: self.zoom_fixed(e.x, e.y, 0.8 if e.delta > 0 else 1.25))

    def on_resize(self, event):
        self.canvas_size = (event.width, event.height)
        self.schedule_render()

    def to_point(self, px, py):
        """Screen pixel -> maths coordinates in the current view."""
        width, height = self.canvas_size
        return pixel_to_point(px, py, width, height, self.view)

    def on_left_press(self, event):
        shift_held = event.state & 0x0001
        self.drag_start = (event.x, event.y, shift_held)

    def on_left_drag(self, event):
        if self.drag_start is None or not self.fractal.zoomable:
            return
        x0, y0, _ = self.drag_start
        self.canvas.delete("box")
        if abs(event.x - x0) > DRAG_THRESHOLD or abs(event.y - y0) > DRAG_THRESHOLD:
            self.canvas.create_rectangle(x0, y0, event.x, event.y,
                                         outline="white", dash=(4, 2), tags="box")

    def on_left_release(self, event):
        if self.drag_start is None:
            return
        x0, y0, shift_held = self.drag_start
        self.drag_start = None
        dragged = self.canvas.find_withtag("box")
        self.canvas.delete("box")

        if shift_held and self.fractal.name == "Mandelbrot" and "Julia" in REGISTRY:
            self.open_julia_at(event.x, event.y)
        elif dragged:
            self.zoom_to_box(x0, y0, event.x, event.y)
        else:
            self.zoom_centered(event.x, event.y, 0.5)

    def on_mouse_move(self, event):
        if self.view is None:
            return
        self._update_status(self.to_point(event.x, event.y))

    # ------------------------------------------------------------------
    # Zooming. `factor` < 1 zooms in, > 1 zooms out.
    # ------------------------------------------------------------------

    def zoom_centered(self, px, py, factor):
        """Zoom and move the clicked point to the centre of the screen."""
        if not self.fractal.zoomable:
            return
        x, y = self.to_point(px, py)
        self.view = (x, y, self.view[2] * factor)
        self._view_changed()

    def zoom_fixed(self, px, py, factor):
        """Zoom while keeping the point under the cursor in the same place
        (feels natural with a scroll wheel)."""
        if not self.fractal.zoomable:
            return
        x, y = self.to_point(px, py)
        cx, cy, w = self.view
        self.view = (x + (cx - x) * factor, y + (cy - y) * factor, w * factor)
        self._view_changed()

    def zoom_to_box(self, x0, y0, x1, y1):
        width, height = self.canvas_size
        cx, cy = self.to_point((x0 + x1) / 2, (y0 + y1) / 2)
        # Pick a width that makes the whole box fit on screen.
        scale = max(abs(x1 - x0) / width, abs(y1 - y0) / height)
        self.view = (cx, cy, self.view[2] * scale)
        self._view_changed()

    def _view_changed(self):
        self._show_zoom_preview()
        self.schedule_render()

    def open_julia_at(self, px, py):
        """Each point c of the Mandelbrot set has its own Julia set."""
        x, y = self.to_point(px, py)
        self.switch_fractal("Julia")
        self.param_vars["c_real"].set(round(x, 3))
        self.param_vars["c_imag"].set(round(y, 3))
        self.schedule_render()

    def _zoom_text(self):
        zoom = self.fractal.default_view()[2] / self.view[2]
        return f"Zoom {zoom:,.1f}×"
