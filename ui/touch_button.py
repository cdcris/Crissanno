"""Touch-friendly controls used by the ServeScan interface."""

from __future__ import annotations

from typing import Callable, Optional
import tkinter as tk
from tkinter import font as tkfont

from ui.theme import COLORS, FONT_FAMILY


class TouchButton(tk.Canvas):
    """Compact icon button designed for a seven-inch touch display."""

    def __init__(
        self,
        parent,
        text: str,
        icon: str,
        command: Callable[[], None],
        color: str,
        hover: str,
        width: int,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=52,
            bg=COLORS["surface"],
            highlightthickness=0,
            cursor="hand2",
            takefocus=True,
            **kwargs,
        )
        self.label = text
        self.icon = icon
        self.command = command
        self.normal_color = color
        self.hover_color = hover
        self.enabled = True
        self._pressed = False
        self.bind("<Configure>", lambda _event: self.draw())
        self.bind("<Enter>", lambda _event: self.draw(self.hover_color))
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<space>", lambda _event: self.invoke())
        self.bind("<Return>", lambda _event: self.invoke())

    def configure_content(self, text: str, icon: str, color: str, hover: str) -> None:
        self.label, self.icon = text, icon
        self.normal_color, self.hover_color = color, hover
        self.draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.draw()

    def invoke(self) -> None:
        if self.enabled:
            self.command()

    def _press(self, _event) -> None:
        if self.enabled:
            self._pressed = True
            self.focus_set()
            self.draw(self.hover_color)

    def _release(self, event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self.draw(self.hover_color if inside else self.normal_color)
        if was_pressed and inside:
            self.invoke()

    def _leave(self, _event) -> None:
        self._pressed = False
        self.draw()

    def _round_rect(self, x1, y1, x2, y2, radius, **kwargs) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, **kwargs)

    @staticmethod
    def content_layout(width: int) -> tuple[float | None, float, int, str]:
        """Return responsive icon and label geometry for the available width."""
        if width < 95:
            return None, width / 2, 8, "center"
        if width < 145:
            return 17, (width + 24) / 2, 9, "center"
        return 25, (width + 30) / 2, 10, "center"

    @staticmethod
    def show_icon(icon: str, width: int) -> bool:
        """Hide the wide mode-switch icon when it would overlap its label."""
        return not (icon == "switch" and width < 165)

    @staticmethod
    def text_region(width: int, with_icon: bool) -> tuple[float, int]:
        """Return a centered label region contained within the button."""
        left = 36 if with_icon else 8
        right = max(width - 8, left + 1)
        return (left + right) / 2, max(right - left, 1)

    def _fit_content(self, width: int) -> tuple[float | None, float, int, int, str]:
        """Fit the icon and a single-line label inside the current width."""
        cx, _text_x, preferred_size, _anchor = self.content_layout(width)
        use_icon = cx is not None and self.show_icon(self.icon, width)

        def font_for(size: int) -> tkfont.Font:
            return tkfont.Font(
                root=self, family=FONT_FAMILY, size=size, weight="bold"
            )

        def fitting_size(max_width: int) -> tuple[int, tkfont.Font]:
            for size in range(preferred_size, 6, -1):
                label_font = font_for(size)
                if label_font.measure(self.label) <= max_width:
                    return size, label_font
            return 7, font_for(7)

        text_x, text_width = self.text_region(width, use_icon)
        font_size, label_font = fitting_size(text_width)
        if use_icon and label_font.measure(self.label) > text_width:
            use_icon = False
            cx = None
            text_x, text_width = self.text_region(width, False)
            font_size, label_font = fitting_size(text_width)

        label = self.label
        if label_font.measure(label) > text_width:
            ellipsis = "…"
            if label_font.measure(ellipsis) > text_width:
                label = ""
            else:
                while label and label_font.measure(label.rstrip() + ellipsis) > text_width:
                    label = label[:-1]
                label = label.rstrip() + ellipsis if label else ellipsis

        return cx if use_icon else None, text_x, font_size, text_width, label

    def draw(self, color: Optional[str] = None) -> None:
        self.delete("all")
        width, height = max(self.winfo_width(), 20), max(self.winfo_height(), 20)
        fill = color or self.normal_color
        if not self.enabled:
            fill = COLORS["surface_soft"]
        self._round_rect(2, 2, width - 2, height - 2, 11, fill=fill, outline="")
        icon_color = COLORS["white"] if self.enabled else COLORS["text_muted"]
        cx, text_x, font_size, text_width, label = self._fit_content(width)
        cy = height / 2
        if cx is None:
            pass
        elif self.icon == "capture":
            self.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill=icon_color, outline="")
            self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=fill, outline="")
        elif self.icon == "pause":
            self.create_rectangle(cx - 9, cy - 11, cx - 3, cy + 11, fill=icon_color, outline="")
            self.create_rectangle(cx + 3, cy - 11, cx + 9, cy + 11, fill=icon_color, outline="")
        elif self.icon == "resume":
            self.create_polygon(
                cx - 7, cy - 12, cx + 11, cy, cx - 7, cy + 12,
                fill=icon_color, outline="",
            )
        elif self.icon == "stop":
            self.create_rectangle(cx - 10, cy - 10, cx + 10, cy + 10, fill=icon_color, outline="")
        elif self.icon == "upload":
            self.create_line(cx, cy + 11, cx, cy - 9, fill=icon_color, width=3)
            self.create_line(cx, cy - 9, cx - 7, cy - 2, fill=icon_color, width=3)
            self.create_line(cx, cy - 9, cx + 7, cy - 2, fill=icon_color, width=3)
            self.create_line(cx - 10, cy + 5, cx - 10, cy + 12, cx + 10, cy + 12,
                             cx + 10, cy + 5, fill=icon_color, width=2)
        elif self.icon == "switch":
            self.create_line(cx - 10, cy - 6, cx + 8, cy - 6, fill=icon_color, width=2)
            self.create_line(cx + 8, cy - 6, cx + 3, cy - 11, fill=icon_color, width=2)
            self.create_line(cx + 8, cy - 6, cx + 3, cy - 1, fill=icon_color, width=2)
            self.create_line(cx + 10, cy + 6, cx - 8, cy + 6, fill=icon_color, width=2)
            self.create_line(cx - 8, cy + 6, cx - 3, cy + 1, fill=icon_color, width=2)
            self.create_line(cx - 8, cy + 6, cx - 3, cy + 11, fill=icon_color, width=2)
        self.create_text(
            text_x,
            cy,
            text=label,
            width=text_width,
            anchor="center",
            justify="center",
            fill=icon_color,
            font=(FONT_FAMILY, font_size, "bold"),
        )
