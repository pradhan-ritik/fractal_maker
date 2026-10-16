"""Start the Fractal Maker. Run with:  python3 main.py"""

import tkinter as tk

from app import FractalApp


def main():
    root = tk.Tk()
    FractalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
