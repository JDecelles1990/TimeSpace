"""Radial Circular Progress Ring for countdown visualization drawn with Tkinter Canvas."""
import math
import tkinter as tk
from src.config import COLORS, FONT_FAMILY

class CircularProgressRing(tk.Frame):
    def __init__(self, parent, size: int = 210, ring_width: int = 10, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)
        self.size = size
        self.ring_width = ring_width
        self.padding = 16

        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg=COLORS["bg_dark"],
            highlightthickness=0
        )
        self.canvas.pack(anchor="center", pady=4)

        self._draw_static()

    def _get_coords(self):
        p = self.padding
        return p, p, self.size - p, self.size - p

    def _draw_static(self):
        self.canvas.delete("all")
        x0, y0, x1, y1 = self._get_coords()

        # Background track arc (full 360 circle)
        self.canvas.create_oval(
            x0, y0, x1, y1,
            outline=COLORS["surface"],
            width=self.ring_width
        )

        # Active progress arc
        self.arc_item = self.canvas.create_arc(
            x0, y0, x1, y1,
            start=90,
            extent=360,
            outline=COLORS["accent"],
            width=self.ring_width,
            style=tk.ARC
        )

        # Center typography
        center_x = self.size / 2
        center_y = self.size / 2

        self.text_time = self.canvas.create_text(
            center_x, center_y - 10,
            text="00:00",
            font=(FONT_FAMILY, 24, "bold"),
            fill=COLORS["text"]
        )

        self.text_title = self.canvas.create_text(
            center_x, center_y + 22,
            text="Ready",
            font=(FONT_FAMILY, 9),
            fill=COLORS["text_muted"]
        )

        self.text_badge = self.canvas.create_text(
            center_x, center_y + 38,
            text="",
            font=(FONT_FAMILY, 8, "bold"),
            fill=COLORS["accent_warning"]
        )

    def update_countdown(
        self,
        remaining_sec: float,
        total_sec: float,
        title: str = "",
        is_repeating: bool = False,
        is_paused: bool = False
    ):
        """Update the arc progress and central time readout."""
        remaining_sec = max(0.0, remaining_sec)
        total_sec = max(1.0, total_sec)

        ratio = min(1.0, remaining_sec / total_sec)
        extent = ratio * 359.9

        # Color changes dynamically or shows paused
        if is_paused:
            arc_color = COLORS["surface_light"]
        elif ratio < 0.10:
            arc_color = COLORS["accent_danger"]
        elif ratio < 0.25:
            arc_color = COLORS["accent_warning"]
        else:
            arc_color = COLORS["accent"]

        # Update arc
        self.canvas.itemconfig(self.arc_item, extent=-extent, outline=arc_color)

        # Format time digits
        total_int = int(math.ceil(remaining_sec))
        m, s = divmod(total_int, 60)
        h, m = divmod(m, 60)
        if h > 0:
            time_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            time_str = f"{m:02d}:{s:02d}"

        self.canvas.itemconfig(self.text_time, text=time_str)
        truncated_title = title if len(title) <= 20 else title[:18] + "…"
        self.canvas.itemconfig(self.text_title, text=truncated_title or "Countdown")

        if is_paused:
            badge_text = "⏸️ PAUSED"
            badge_color = COLORS["accent_warning"]
        elif is_repeating:
            badge_text = "🔁 Repeat"
            badge_color = COLORS["accent_success"]
        else:
            badge_text = ""
            badge_color = COLORS["accent_warning"]

        self.canvas.itemconfig(self.text_badge, text=badge_text, fill=badge_color)

    def set_idle(self):
        """Reset ring to calm waiting state."""
        self.canvas.itemconfig(self.arc_item, extent=0, outline=COLORS["surface_light"])
        self.canvas.itemconfig(self.text_time, text="--:--")
        self.canvas.itemconfig(self.text_title, text="No active timer")
        self.canvas.itemconfig(self.text_badge, text="")
