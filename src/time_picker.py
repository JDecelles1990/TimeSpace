"""Ergonomic Big-Buttons Time Picker Widget."""
import tkinter as tk
from typing import Tuple, Callable, Optional
from src.config import COLORS, FONT_FAMILY

class BigButtonsTimePicker(tk.Frame):
    def __init__(self, parent, initial_hour: int = 14, initial_minute: int = 0, on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)
        self.hour = initial_hour
        self.minute = initial_minute
        self.on_change = on_change

        self._build_ui()
        self._update_display()

    def _build_ui(self):
        # Stepper Row (Large buttons & readouts)
        stepper_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        stepper_frame.pack(pady=(0, 4))

        # Hour Stepper
        h_box = tk.Frame(stepper_frame, bg=COLORS["surface"], padx=4, pady=2)
        h_box.pack(side="left", padx=4)

        tk.Button(
            h_box, text="−", font=(FONT_FAMILY, 12, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", width=2, command=lambda: self._adjust_hour(-1)
        ).pack(side="left", padx=2)

        self.lbl_hour = tk.Label(
            h_box, text="14", font=(FONT_FAMILY, 16, "bold"),
            bg=COLORS["surface"], fg=COLORS["accent"], width=3
        )
        self.lbl_hour.pack(side="left", padx=2)

        tk.Button(
            h_box, text="+", font=(FONT_FAMILY, 12, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", width=2, command=lambda: self._adjust_hour(1)
        ).pack(side="left", padx=2)

        # Colon Separator
        tk.Label(
            stepper_frame, text=":", font=(FONT_FAMILY, 18, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"]
        ).pack(side="left", padx=2)

        # Minute Stepper
        m_box = tk.Frame(stepper_frame, bg=COLORS["surface"], padx=4, pady=2)
        m_box.pack(side="left", padx=4)

        tk.Button(
            m_box, text="−", font=(FONT_FAMILY, 12, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", width=2, command=lambda: self._adjust_minute(-5)
        ).pack(side="left", padx=2)

        self.lbl_minute = tk.Label(
            m_box, text="00", font=(FONT_FAMILY, 16, "bold"),
            bg=COLORS["surface"], fg=COLORS["accent"], width=3
        )
        self.lbl_minute.pack(side="left", padx=2)

        tk.Button(
            m_box, text="+", font=(FONT_FAMILY, 12, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", width=2, command=lambda: self._adjust_minute(5)
        ).pack(side="left", padx=2)

        # Quick Minute Chips (:00, :15, :30, :45)
        chip_row = tk.Frame(self, bg=COLORS["bg_dark"])
        chip_row.pack(pady=2)

        tk.Label(chip_row, text="Minutes:", font=(FONT_FAMILY, 8),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left", padx=(0, 4))

        for min_val in [0, 15, 30, 45]:
            tk.Button(
                chip_row, text=f":{min_val:02d}", font=(FONT_FAMILY, 8, "bold"),
                bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["accent"],
                relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda m=min_val: self.set_minute(m)
            ).pack(side="left", padx=2)

        # Quick Time Presets (Morning, Noon, Afternoon, Evening)
        preset_row = tk.Frame(self, bg=COLORS["bg_dark"])
        preset_row.pack(pady=(4, 0))

        presets = [
            ("🌅 09:00", 9, 0),
            ("☀️ 12:00", 12, 0),
            ("☕ 15:00", 15, 0),
            ("🌙 18:00", 18, 0)
        ]

        for label, h, m in presets:
            tk.Button(
                preset_row, text=label, font=(FONT_FAMILY, 8),
                bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["accent"],
                relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda h=h, m=m: self.set_time(h, m)
            ).pack(side="left", padx=2)

    def _adjust_hour(self, delta: int):
        self.hour = (self.hour + delta) % 24
        self._update_display()

    def _adjust_minute(self, delta: int):
        self.minute = (self.minute + delta) % 60
        self._update_display()

    def set_minute(self, m: int):
        self.minute = m % 60
        self._update_display()

    def set_time(self, h: int, m: int):
        self.hour = h % 24
        self.minute = m % 60
        self._update_display()

    def _update_display(self):
        self.lbl_hour.config(text=f"{self.hour:02d}")
        self.lbl_minute.config(text=f"{self.minute:02d}")
        if self.on_change:
            self.on_change(self.hour, self.minute)

    def get_time(self) -> Tuple[int, int]:
        return self.hour, self.minute

