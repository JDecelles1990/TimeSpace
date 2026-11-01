"""Floating Mini HUD: compact, draggable, always-on-top desktop widget for IT Helpdesk / multi-monitor setups."""
import tkinter as tk
from typing import Optional, Callable
from src.config import COLORS, FONT_FAMILY

class FloatingMiniHUD(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_bring_main_to_front: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        initial_x: int = 120,
        initial_y: int = 80
    ):
        super().__init__(master)
        self.on_toggle_pause = on_toggle_pause
        self.on_bring_main_to_front = on_bring_main_to_front
        self.on_close_cb = on_close

        # Window configuration
        self.title("Mini HUD")
        self.overrideredirect(True)      # Borderless modern HUD
        self.attributes("-topmost", True) # Always-on-top
        self.attributes("-alpha", 0.94)   # Subtle translucency
        self.configure(bg="#27272a")

        # Size and position
        self.width = 280
        self.height = 42
        self.geometry(f"{self.width}x{self.height}+{initial_x}+{initial_y}")

        # Dragging mechanics
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()
        self._bind_drag_events()

    def _build_ui(self):
        # Outer border frame
        self.outer_frame = tk.Frame(self, bg=COLORS["accent"], padx=1, pady=1)
        self.outer_frame.pack(fill="both", expand=True)

        # Inner container
        self.inner_frame = tk.Frame(self.outer_frame, bg="#18181b", padx=6, pady=4)
        self.inner_frame.pack(fill="both", expand=True)

        # Drag handle / Status Icon
        self.lbl_icon = tk.Label(
            self.inner_frame, text="⏳", font=(FONT_FAMILY, 10),
            bg="#18181b", fg=COLORS["text"], cursor="fleur"
        )
        self.lbl_icon.pack(side="left", padx=(0, 4))

        # Title / Ticket Name
        self.lbl_title = tk.Label(
            self.inner_frame, text="All Quiet", font=(FONT_FAMILY, 8, "bold"),
            bg="#18181b", fg=COLORS["text"], anchor="w", width=14, cursor="hand2"
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        # Countdown display
        self.lbl_countdown = tk.Label(
            self.inner_frame, text="--:--", font=(FONT_FAMILY, 10, "bold"),
            bg="#18181b", fg=COLORS["accent"], cursor="hand2"
        )
        self.lbl_countdown.pack(side="left", padx=(4, 6))

        # Pause / Resume quick button
        self.btn_pause = tk.Button(
            self.inner_frame, text="⏯️", font=(FONT_FAMILY, 8),
            bg="#27272a", fg=COLORS["text"], activebackground=COLORS["accent"],
            relief="flat", cursor="hand2", padx=4, pady=1, command=self._handle_pause
        )
        self.btn_pause.pack(side="left", padx=(0, 4))

        # Close button
        btn_close = tk.Button(
            self.inner_frame, text="✕", font=(FONT_FAMILY, 8),
            bg="#27272a", fg=COLORS["text_muted"], activebackground=COLORS["accent_danger"],
            relief="flat", cursor="hand2", padx=4, pady=1, command=self.close_hud
        )
        btn_close.pack(side="right")

    def _bind_drag_events(self):
        # Bind dragging on the frames and text labels
        drag_targets = [self.outer_frame, self.inner_frame, self.lbl_icon, self.lbl_title, self.lbl_countdown]
        for w in drag_targets:
            w.bind("<ButtonPress-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<Double-Button-1>", self._on_double_click)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag_motion(self, event):
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.geometry(f"+{new_x}+{new_y}")

    def _on_double_click(self, _event):
        if self.on_bring_main_to_front:
            self.on_bring_main_to_front()

    def _handle_pause(self):
        if self.on_toggle_pause:
            self.on_toggle_pause()

    def update_status(self, name: str, remaining_sec: float, is_paused: bool = False, is_sla: bool = False):
        """Update live status display and adapt colors based on SLA urgency."""
        if is_paused:
            rem = int(remaining_sec)
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            self.lbl_countdown.config(text=f"⏸ {h:02d}:{m:02d}:{s:02d}", fg=COLORS["text_muted"])
            self.lbl_icon.config(text="⏸️")
            self.outer_frame.config(bg="#52525b")
        elif remaining_sec <= 0:
            self.lbl_countdown.config(text="🚨 00:00", fg=COLORS["accent_danger"])
            self.lbl_icon.config(text="🚨")
            self.outer_frame.config(bg=COLORS["accent_danger"])
        else:
            rem = int(remaining_sec)
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

            # Urgency styling
            if remaining_sec < 60:
                # Under 1 minute (Critical / SLA Breach imminent)
                color = COLORS["accent_danger"]
                icon = "🚨" if is_sla else "⏱️"
            elif remaining_sec < 300:
                # Under 5 minutes (Warning)
                color = COLORS["accent_warning"]
                icon = "⚡" if is_sla else "⏳"
            else:
                # Normal
                color = "#818cf8"
                icon = "🎫" if is_sla else "⏳"

            self.lbl_countdown.config(text=time_str, fg=color)
            self.lbl_icon.config(text=icon)
            self.outer_frame.config(bg=color)

        # Truncate title cleanly
        display_name = name if len(name) <= 15 else name[:13] + ".."
        self.lbl_title.config(text=display_name)

    def set_idle(self):
        """Set HUD to idle state when no timers are active."""
        self.lbl_icon.config(text="✅")
        self.lbl_title.config(text="All Quiet")
        self.lbl_countdown.config(text="00:00", fg=COLORS["text_muted"])
        self.outer_frame.config(bg=COLORS["surface_light"])

    def close_hud(self):
        self.withdraw()
        if self.on_close_cb:
            self.on_close_cb()
