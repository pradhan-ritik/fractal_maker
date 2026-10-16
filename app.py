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

RENDER_DELAY_MS = 40  # wait this long after the last change before redrawing
POLL_MS = 15          # how often the window checks for finished pictures
DRAG_THRESHOLD = 6    # pixels the mouse must move before a drag counts as a box

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

        self.fractal = None        # the current Fractal object
        self.view = None           # (center_x, center_y, width) in maths coords
        self.param_vars = {}       # param key -> tk variable behind its slider
        self.canvas_size = (1, 1)
        self.image = None          # last finished picture (what "Save PNG" saves)
        self.image_view = None     # the view that picture shows
        self.render_info = ""
        self.pending_render = None
        self.drag_start = None

        # Rendering happens in a background thread so the window never
        # freezes. The window puts jobs in `jobs`; the thread puts finished
        # pictures in `results`. Every job gets a new `generation` number,
        # so pictures from outdated jobs can be recognised and thrown away.
        self.generation = 0
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        threading.Thread(target=self.render_worker, daemon=True).start()

        self.build_layout()
        self.bind_mouse()
        self.switch_fractal(next(iter(REGISTRY)))
        self.poll_results()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def build_layout(self):
        self.status = tk.StringVar()
        tk.Label(self.root, textvariable=self.status, anchor="w",
                 relief="sunken", padx=6).pack(side="bottom", fill="x")

        sidebar = ttk.Frame(self.root, padding=10, width=260)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)  # keep the sidebar at its fixed width

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0,
                                cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.fractal_choice = self.add_dropdown(
            sidebar, "Fractal", list(REGISTRY),
            lambda name: self.switch_fractal(name))
        self.palette_choice = self.add_dropdown(
            sidebar, "Colour palette", list(PALETTES),
            lambda name: self.schedule_render())
        self.palette_choice.set(next(iter(PALETTES)))

        # Filled in by switch_fractal(), because each fractal has its own
        # sliders and presets.
        self.params_frame = ttk.Frame(sidebar)
        self.params_frame.pack(fill="x")

        buttons = ttk.Frame(sidebar)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="Reset view", command=self.reset_view
                   ).pack(side="left", expand=True, fill="x")
        ttk.Button(buttons, text="Save PNG…", command=self.save_png
                   ).pack(side="left", expand=True, fill="x")

        ttk.Label(sidebar, text=HELP_TEXT, justify="left",
                  foreground="#555").pack(anchor="w", pady=(10, 0))

    def add_dropdown(self, parent, label, options, on_select):
        """A label plus a dropdown list. Calls on_select(choice) when the
        user picks something. Returns the variable holding the choice."""
        ttk.Label(parent, text=label).pack(anchor="w")
        choice = tk.StringVar()
        box = ttk.Combobox(parent, textvariable=choice, values=options,
                           state="readonly")
        box.pack(fill="x", pady=(0, 10))
        box.bind("<<ComboboxSelected>>", lambda event: on_select(choice.get()))
        return choice

    def build_param_controls(self):
        """Create one slider per fractal parameter, plus a preset menu."""
        for child in self.params_frame.winfo_children():
            child.destroy()
        self.param_vars = {}

        if self.fractal.presets:
            preset = self.add_dropdown(self.params_frame, "Presets",
                                       list(self.fractal.presets), self.apply_preset)
            preset.set("Choose a preset…")

        for key, param in self.fractal.params.items():
            ttk.Label(self.params_frame, text=param.label).pack(anchor="w")
            var = tk.DoubleVar(value=param.default)
            tk.Scale(self.params_frame, variable=var, orient="horizontal",
                     from_=param.min, to=param.max, resolution=param.step,
                     command=lambda value: self.schedule_render()
                     ).pack(fill="x", pady=(0, 6))
            self.param_vars[key] = var

    # ------------------------------------------------------------------
    # Switching fractals, presets and views
    # ------------------------------------------------------------------

    def switch_fractal(self, name):
        self.fractal = REGISTRY[name]()
        self.fractal_choice.set(name)
        self.build_param_controls()
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
        settings = {"palette": self.palette_choice.get()}
        for key, param in self.fractal.params.items():
            value = self.param_vars[key].get()
            # Sliders always give decimals; round them for whole-number params.
            settings[key] = round(value) if isinstance(param.default, int) else value
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
        """Hand a job to the background thread and return straight away."""
        self.pending_render = None
        width, height = self.canvas_size
        self.generation += 1
        self.jobs.put((self.generation, self.fractal, width, height,
                       self.view, self.current_settings()))
        self.render_info = "Rendering…"
        self.update_status()

    def render_worker(self):
        """Runs forever in the background thread.

        Important: this thread must NEVER touch tkinter widgets (tkinter is
        not thread-safe). It only computes pictures and puts them in a queue.
        """
        while True:
            job = self.jobs.get()            # wait for work
            while not self.jobs.empty():     # skip straight to the newest job
                job = self.jobs.get()
            generation, fractal, width, height, view, settings = job

            start = time.perf_counter()
            image = fractal.render(width, height, view, settings)
            seconds = time.perf_counter() - start
            self.results.put((generation, image, view, seconds))

    def poll_results(self):
        """Runs in the window's thread every few ms: show finished pictures."""
        while not self.results.empty():
            generation, image, view, seconds = self.results.get()
            if generation == self.generation:  # ignore outdated pictures
                self.image, self.image_view = image, view
                self.display(image)
                self.render_info = f"Rendered in {seconds:.2f} s"
                self.update_status()
        self.root.after(POLL_MS, self.poll_results)

    def display(self, image):
        # tkinter only shows the picture while we keep a reference to it,
        # hence self.photo.
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete("image")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="image")
        self.canvas.tag_lower("image")  # keep the zoom box drawn on top

    def show_zoom_preview(self):
        """Instantly stretch the last picture to match the new view. It looks
        blurry for a moment until the real render arrives, but the zoom
        feels immediate."""
        if self.image is None or self.image.size != self.canvas_size:
            return
        width, height = self.canvas_size
        old_cx, old_cy, old_w = self.image_view
        new_cx, new_cy, new_w = self.view
        old_h, new_h = old_w * height / width, new_w * height / width

        # For each pixel of the new picture, work out which pixel of the old
        # picture shows the same maths point:  old = scale * new + offset.
        scale = new_w / old_w
        x_offset = ((new_cx - new_w / 2) - (old_cx - old_w / 2)) / old_w * width
        y_offset = ((old_cy + old_h / 2) - (new_cy + new_h / 2)) / old_h * height
        preview = self.image.transform(
            self.canvas_size, Image.AFFINE,
            (scale, 0, x_offset, 0, scale, y_offset), resample=Image.BILINEAR)
        self.display(preview)

    def update_status(self, point=None):
        zoom = self.fractal.default_view()[2] / self.view[2]
        parts = [f"Zoom {zoom:,.1f}×", self.render_info]
        if point is not None:
            parts.insert(0, f"x = {point[0]:.10f}   y = {point[1]:.10f}")
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

    def bind_mouse(self):
        c = self.canvas
        c.bind("<Configure>", self.on_resize)
        c.bind("<ButtonPress-1>", self.on_left_press)
        c.bind("<B1-Motion>", self.on_left_drag)
        c.bind("<ButtonRelease-1>", self.on_left_release)
        c.bind("<Button-3>", lambda e: self.zoom_centered(e.x, e.y, 2.0))
        c.bind("<Motion>", lambda e: self.update_status(self.to_point(e.x, e.y)))
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
        x0, y0, _ = self.drag_start
        self.canvas.delete("box")
        if abs(event.x - x0) > DRAG_THRESHOLD or abs(event.y - y0) > DRAG_THRESHOLD:
            self.canvas.create_rectangle(x0, y0, event.x, event.y,
                                         outline="white", dash=(4, 2), tags="box")

    def on_left_release(self, event):
        x0, y0, shift_held = self.drag_start
        dragged = self.canvas.find_withtag("box")
        self.canvas.delete("box")

        if shift_held and self.fractal.name == "Mandelbrot":
            self.open_julia_at(event.x, event.y)
        elif dragged:
            self.zoom_to_box(x0, y0, event.x, event.y)
        else:
            self.zoom_centered(event.x, event.y, 0.5)

    # ------------------------------------------------------------------
    # Zooming. `factor` < 1 zooms in, > 1 zooms out.
    # ------------------------------------------------------------------

    def zoom_centered(self, px, py, factor):
        """Zoom and move the clicked point to the centre of the screen."""
        x, y = self.to_point(px, py)
        self.set_view(x, y, self.view[2] * factor)

    def zoom_fixed(self, px, py, factor):
        """Zoom while keeping the point under the cursor in the same place
        (feels natural with a scroll wheel)."""
        x, y = self.to_point(px, py)
        cx, cy, w = self.view
        self.set_view(x + (cx - x) * factor, y + (cy - y) * factor, w * factor)

    def zoom_to_box(self, x0, y0, x1, y1):
        width, height = self.canvas_size
        cx, cy = self.to_point((x0 + x1) / 2, (y0 + y1) / 2)
        # Pick a width that makes the whole box fit on screen.
        scale = max(abs(x1 - x0) / width, abs(y1 - y0) / height)
        self.set_view(cx, cy, self.view[2] * scale)

    def set_view(self, cx, cy, w):
        """Every zoom ends up here."""
        if not self.fractal.zoomable:
            return
        self.view = (cx, cy, w)
        self.show_zoom_preview()
        self.schedule_render()

    def open_julia_at(self, px, py):
        """Each point c of the Mandelbrot set has its own Julia set."""
        x, y = self.to_point(px, py)
        self.switch_fractal("Julia")
        self.param_vars["c_real"].set(round(x, 3))
        self.param_vars["c_imag"].set(round(y, 3))
