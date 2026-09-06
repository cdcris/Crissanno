"""ServeScan design tokens and Tk/ttk theme configuration.

This module plays the same role as a small CSS variables file: edit the
palette or spacing here and the whole application follows.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    # ServeScan brand palette: signal red, clean white, and graphite.
    "background": "#F4F5F5",
    "surface": "#FFFFFF",
    "surface_raised": "#FFFFFF",
    "surface_soft": "#ECEEEE",
    "border": "#D4D7D8",
    "text": "#35383A",
    "text_muted": "#53575A",
    "primary": "#DA261C",
    "primary_hover": "#B91F17",
    "success": "#287A57",
    "success_hover": "#206347",
    "danger": "#DA261C",
    "danger_hover": "#B91F17",
    "warning": "#A5620E",
    "warning_hover": "#844D0B",
    # The camera viewport stays dark so footage remains the visual focus.
    "preview": "#191B1C",
    "preview_overlay": "#35383A",
    "preview_border": "#6F7477",
    "preview_text": "#E6E8E8",
    "black": "#191B1C",
    "white": "#FFFFFF",
}

FONT_FAMILY = "DejaVu Sans"
MONO_FONT_FAMILY = "DejaVu Sans Mono"


class ServeScanTheme:
    """Apply the ServeScan visual language to a Tk root window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.colors = COLORS
        root.configure(background=COLORS["background"])
        root.option_add("*Font", (FONT_FAMILY, 10))

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["background"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Raised.TFrame", background=COLORS["surface_raised"])
        style.configure(
            "TLabel", background=COLORS["background"], foreground=COLORS["text"]
        )
        style.configure(
            "Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"]
        )
        style.configure(
            "Muted.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text_muted"],
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["surface_soft"],
            foreground=COLORS["text"],
            padding=(11, 5),
        )
