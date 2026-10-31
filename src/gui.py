"""Main GUI with Dark Mode, Radial Ring, Natural Language Input, Pomodoro, Settings, and Hotkey."""
import sys
import os
import time
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.config import COLORS, FONT_FAMILY, HOTKEY
from src.sound import SoundPlayer, SOUND_PRESETS
from src.storage import Storage
from src.alarm_dialog import AlarmDialog
from src.scheduler import ReminderScheduler, ScheduledItem
from src.tray import TrayManager
from src.circular_ring import CircularProgressRing
from src.natural_parser import NaturalParser
from src.calendar_export import CalendarManager
from src.calendar_widget import MiniCalendar
from src.time_picker import BigButtonsTimePicker
from src.startup import is_startup_enabled, set_startup_enabled
from src.notifications import show_toast

class MainApp(tk.Tk):
    def __init__(self, start_minimized: bool = False):
        super().__init__()
        self.title("Timer & Rendez-vous ⏰")
        self.geometry("620x860")
        self.configure(bg=COLORS["bg_dark"])

        self.settings = Storage.load_settings()
        self.sound_player = SoundPlayer()
        self.scheduler = ReminderScheduler(
            on_trigger_callback=self._on_item_triggered,
            on_wake_missed_callback=self._on_wake_missed
        )

        # Setup System Tray early to avoid race conditions
        self.tray = TrayManager(
            on_toggle=self.toggle_visibility,
            on_exit=self.quit_app,
            on_toggle_pause=self._toggle_active_timer_pause
        )
        self.tray.start()

        # Build UI Components
        self._build_styles()
        self._build_header()
        self._build_smart_input_bar()
        self._build_ring_section()
        self._build_tabs()
        self._build_active_list()

        # Handle window close (minimize to tray)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self._setup_hotkey()

        # Check for missed alarms from before launch
        self.after(500, self._check_missed_alarms)

        if start_minimized:
            self.withdraw()

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg_dark"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["surface"], foreground=COLORS["text"],
                        font=(FONT_FAMILY, 10, "bold"), padding=[14, 6])
        style.map("TNotebook.Tab", background=[("selected", COLORS["accent"])])

    def _build_header(self):
        header = tk.Frame(self, bg=COLORS["surface"], padx=16, pady=10)
        header.pack(fill="x")
        title = tk.Label(header, text="Timer & Rendez-vous ⏰", font=(FONT_FAMILY, 15, "bold"),
                         bg=COLORS["surface"], fg=COLORS["text"])
        title.pack(side="left")

        hotkey_badge = tk.Label(header, text=f"Toggle: {HOTKEY.upper()}", font=(FONT_FAMILY, 9),
                                bg=COLORS["surface_light"], fg=COLORS["accent"], padx=8, pady=3)
        hotkey_badge.pack(side="right")

    def _build_smart_input_bar(self):
        """Natural Language Quick Input Box."""
        container = tk.Frame(self, bg=COLORS["bg_dark"], padx=16, pady=6)
        container.pack(fill="x")

        lbl_desc = tk.Label(container, text="⚡ Quick Natural Input:", font=(FONT_FAMILY, 9, "bold"),
                            bg=COLORS["bg_dark"], fg=COLORS["accent"])
        lbl_desc.pack(anchor="w", pady=(0, 2))

        input_row = tk.Frame(container, bg=COLORS["bg_dark"])
        input_row.pack(fill="x")

        self.smart_entry = tk.Entry(
            input_row, bg=COLORS["surface"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=(FONT_FAMILY, 10)
        )
        self.smart_entry.insert(0, "Ring in 15 min")
        self.smart_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        self.smart_entry.bind("<Return>", lambda e: self._on_smart_input_submit())

        btn_go = tk.Button(
            input_row, text="Create ⚡", font=(FONT_FAMILY, 9, "bold"),
            bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_hover"],
            relief="flat", cursor="hand2", padx=12, pady=4, command=self._on_smart_input_submit
        )
        btn_go.pack(side="right")

        self.smart_feedback = tk.Label(
            container, text='Try: "Ring in 15 min", "RDV at 4PM", "Call Linda at 7:15 tomorrow morning"',
            font=(FONT_FAMILY, 8), bg=COLORS["bg_dark"], fg=COLORS["text_muted"]
        )
        self.smart_feedback.pack(anchor="w", pady=(2, 0))

    def _on_smart_input_submit(self):
        query = self.smart_entry.get().strip()
        parsed = NaturalParser.parse(query)
        if not parsed:
            self.smart_feedback.config(
                text='❌ Unrecognized. Try: "Ring in 15 min", "RDV at 4PM", or "Call Linda at 7:15 tomorrow morning"',
                fg=COLORS["accent_danger"]
            )
            return

        if parsed["kind"] == "timer":
            self.scheduler.add_item(
                kind="timer",
                name=parsed["name"],
                seconds_from_now=parsed["seconds_from_now"],
                original_duration=parsed["original_duration"]
            )
        else:
            self.scheduler.add_item(
                kind="rendez-vous",
                name=parsed["name"],
                seconds_from_now=parsed["seconds_from_now"]
            )

        self.smart_feedback.config(
            text=f"✅ Scheduled {parsed['display_str']}",
            fg=COLORS["accent_success"]
        )
        self.smart_entry.delete(0, tk.END)

    def _build_ring_section(self):
        """Radial circular countdown visualizer with playback controls."""
        ring_container = tk.Frame(self, bg=COLORS["bg_dark"])
        ring_container.pack(pady=(2, 4))

        self.ring = CircularProgressRing(ring_container, size=185, ring_width=9)
        self.ring.pack()

        # Play/Pause and Reset buttons under the ring
        ctrl_frame = tk.Frame(ring_container, bg=COLORS["bg_dark"])
        ctrl_frame.pack(pady=(2, 0))

        self.btn_ring_play_pause = tk.Button(
            ctrl_frame, text="⏯️ Pause", font=(FONT_FAMILY, 8, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["accent"],
            relief="flat", cursor="hand2", padx=10, pady=3, command=self._toggle_active_timer_pause
        )
        self.btn_ring_play_pause.pack(side="left", padx=4)

        self.btn_ring_reset = tk.Button(
            ctrl_frame, text="⏹️ Stop", font=(FONT_FAMILY, 8),
            bg=COLORS["surface"], fg=COLORS["text_muted"], activebackground=COLORS["accent_danger"],
            relief="flat", cursor="hand2", padx=10, pady=3, command=self._stop_active_timer
        )
        self.btn_ring_reset.pack(side="left", padx=4)

    def _build_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="x", padx=16, pady=4)

        # Tab 1: Timers
        tab_timer = tk.Frame(notebook, bg=COLORS["bg_dark"], pady=4)
        notebook.add(tab_timer, text="  Timers ⏳  ")
        self._init_timer_tab(tab_timer)

        # Tab 2: Rendez-vous
        tab_rdv = tk.Frame(notebook, bg=COLORS["bg_dark"], pady=4)
        notebook.add(tab_rdv, text="  Rendez-vous 📅  ")
        self._init_rdv_tab(tab_rdv)

        # Tab 3: Settings
        tab_settings = tk.Frame(notebook, bg=COLORS["bg_dark"], pady=4)
        notebook.add(tab_settings, text="  Settings ⚙️  ")
        self._init_settings_tab(tab_settings)

        # Tab 4: Activity Log
        tab_activity = tk.Frame(notebook, bg=COLORS["bg_dark"], pady=4)
        notebook.add(tab_activity, text="  Activity 📋  ")
        self._init_activity_tab(tab_activity)

    def _init_timer_tab(self, parent):
        # Quick Presets
        p_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        p_frame.pack(fill="x", pady=2)
        tk.Label(p_frame, text="Quick Presets:", font=(FONT_FAMILY, 9, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(anchor="w")

        btn_row = tk.Frame(p_frame, bg=COLORS["bg_dark"])
        btn_row.pack(fill="x", pady=2)
        for label, mins in [("30 Minutes", 30), ("1 Hour", 60), ("2 Hours", 120)]:
            tk.Button(
                btn_row, text=label, font=(FONT_FAMILY, 9, "bold"),
                bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["accent"],
                relief="flat", cursor="hand2", padx=10, pady=3,
                command=lambda m=mins, l=label: self.scheduler.add_item(
                    "timer", l, m * 60, original_duration=m * 60
                )
            ).pack(side="left", padx=(0, 8))

        # Custom Timer
        c_frame = tk.LabelFrame(parent, text=" Custom Timer ", font=(FONT_FAMILY, 9),
                                bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=10, pady=4)
        c_frame.pack(fill="x", pady=2)

        tk.Label(c_frame, text="Task Name:", bg=COLORS["bg_dark"], fg=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=2)
        self.entry_timer_name = tk.Entry(c_frame, bg=COLORS["surface"], fg=COLORS["text"],
                                         insertbackground=COLORS["text"], relief="flat", font=(FONT_FAMILY, 9))
        self.entry_timer_name.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2, padx=5)

        tk.Label(c_frame, text="Duration:", bg=COLORS["bg_dark"], fg=COLORS["text"]).grid(row=1, column=0, sticky="w", pady=2)
        time_row = tk.Frame(c_frame, bg=COLORS["bg_dark"])
        time_row.grid(row=1, column=1, columnspan=3, sticky="w")
        self.spin_h = tk.Spinbox(time_row, from_=0, to=24, width=3, bg=COLORS["surface"], fg=COLORS["text"])
        self.spin_m = tk.Spinbox(time_row, from_=0, to=59, width=3, bg=COLORS["surface"], fg=COLORS["text"])
        self.spin_s = tk.Spinbox(time_row, from_=0, to=59, width=3, bg=COLORS["surface"], fg=COLORS["text"])
        self.spin_h.pack(side="left"); tk.Label(time_row, text="h", bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left", padx=2)
        self.spin_m.pack(side="left"); tk.Label(time_row, text="m", bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left", padx=2)
        self.spin_s.pack(side="left"); tk.Label(time_row, text="s", bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left", padx=2)

        self.repeat_var = tk.BooleanVar(value=False)
        tk.Checkbutton(c_frame, text="Repeat automatically", variable=self.repeat_var,
                       bg=COLORS["bg_dark"], fg=COLORS["text"], selectcolor=COLORS["surface"],
                       activebackground=COLORS["bg_dark"]).grid(row=2, column=1, sticky="w", pady=2)

        tk.Button(c_frame, text="Start Timer", bg=COLORS["accent"], fg="white",
                  font=(FONT_FAMILY, 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=3,
                  command=self._start_custom_timer).grid(row=3, column=1, sticky="e", pady=3)

    def _init_rdv_tab(self, parent):
        # Two-column layout: Left column = Calendar & Agenda, Right column = Time picker & Details
        container = tk.Frame(parent, bg=COLORS["bg_dark"])
        container.pack(fill="both", expand=True, pady=2)

        # Left Column: Calendar & Selected Day Agenda
        left_col = tk.Frame(container, bg=COLORS["bg_dark"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        cal_box = tk.LabelFrame(left_col, text=" 📅 Interactive Calendar ", font=(FONT_FAMILY, 9, "bold"),
                                bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=6, pady=4)
        cal_box.pack(fill="x", pady=2)

        self.mini_calendar = MiniCalendar(cal_box, on_date_selected=self._on_calendar_date_selected)
        self.mini_calendar.pack(fill="x")

        # Day Inspector
        self.lbl_day_agenda = tk.Label(
            cal_box, text=f"{datetime.date.today().strftime('%b %d')}: No scheduled events",
            font=(FONT_FAMILY, 8), bg=COLORS["surface"], fg=COLORS["text_muted"], anchor="w", padx=6, pady=3
        )
        self.lbl_day_agenda.pack(fill="x", pady=(4, 0))

        # Right Column: Event Details & Big Buttons Time Picker
        right_col = tk.Frame(container, bg=COLORS["bg_dark"])
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0))

        details_box = tk.LabelFrame(right_col, text=" ⏰ Time & Event Details ", font=(FONT_FAMILY, 9, "bold"),
                                    bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=8, pady=4)
        details_box.pack(fill="x", pady=2)

        # Event Name
        tk.Label(details_box, text="Event Name:", font=(FONT_FAMILY, 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text"]).pack(anchor="w")
        self.entry_rdv_name = tk.Entry(details_box, bg=COLORS["surface"], fg=COLORS["text"],
                                       insertbackground=COLORS["text"], relief="flat", font=(FONT_FAMILY, 9))
        self.entry_rdv_name.insert(0, "Team Sync")
        self.entry_rdv_name.pack(fill="x", pady=(2, 4))

        # Big Buttons Time Picker
        tk.Label(details_box, text="Event Time:", font=(FONT_FAMILY, 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text"]).pack(anchor="w")
        self.time_picker = BigButtonsTimePicker(details_box, initial_hour=14, initial_minute=0)
        self.time_picker.pack(fill="x", pady=(2, 4))

        # Category & Early Warning Rows
        meta_grid = tk.Frame(details_box, bg=COLORS["bg_dark"])
        meta_grid.pack(fill="x", pady=2)

        tk.Label(meta_grid, text="Category:", font=(FONT_FAMILY, 8),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", pady=2)
        self.rdv_category_var = tk.StringVar(value="💼 Work")
        combo_cat = ttk.Combobox(
            meta_grid, textvariable=self.rdv_category_var,
            values=["💼 Work", "🩺 Health", "📞 Call", "🏠 Personal", "🎉 Social", "📌 General"],
            width=12, state="readonly"
        )
        combo_cat.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        tk.Label(meta_grid, text="Early Alert:", font=(FONT_FAMILY, 8),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).grid(row=1, column=0, sticky="w", pady=2)
        self.rdv_lead_var = tk.StringVar(value="At time (0m)")
        combo_lead = ttk.Combobox(
            meta_grid, textvariable=self.rdv_lead_var,
            values=["At time (0m)", "5m before", "10m before", "15m before"],
            width=12, state="readonly"
        )
        combo_lead.grid(row=1, column=1, sticky="w", padx=4, pady=2)

        tk.Label(meta_grid, text="Repeat:", font=(FONT_FAMILY, 8),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).grid(row=2, column=0, sticky="w", pady=2)
        self.rdv_repeat_var = tk.StringVar(value="None")
        combo_rep = ttk.Combobox(
            meta_grid, textvariable=self.rdv_repeat_var,
            values=["None", "Daily", "Weekly", "Monthly"],
            width=12, state="readonly"
        )
        combo_rep.grid(row=2, column=1, sticky="w", padx=4, pady=2)

        # Action Buttons
        action_row = tk.Frame(details_box, bg=COLORS["bg_dark"])
        action_row.pack(fill="x", pady=(6, 2))

        tk.Button(action_row, text="Add Event 📅", bg=COLORS["accent"], fg="white",
                  font=(FONT_FAMILY, 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                  command=self._add_rendez_vous).pack(side="right")

        tk.Button(action_row, text="Export .ics", bg=COLORS["surface_light"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 8), relief="flat", cursor="hand2", padx=6, pady=3,
                  command=self._export_calendar).pack(side="left", padx=(0, 4))

        tk.Button(action_row, text="Import .ics", bg=COLORS["surface_light"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 8), relief="flat", cursor="hand2", padx=6, pady=3,
                  command=self._import_calendar).pack(side="left")

    def _on_calendar_date_selected(self, d_val: datetime.date):
        events = self.scheduler.get_events_for_date(d_val)
        if events:
            event_titles = ", ".join(f"'{ev.name}'" for ev in events[:2])
            more = f" (+{len(events)-2} more)" if len(events) > 2 else ""
            self.lbl_day_agenda.config(
                text=f"{d_val.strftime('%b %d')}: {event_titles}{more}",
                fg=COLORS["accent"]
            )
        else:
            self.lbl_day_agenda.config(
                text=f"{d_val.strftime('%b %d')}: No scheduled events",
                fg=COLORS["text_muted"]
            )

    def _init_settings_tab(self, parent):
        s_box = tk.LabelFrame(parent, text=" Sound, Volume & System Preferences ", font=(FONT_FAMILY, 9),
                              bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=10, pady=6)
        s_box.pack(fill="x", pady=4)

        # Sound Presets Dropdown
        tk.Label(s_box, text="Alarm Sound Pattern:", bg=COLORS["bg_dark"], fg=COLORS["text"]).pack(anchor="w")
        self.sound_choice_var = tk.StringVar(value=self.settings.get("sound_type", "gentle"))
        preset_options = list(SOUND_PRESETS.keys())
        self.combo_sound = ttk.Combobox(s_box, textvariable=self.sound_choice_var, values=preset_options,
                                        width=15, state="readonly")
        self.combo_sound.pack(anchor="w", pady=(2, 4))

        # Volume Slider
        vol_frame = tk.Frame(s_box, bg=COLORS["bg_dark"])
        vol_frame.pack(fill="x", pady=3)
        self.lbl_volume = tk.Label(
            vol_frame, text=f"Master Alarm Volume: {self.settings.get('volume', 85)}%",
            bg=COLORS["bg_dark"], fg=COLORS["text"]
        )
        self.lbl_volume.pack(anchor="w")

        self.scale_volume = tk.Scale(
            vol_frame, from_=0, to=100, orient="horizontal",
            bg=COLORS["surface"], fg=COLORS["text"], troughcolor=COLORS["surface_light"],
            highlightthickness=0, relief="flat",
            command=self._on_volume_change
        )
        self.scale_volume.set(self.settings.get("volume", 85))
        self.scale_volume.pack(fill="x", pady=(2, 4))

        # Preview Button
        preview_row = tk.Frame(s_box, bg=COLORS["bg_dark"])
        preview_row.pack(fill="x", pady=2)
        self.btn_preview = tk.Button(
            preview_row, text="🔊 Play Sound Preview", bg=COLORS["surface_light"], fg=COLORS["text"],
            relief="flat", cursor="hand2", padx=10, pady=3, command=self._toggle_preview
        )
        self.btn_preview.pack(side="left")
        self.is_previewing = False

        # Custom Audio File
        file_row = tk.Frame(s_box, bg=COLORS["bg_dark"])
        file_row.pack(fill="x", pady=4)
        tk.Label(file_row, text="Custom File (if selected):", bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(anchor="w")
        self.lbl_sound_path = tk.Label(file_row, text=self.settings.get("custom_sound_path") or "No file chosen",
                                       bg=COLORS["surface"], fg=COLORS["text_muted"], anchor="w", padx=6, pady=3)
        self.lbl_sound_path.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(file_row, text="Browse...", bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
                  command=self._browse_audio).pack(side="right")

        # Gradual Escalation, Startup, Snooze
        opt_frame = tk.Frame(s_box, bg=COLORS["bg_dark"])
        opt_frame.pack(fill="x", pady=3)

        self.escalate_var = tk.BooleanVar(value=self.settings.get("gradual_escalation", True))
        tk.Checkbutton(opt_frame, text="Gradual volume & tempo escalation", variable=self.escalate_var,
                       bg=COLORS["bg_dark"], fg=COLORS["text"], selectcolor=COLORS["surface"],
                       activebackground=COLORS["bg_dark"]).pack(anchor="w")

        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        tk.Checkbutton(opt_frame, text="Launch at Windows startup (minimized)", variable=self.startup_var,
                       bg=COLORS["bg_dark"], fg=COLORS["text"], selectcolor=COLORS["surface"],
                       activebackground=COLORS["bg_dark"]).pack(anchor="w")

        snooze_row = tk.Frame(opt_frame, bg=COLORS["bg_dark"])
        snooze_row.pack(fill="x", pady=3)
        tk.Label(snooze_row, text="Default Snooze:", bg=COLORS["bg_dark"], fg=COLORS["text"]).pack(side="left")
        self.combo_snooze = ttk.Combobox(snooze_row, values=[5, 15], width=4, state="readonly")
        self.combo_snooze.set(self.settings.get("default_snooze_minutes", 5))
        self.combo_snooze.pack(side="left", padx=6)
        tk.Label(snooze_row, text="minutes", bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left")

        tk.Button(s_box, text="Save Settings", bg=COLORS["accent_success"], fg="white", font=(FONT_FAMILY, 9, "bold"),
                  relief="flat", cursor="hand2", padx=12, pady=4, command=self._save_settings).pack(anchor="e", pady=4)

    def _init_activity_tab(self, parent):
        """Activity tab: live view of All Timers and All Rendez-vous with detail panel."""
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        # ── Timers column ──────────────────────────────────────────────────────
        timer_box = tk.LabelFrame(
            parent, text=" ⏳ All Timers ", font=(FONT_FAMILY, 9, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=6, pady=4
        )
        timer_box.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(4, 2), pady=4)

        # Counter badge
        self.lbl_timer_count = tk.Label(
            timer_box, text="0 active", font=(FONT_FAMILY, 8),
            bg=COLORS["surface_light"], fg=COLORS["accent"], padx=6, pady=1
        )
        self.lbl_timer_count.pack(anchor="e", pady=(0, 4))

        # Listbox + scrollbar
        t_list_frame = tk.Frame(timer_box, bg=COLORS["bg_dark"])
        t_list_frame.pack(fill="both", expand=True)

        t_scrollbar = tk.Scrollbar(t_list_frame, orient="vertical", bg=COLORS["surface"])
        t_scrollbar.pack(side="right", fill="y")

        self.activity_timer_lb = tk.Listbox(
            t_list_frame, bg=COLORS["surface"], fg=COLORS["text"],
            selectbackground=COLORS["accent"], borderwidth=0,
            font=(FONT_FAMILY, 8), yscrollcommand=t_scrollbar.set,
            activestyle="none", cursor="hand2"
        )
        self.activity_timer_lb.pack(fill="both", expand=True)
        t_scrollbar.config(command=self.activity_timer_lb.yview)
        self.activity_timer_lb.bind("<<ListboxSelect>>", self._on_activity_timer_select)

        # Detail card for selected timer
        self.timer_detail = tk.Label(
            timer_box, text="Select a timer to see details.",
            font=(FONT_FAMILY, 8), bg=COLORS["surface"], fg=COLORS["text_muted"],
            anchor="w", justify="left", padx=6, pady=4, wraplength=240
        )
        self.timer_detail.pack(fill="x", pady=(4, 2))

        # Action buttons row
        t_btn_row = tk.Frame(timer_box, bg=COLORS["bg_dark"])
        t_btn_row.pack(fill="x", pady=(2, 0))

        tk.Button(
            t_btn_row, text="⏯️ Pause/Resume", font=(FONT_FAMILY, 7, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", padx=6, pady=2,
            command=self._activity_pause_timer
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            t_btn_row, text="🗑️ Delete", font=(FONT_FAMILY, 7),
            bg=COLORS["surface_light"], fg=COLORS["accent_danger"], relief="flat",
            cursor="hand2", padx=6, pady=2,
            command=self._activity_delete_timer
        ).pack(side="left")

        # ── Rendez-vous column ────────────────────────────────────────────────
        rdv_box = tk.LabelFrame(
            parent, text=" 📅 All Rendez-vous ", font=(FONT_FAMILY, 9, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["accent"], padx=6, pady=4
        )
        rdv_box.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(2, 4), pady=4)

        # Counter badge
        self.lbl_rdv_count = tk.Label(
            rdv_box, text="0 scheduled", font=(FONT_FAMILY, 8),
            bg=COLORS["surface_light"], fg=COLORS["accent"], padx=6, pady=1
        )
        self.lbl_rdv_count.pack(anchor="e", pady=(0, 4))

        # Listbox + scrollbar
        r_list_frame = tk.Frame(rdv_box, bg=COLORS["bg_dark"])
        r_list_frame.pack(fill="both", expand=True)

        r_scrollbar = tk.Scrollbar(r_list_frame, orient="vertical", bg=COLORS["surface"])
        r_scrollbar.pack(side="right", fill="y")

        self.activity_rdv_lb = tk.Listbox(
            r_list_frame, bg=COLORS["surface"], fg=COLORS["text"],
            selectbackground=COLORS["accent"], borderwidth=0,
            font=(FONT_FAMILY, 8), yscrollcommand=r_scrollbar.set,
            activestyle="none", cursor="hand2"
        )
        self.activity_rdv_lb.pack(fill="both", expand=True)
        r_scrollbar.config(command=self.activity_rdv_lb.yview)
        self.activity_rdv_lb.bind("<<ListboxSelect>>", self._on_activity_rdv_select)

        # Detail card for selected rendez-vous
        self.rdv_detail = tk.Label(
            rdv_box, text="Select an event to see details.",
            font=(FONT_FAMILY, 8), bg=COLORS["surface"], fg=COLORS["text_muted"],
            anchor="w", justify="left", padx=6, pady=4, wraplength=240
        )
        self.rdv_detail.pack(fill="x", pady=(4, 2))

        # Action button
        r_btn_row = tk.Frame(rdv_box, bg=COLORS["bg_dark"])
        r_btn_row.pack(fill="x", pady=(2, 0))

        tk.Button(
            r_btn_row, text="🗑️ Delete", font=(FONT_FAMILY, 7),
            bg=COLORS["surface_light"], fg=COLORS["accent_danger"], relief="flat",
            cursor="hand2", padx=6, pady=2,
            command=self._activity_delete_rdv
        ).pack(side="left")

        # Internal caches used by action callbacks (filled by _refresh_loop)
        self._activity_timer_items: list = []
        self._activity_rdv_items: list = []

    # ── Activity Tab helpers ──────────────────────────────────────────────────

    def _fmt_remain(self, item, now: float) -> str:
        """Return 'HH:MM:SS remaining' or 'PAUSED HH:MM:SS' string."""
        if item.is_paused:
            rem = int(item.remaining_paused)
            prefix = "⏸️ PAUSED — "
        else:
            rem = max(0, int(item.target_time - now))
            prefix = ""
        m, s = divmod(rem, 60)
        h, m = divmod(m, 60)
        return f"{prefix}{h:02d}:{m:02d}:{s:02d}"

    def _fmt_target(self, item) -> str:
        """Return a human-readable scheduled time."""
        dt = datetime.datetime.fromtimestamp(item.target_time)
        return dt.strftime("%b %d  %H:%M:%S")

    def _on_activity_timer_select(self, _event=None):
        sel = self.activity_timer_lb.curselection()
        if not sel or sel[0] >= len(self._activity_timer_items):
            return
        it = self._activity_timer_items[sel[0]]
        now = __import__("time").time()
        cat = it.category if it.category and it.category != "General" else "—"
        rep = "Yes" if it.repeat_sec > 0 else "No"
        lines = [
            f"📌 {it.name}",
            f"⏱ Remaining: {self._fmt_remain(it, now)}",
            f"🔔 Fires at:  {self._fmt_target(it)}",
            f"🔁 Repeat:    {rep}",
            f"🏷 Category:  {cat}",
        ]
        self.timer_detail.config(text="\n".join(lines), fg=COLORS["text"])

    def _on_activity_rdv_select(self, _event=None):
        sel = self.activity_rdv_lb.curselection()
        if not sel or sel[0] >= len(self._activity_rdv_items):
            return
        it = self._activity_rdv_items[sel[0]]
        now = __import__("time").time()
        cat = it.category if it.category and it.category != "General" else "—"
        rep = it.repeat_rule.capitalize() if it.repeat_rule and it.repeat_rule != "none" else "None"
        lead = f"{it.lead_time_min}m before" if it.lead_time_min else "At event time"
        lines = [
            f"📌 {it.name}",
            f"⏱ Remaining: {self._fmt_remain(it, now)}",
            f"📅 Date/Time: {self._fmt_target(it)}",
            f"🔁 Repeat:    {rep}",
            f"🏷 Category:  {cat}",
            f"⏰ Alert:     {lead}",
        ]
        self.rdv_detail.config(text="\n".join(lines), fg=COLORS["text"])

    def _activity_pause_timer(self):
        sel = self.activity_timer_lb.curselection()
        if sel and sel[0] < len(self._activity_timer_items):
            it = self._activity_timer_items[sel[0]]
            self.scheduler.toggle_pause(it.id)

    def _activity_delete_timer(self):
        sel = self.activity_timer_lb.curselection()
        if sel and sel[0] < len(self._activity_timer_items):
            it = self._activity_timer_items[sel[0]]
            self.scheduler.remove_item(it.id)
            self.timer_detail.config(text="Select a timer to see details.", fg=COLORS["text_muted"])

    def _activity_delete_rdv(self):
        sel = self.activity_rdv_lb.curselection()
        if sel and sel[0] < len(self._activity_rdv_items):
            it = self._activity_rdv_items[sel[0]]
            self.scheduler.remove_item(it.id)
            self.rdv_detail.config(text="Select an event to see details.", fg=COLORS["text_muted"])

    def _on_volume_change(self, val):
        self.lbl_volume.config(text=f"Master Alarm Volume: {val}%")

    def _toggle_preview(self):
        if self.is_previewing:
            self.sound_player.stop_preview()
            self.btn_preview.config(text="🔊 Play Sound Preview", bg=COLORS["surface_light"])
            self.is_previewing = False
        else:
            snd_type = self.sound_choice_var.get()
            custom_p = self.lbl_sound_path.cget("text")
            vol = int(self.scale_volume.get())
            self.sound_player.start_preview(snd_type, custom_p, volume=vol)
            self.btn_preview.config(text="⏹️ Stop Preview", bg=COLORS["accent_danger"])
            self.is_previewing = True
            self.after(3500, self._reset_preview_btn)

    def _reset_preview_btn(self):
        self.btn_preview.config(text="🔊 Play Sound Preview", bg=COLORS["surface_light"])
        self.is_previewing = False

    def _browse_audio(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav"), ("All Files", "*.*")])
        if path:
            self.lbl_sound_path.config(text=path)
            self.sound_choice_var.set("custom")

    def _save_settings(self):
        self.settings["sound_type"] = self.sound_choice_var.get()
        self.settings["custom_sound_path"] = self.lbl_sound_path.cget("text")
        self.settings["volume"] = int(self.scale_volume.get())
        self.settings["default_snooze_minutes"] = int(self.combo_snooze.get())
        self.settings["gradual_escalation"] = self.escalate_var.get()
        Storage.save_settings(self.settings)

        # Apply Windows startup registry change
        set_startup_enabled(self.startup_var.get())
        messagebox.showinfo("Saved", "Preferences saved successfully!")

    def _toggle_active_timer_pause(self):
        active = self.scheduler.get_active_timer()
        if active:
            now_paused = self.scheduler.toggle_pause(active.id)
            btn_text = "▶️ Resume" if now_paused else "⏯️ Pause"
            self.btn_ring_play_pause.config(text=btn_text)
        else:
            # If no timer, toggle pause on nearest item if any
            nearest = self.scheduler.get_nearest_item()
            if nearest:
                self.scheduler.toggle_pause(nearest.id)

    def _stop_active_timer(self):
        active = self.scheduler.get_active_timer()
        if active:
            self.scheduler.remove_item(active.id)
            self.btn_ring_play_pause.config(text="⏯️ Pause")

    def _export_calendar(self):
        rdv_items = [it.to_dict() for it in self.scheduler.items if it.kind == "rendez-vous"]
        if not rdv_items:
            messagebox.showinfo("Export", "No rendez-vous events to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".ics", filetypes=[("iCalendar Files", "*.ics")])
        if path:
            success = CalendarManager.export_to_ics(rdv_items, path)
            if success:
                messagebox.showinfo("Success", f"Exported {len(rdv_items)} events to {os.path.basename(path)}.")

    def _import_calendar(self):
        path = filedialog.askopenfilename(filetypes=[("iCalendar Files", "*.ics")])
        if path:
            events = CalendarManager.import_from_ics(path)
            added = 0
            now = time.time()
            for ev in events:
                if ev["target_time"] > now:
                    delta = ev["target_time"] - now
                    self.scheduler.add_item(
                        kind="rendez-vous",
                        name=ev["name"],
                        seconds_from_now=delta,
                        repeat_rule=ev.get("repeat_rule", "none")
                    )
                    added += 1
            messagebox.showinfo("Imported", f"Successfully imported {added} upcoming event(s).")

    def _build_active_list(self):
        container = tk.Frame(self, bg=COLORS["bg_dark"], padx=16)
        container.pack(fill="both", expand=True, pady=(2, 10))

        header_row = tk.Frame(container, bg=COLORS["bg_dark"])
        header_row.pack(fill="x", pady=(0, 2))
        tk.Label(header_row, text="Active Reminders", font=(FONT_FAMILY, 9, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left")

        tk.Button(header_row, text="Delete Selected", font=(FONT_FAMILY, 8),
                  bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
                  command=self._delete_selected).pack(side="right")

        tk.Button(header_row, text="Pause / Resume Selected", font=(FONT_FAMILY, 8),
                  bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
                  command=self._toggle_selected_pause).pack(side="right", padx=(0, 6))

        self.listbox = tk.Listbox(container, bg=COLORS["surface"], fg=COLORS["text"],
                                  selectbackground=COLORS["accent"], borderwidth=0, font=(FONT_FAMILY, 9))
        self.listbox.pack(fill="both", expand=True)

        self._refresh_loop()

    def _toggle_selected_pause(self):
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self.scheduler.items):
            item = self.scheduler.items[sel[0]]
            self.scheduler.toggle_pause(item.id)

    def _delete_selected(self):
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self.scheduler.items):
            item_to_remove = self.scheduler.items[sel[0]]
            self.scheduler.remove_item(item_to_remove.id)

    def _start_custom_timer(self):
        name = self.entry_timer_name.get().strip() or "Custom Timer"
        try:
            h = int(self.spin_h.get() or 0)
            m = int(self.spin_m.get() or 0)
            s = int(self.spin_s.get() or 0)
            total_sec = h * 3600 + m * 60 + s
            if total_sec <= 0:
                messagebox.showwarning("Invalid", "Duration must be > 0.")
                return
            repeat = total_sec if self.repeat_var.get() else 0
            self.scheduler.add_item("timer", name, total_sec, repeat_sec=repeat, original_duration=total_sec)
        except ValueError:
            messagebox.showerror("Error", "Hours, minutes, seconds must be numbers.")

    def _add_rendez_vous(self):
        name = self.entry_rdv_name.get().strip() or "Meeting"
        d_val = self.mini_calendar.selected_date
        h, m = self.time_picker.get_time()
        rule = self.rdv_repeat_var.get().lower()
        cat = self.rdv_category_var.get()

        # Parse lead time (e.g. "10m before" -> 10)
        lead_str = self.rdv_lead_var.get()
        lead_time = 0
        if "5m" in lead_str:
            lead_time = 5
        elif "10m" in lead_str:
            lead_time = 10
        elif "15m" in lead_str:
            lead_time = 15

        dt = datetime.datetime.combine(d_val, datetime.time(h, m))
        delta = (dt - datetime.datetime.now()).total_seconds()
        if delta <= 0:
            messagebox.showwarning("Past Date", "Please choose a future date and time.")
            return

        self.scheduler.add_item(
            kind="rendez-vous",
            name=name,
            seconds_from_now=delta,
            repeat_rule=rule,
            category=cat,
            lead_time_min=lead_time
        )
        self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
        self._on_calendar_date_selected(d_val)
        messagebox.showinfo("Scheduled", f"Rendez-vous '{name}' ({cat}) set for {dt.strftime('%b %d at %H:%M')}.")

    def _refresh_loop(self):
        """Update listbox, circular ring, and system tray tooltip every second."""
        cur_selection = self.listbox.curselection()
        self.listbox.delete(0, tk.END)
        now = time.time()

        nearest_item = None
        nearest_delta = 99999999
        active_timer = None

        for it in self.scheduler.items:
            if it.is_paused:
                remain = it.remaining_paused
                status_prefix = "⏸️ [PAUSED] "
            else:
                remain = max(0.0, it.target_time - now)
                status_prefix = ""
                if remain < nearest_delta:
                    nearest_delta = remain
                    nearest_item = it

            if it.kind == "timer" and active_timer is None:
                active_timer = it

            m, s = divmod(int(remain), 60)
            h, m = divmod(m, 60)
            cat_icon = f"[{it.category.split()[0]}] " if hasattr(it, "category") and it.category and it.category != "General" else ""
            icon = "⏳" if it.kind == "timer" else "📅"
            rep = " 🔁" if (it.repeat_sec > 0 or it.repeat_rule != "none") else ""
            self.listbox.insert(tk.END, f"{icon} {status_prefix}{cat_icon}{it.name}{rep} — Remaining: {h:02d}:{m:02d}:{s:02d}")

        if cur_selection and cur_selection[0] < self.listbox.size():
            self.listbox.selection_set(cur_selection[0])

        # Update Radial Circular Progress Ring
        if active_timer:
            rem = active_timer.remaining_paused if active_timer.is_paused else max(0.0, active_timer.target_time - now)
            tot = max(1.0, active_timer.original_duration)
            self.ring.update_countdown(
                remaining_sec=rem,
                total_sec=tot,
                title=active_timer.name,
                is_repeating=active_timer.repeat_sec > 0,
                is_paused=active_timer.is_paused
            )
            # Update Ring Pause button text
            btn_txt = "▶️ Resume" if active_timer.is_paused else "⏯️ Pause"
            self.btn_ring_play_pause.config(text=btn_txt)
        elif nearest_item:
            rem = nearest_item.remaining_paused if nearest_item.is_paused else max(0.0, nearest_item.target_time - now)
            tot = max(1.0, nearest_item.original_duration or rem)
            self.ring.update_countdown(
                remaining_sec=rem,
                total_sec=tot,
                title=nearest_item.name,
                is_repeating=nearest_item.repeat_rule != "none",
                is_paused=nearest_item.is_paused
            )
            self.btn_ring_play_pause.config(text="⏯️ Pause")
        else:
            self.ring.set_idle()
            self.btn_ring_play_pause.config(text="⏯️ Pause")

        # Update Tray Tooltip
        if nearest_item:
            rem_int = int(nearest_delta)
            m, s = divmod(rem_int, 60)
            h, m = divmod(m, 60)
            tooltip = f"Next: {nearest_item.name} ({h:02d}:{m:02d}:{s:02d})"
        else:
            tooltip = "Timer & Rendez-vous: All quiet"

        if hasattr(self, "tray") and self.tray:
            self.tray.update_tooltip(tooltip)

        # Update Activity Tab (only if it has been built)
        if hasattr(self, "activity_timer_lb"):
            self._refresh_activity_tab(now)

        self.after(1000, self._refresh_loop)

    def _refresh_activity_tab(self, now: float):
        """Refresh the Activity tab's Timer and Rendez-vous listboxes."""
        timers = [it for it in self.scheduler.items if it.kind == "timer"]
        rdvs   = [it for it in self.scheduler.items if it.kind == "rendez-vous"]

        # ── Timers list ──────────────────────────────────────────────────────
        t_sel = self.activity_timer_lb.curselection()
        self.activity_timer_lb.delete(0, tk.END)
        self._activity_timer_items = timers

        for it in timers:
            rem = int(it.remaining_paused if it.is_paused else max(0.0, it.target_time - now))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            paused_badge = " ⏸️" if it.is_paused else ""
            rep_badge    = " 🔁" if it.repeat_sec > 0 else ""
            self.activity_timer_lb.insert(
                tk.END,
                f"⏳{paused_badge}{rep_badge} {it.name} — {h:02d}:{m:02d}:{s:02d}"
            )

        # Restore selection
        if t_sel and t_sel[0] < self.activity_timer_lb.size():
            self.activity_timer_lb.selection_set(t_sel[0])
            self._on_activity_timer_select()

        t_count = len(timers)
        self.lbl_timer_count.config(
            text=f"{t_count} active" if t_count else "None active",
            fg=COLORS["accent"] if t_count else COLORS["text_muted"]
        )

        # ── Rendez-vous list ─────────────────────────────────────────────────
        r_sel = self.activity_rdv_lb.curselection()
        self.activity_rdv_lb.delete(0, tk.END)
        self._activity_rdv_items = rdvs

        for it in rdvs:
            rem = int(it.remaining_paused if it.is_paused else max(0.0, it.target_time - now))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            cat_icon = it.category.split()[0] if it.category and it.category != "General" else "📌"
            rep_badge = " 🔁" if it.repeat_rule and it.repeat_rule != "none" else ""
            self.activity_rdv_lb.insert(
                tk.END,
                f"{cat_icon}{rep_badge} {it.name} — {h:02d}:{m:02d}:{s:02d}"
            )

        # Restore selection
        if r_sel and r_sel[0] < self.activity_rdv_lb.size():
            self.activity_rdv_lb.selection_set(r_sel[0])
            self._on_activity_rdv_select()

        r_count = len(rdvs)
        self.lbl_rdv_count.config(
            text=f"{r_count} scheduled" if r_count else "None scheduled",
            fg=COLORS["accent"] if r_count else COLORS["text_muted"]
        )

    def _check_missed_alarms(self):
        if self.scheduler.missed_items:
            names = ", ".join(f"'{it.name}'" for it in self.scheduler.missed_items[:3])
            more = f" and {len(self.scheduler.missed_items)-3} more" if len(self.scheduler.missed_items) > 3 else ""
            show_toast("⚠️ Missed Reminders", f"While closed: {names}{more}")
            messagebox.showwarning(
                "Missed Reminders",
                f"You missed reminder(s) while the app was closed:\n{names}{more}"
            )
            self.scheduler.missed_items.clear()

    def _on_wake_missed(self, items: list):
        """Called when system wakes from sleep and alarms passed during sleep."""
        self.after(0, lambda: self._handle_wake_missed_ui(items))

    def _handle_wake_missed_ui(self, items: list):
        names = ", ".join(f"'{it.name}'" for it in items[:3])
        show_toast("⚠️ PC Woke Up - Missed Alarms", f"Due while sleeping: {names}")
        messagebox.showwarning(
            "Missed Alarms While Asleep",
            f"The following alarms passed while your PC was in sleep/hibernation:\n{names}"
        )

    def _on_item_triggered(self, item: ScheduledItem):
        self.after(0, lambda: self._popup_alarm(item))

    def _popup_alarm(self, item: ScheduledItem):
        self.sound_player.start_alarm()
        self.deiconify()
        self.lift()

        def dismiss():
            self.sound_player.stop_alarm()

        def snooze(minutes: int):
            self.sound_player.stop_alarm()
            self.scheduler.add_item(
                kind=item.kind,
                name=f"[Snooze] {item.name}",
                seconds_from_now=minutes * 60,
                original_duration=minutes * 60
            )

        AlarmDialog(
            master=self,
            title_text=f"Time for: {item.name}",
            reminder_name=f"{'Timer finished' if item.kind == 'timer' else 'Rendez-vous appointment'}",
            on_dismiss=dismiss,
            on_snooze=snooze,
            category=getattr(item, "category", "")
        )

    def hide_to_tray(self):
        self.withdraw()

    def toggle_visibility(self):
        if self.state() == "normal":
            self.withdraw()
        else:
            self.deiconify()
            self.lift()

    def quit_app(self):
        self.tray.stop()
        self.destroy()
        sys.exit(0)

    def _setup_hotkey(self):
        try:
            import keyboard
            keyboard.add_hotkey(HOTKEY, self.toggle_visibility)
        except Exception:
            self.bind_all("<Control-F7>", lambda e: self.toggle_visibility())
