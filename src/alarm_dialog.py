"""Top-most Alarm Dialog with Dismiss, 5m/15m Snooze, and Action Center alert."""
import tkinter as tk
from tkinter import ttk
from src.config import COLORS, FONT_FAMILY
from src.storage import Storage
from src.notifications import show_toast

class AlarmDialog(tk.Toplevel):
    def __init__(self, master, title_text: str, reminder_name: str, on_dismiss, on_snooze, category: str = ""):
        super().__init__(master)
        self.title("⏰ Alarm Alert!")
        self.geometry("450x280")
        self.configure(bg=COLORS["bg_dark"])
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.on_dismiss = on_dismiss
        self.on_snooze = on_snooze
        self.category = category

        settings = Storage.load_settings()
        self.default_snooze = settings.get("default_snooze_minutes", 5)

        # Trigger native Windows Action Center Toast in addition to modal dialog
        badge_prefix = f"[{category}] " if category and category != "General" else ""
        show_toast(f"{badge_prefix}{title_text}", f"Time is up! {reminder_name}")

        self._build_ui(title_text, reminder_name)
        self.protocol("WM_DELETE_WINDOW", self._handle_dismiss)

    def _build_ui(self, title_text: str, reminder_name: str):
        badge_text = f"⏰ TIME IS UP! • {self.category.upper()}" if self.category and self.category != "General" else "⏰ TIME IS UP!"
        badge = tk.Label(
            self, text=badge_text, font=(FONT_FAMILY, 10, "bold"),
            bg=COLORS["surface"], fg=COLORS["accent_warning"], padx=12, pady=4
        )
        badge.pack(pady=(16, 4))

        lbl_title = tk.Label(
            self, text=title_text, font=(FONT_FAMILY, 15, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["text"], wraplength=410
        )
        lbl_title.pack(pady=2)

        lbl_desc = tk.Label(
            self, text=f"Reminder: {reminder_name}", font=(FONT_FAMILY, 11),
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"], wraplength=410
        )
        lbl_desc.pack(pady=(0, 16))

        # Action Buttons & Snooze Selector
        action_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        action_frame.pack(side="bottom", pady=20, fill="x", padx=20)

        btn_dismiss = tk.Button(
            action_frame, text="Turn Off / Dismiss", font=(FONT_FAMILY, 11, "bold"),
            bg=COLORS["accent_danger"], fg="white", activebackground="#dc2626",
            relief="flat", cursor="hand2", padx=16, pady=8, command=self._handle_dismiss
        )
        btn_dismiss.pack(side="left", padx=(0, 10))

        snooze_box = tk.Frame(action_frame, bg=COLORS["surface"], padx=8, pady=4)
        snooze_box.pack(side="right")

        self.snooze_choice = tk.IntVar(value=self.default_snooze)
        snooze_dropdown = ttk.Combobox(
            snooze_box, textvariable=self.snooze_choice, values=[5, 15],
            width=3, state="readonly", font=(FONT_FAMILY, 10)
        )
        snooze_dropdown.pack(side="left", padx=4)

        btn_snooze = tk.Button(
            snooze_box, text="Snooze (min)", font=(FONT_FAMILY, 10, "bold"),
            bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"],
            relief="flat", cursor="hand2", padx=10, pady=4, command=self._handle_snooze
        )
        btn_snooze.pack(side="left", padx=4)

    def _handle_dismiss(self):
        self.destroy()
        if self.on_dismiss:
            self.on_dismiss()

    def _handle_snooze(self):
        mins = self.snooze_choice.get()
        self.destroy()
        if self.on_snooze:
            self.on_snooze(mins)
