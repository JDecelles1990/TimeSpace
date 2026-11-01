"""PySide6 UI for Timer & Rendez-vous Module (F7Hub Modular Widget & Standalone Window)."""
import sys
import os
import time
import datetime
from typing import Optional, List

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QShortcut, QKeySequence, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QTabWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSlider,
    QFileDialog,
    QMessageBox,
    QFrame,
)

from src.config import (
    APP_TITLE,
    COLORS,
    DARK_QSS,
    HOTKEY,
    UI_DIMENSIONS,
    SOUND_PRESETS,
    CATEGORIES,
    QUICK_TIMER_PRESETS,
    SNOOZE_OPTIONS,
    AppConfig,
    HistoryEntry,
    ScratchpadState,
)
from src.sound import SoundPlayer
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
from src.mini_hud import FloatingMiniHUD
from src.hotkey_manager import GlobalHotkeyListener
from src.notifications import open_attachment_link, normalize_link_target


class SchedulerBridge(QObject):
    """Thread-safe Qt signal bridge marshaling background thread callbacks to the PySide6 GUI thread."""
    itemTriggered = Signal(object)
    wakeMissed = Signal(object)
    toggleVisibilityRequested = Signal()
    togglePauseRequested = Signal()
    toggleHudRequested = Signal()
    quitRequested = Signal()


class TimerRendezVousWidget(QWidget):
    """Self-contained PySide6 module widget for F7Hub or standalone window embedding."""

    hudToggleRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(DARK_QSS)

        # Unified typed state models
        self.app_config: AppConfig = Storage.load_config()
        self.scratchpad_state: ScratchpadState = Storage.load_scratchpad()

        # Debounce QTimer for auto-saving scratchpad notes
        self._scratchpad_save_timer = QTimer(self)
        self._scratchpad_save_timer.setSingleShot(True)
        self._scratchpad_save_timer.setInterval(500)
        self._scratchpad_save_timer.timeout.connect(self._save_scratchpad_now)

        # Thread-safe Qt Signal Bridge
        self.bridge = SchedulerBridge(self)
        self.bridge.itemTriggered.connect(self._popup_alarm)
        self.bridge.wakeMissed.connect(self._handle_wake_missed_ui)
        self.bridge.togglePauseRequested.connect(self._toggle_active_timer_pause)
        self.bridge.toggleHudRequested.connect(self._toggle_hud)

        # Backend services
        self.sound_player = SoundPlayer(config=self.app_config)
        self.scheduler = ReminderScheduler(
            on_trigger_callback=lambda item: self.bridge.itemTriggered.emit(item),
            on_wake_missed_callback=lambda items: self.bridge.wakeMissed.emit(items),
        )

        # Mini HUD state
        self.hud: Optional[FloatingMiniHUD] = None
        self.hud_enabled: bool = self.app_config.hud_enabled
        self.is_previewing: bool = False

        # Internal caches for Activity & History tabs
        self._activity_timer_items: List[ScheduledItem] = []
        self._activity_rdv_items: List[ScheduledItem] = []
        self._history_items: List[dict] = []

        # Build UI layout
        self._build_ui()

        # 1-second non-blocking QTimer refresh loop
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self._refresh_loop)
        self.refresh_timer.start()
        self._refresh_loop()

        # Check missed alarms shortly after startup
        QTimer.singleShot(500, self._check_missed_alarms)
        if self.hud_enabled:
            QTimer.singleShot(300, self._show_hud)

    # ── Main Layout Assembly ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(6)

        self._build_header(root_layout)
        self._build_hero_deck(root_layout)
        self._build_tabs(root_layout)
        self._build_active_queue(root_layout)

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }}"
        )
        header_row = QHBoxLayout(header_frame)
        header_row.setContentsMargins(12, 5, 12, 5)

        lbl_title = QLabel(f"⏰ {APP_TITLE}")
        lbl_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']}; border: none;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        hud_text = "📌 HUD: ON" if self.hud_enabled else "📌 HUD: OFF"
        self.btn_hud_toggle = QPushButton(hud_text)
        self.btn_hud_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hud_toggle.setFixedHeight(23)
        self.btn_hud_toggle.clicked.connect(self._toggle_hud)
        header_row.addWidget(self.btn_hud_toggle)

        lbl_hotkey = QLabel(f"Hotkey: {HOTKEY.upper()}")
        lbl_hotkey.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['accent']}; "
            f"font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px; border: none;"
        )
        header_row.addWidget(lbl_hotkey)

        parent_layout.addWidget(header_frame)

    def _build_hero_deck(self, parent_layout: QVBoxLayout) -> None:
        """Clean side-by-side top deck: Left = Radial Ring + Controls; Right = Quick Natural Input."""
        deck_frame = QFrame()
        deck_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }}"
        )
        deck_layout = QHBoxLayout(deck_frame)
        deck_layout.setContentsMargins(10, 6, 10, 6)
        deck_layout.setSpacing(14)

        # Left column: Radial Progress Ring + Pause/Stop
        ring_col = QVBoxLayout()
        ring_col.setSpacing(3)
        self.ring = CircularProgressRing(
            self,
            size=UI_DIMENSIONS["ring_size"],
            ring_width=UI_DIMENSIONS["ring_width"],
        )
        ring_col.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        ring_ctrl = QHBoxLayout()
        ring_ctrl.setSpacing(4)
        self.btn_ring_play_pause = QPushButton("⏯ Pause")
        self.btn_ring_play_pause.setFixedHeight(22)
        self.btn_ring_play_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ring_play_pause.clicked.connect(self._toggle_active_timer_pause)

        self.btn_ring_reset = QPushButton("⏹ Stop")
        self.btn_ring_reset.setObjectName("dangerBtn")
        self.btn_ring_reset.setFixedHeight(22)
        self.btn_ring_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ring_reset.clicked.connect(self._stop_active_timer)

        ring_ctrl.addWidget(self.btn_ring_play_pause)
        ring_ctrl.addWidget(self.btn_ring_reset)
        ring_col.addLayout(ring_ctrl)
        deck_layout.addLayout(ring_col)

        # Right column: Smart Natural Schedule (no duplicate preset clutter)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.addStretch()

        lbl_smart = QLabel("⚡ Quick Natural Schedule")
        lbl_smart.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px; border: none;")
        right_col.addWidget(lbl_smart)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.smart_entry = QLineEdit("Ring in 15 min")
        self.smart_entry.setPlaceholderText('e.g., "Ring in 15m", "Call Sam in 2 days", "RDV at 4PM"')
        self.smart_entry.returnPressed.connect(self._on_smart_input_submit)
        input_row.addWidget(self.smart_entry, 1)

        btn_create = QPushButton("Create ⚡")
        btn_create.setObjectName("primaryBtn")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._on_smart_input_submit)
        input_row.addWidget(btn_create)
        right_col.addLayout(input_row)

        self.smart_feedback = QLabel('Try: "Ring in 15m" · "Check backups in 45m" · "Call Sam tomorrow at 2pm"')
        self.smart_feedback.setWordWrap(True)
        self.smart_feedback.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")
        right_col.addWidget(self.smart_feedback)

        right_col.addStretch()
        deck_layout.addLayout(right_col, 1)

        parent_layout.addWidget(deck_frame)

    # ── 6-Tab Section (1=Timers, 2=RDV, 3=Activity, 4=Scratchpad, 5=History, 6=Settings) ─

    def _build_tabs(self, parent_layout: QVBoxLayout) -> None:
        self.tabs = QTabWidget()

        tab_timers = QWidget()
        self._init_timer_tab(tab_timers)
        self.tabs.addTab(tab_timers, "1. Timers ⏳")

        tab_rdv = QWidget()
        self._init_rdv_tab(tab_rdv)
        self.tabs.addTab(tab_rdv, "2. RDV 📅")

        tab_activity = QWidget()
        self._init_activity_tab(tab_activity)
        self.tabs.addTab(tab_activity, "3. Activity 📋")

        tab_scratchpad = QWidget()
        self._init_scratchpad_tab(tab_scratchpad)
        self.tabs.addTab(tab_scratchpad, "4. Scratchpad 📝")

        tab_history = QWidget()
        self._init_history_tab(tab_history)
        self.tabs.addTab(tab_history, "5. History 📜")

        tab_settings = QWidget()
        self._init_settings_tab(tab_settings)
        self.tabs.addTab(tab_settings, "6. Settings ⚙️")

        parent_layout.addWidget(self.tabs, 2)

    # ── Tab 1: Professional Timer ────────────────────────────────────────────

    def _init_timer_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Clean Quick Presets Row (15m, 30m, 1h, 2h)
        preset_group = QGroupBox("⚡ Quick Start Presets")
        preset_row = QHBoxLayout(preset_group)
        preset_row.setSpacing(8)
        for label, mins in QUICK_TIMER_PRESETS:
            btn = QPushButton(label)
            btn.setMinimumHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, m=mins, l=label: self._start_preset_timer(l, m * 60))
            preset_row.addWidget(btn, 1)
        layout.addWidget(preset_group)

        # Intuitive Professional Timer Form (Description + Client/Ticket Ref + Link/Note + Duration)
        custom_group = QGroupBox("⏱️ Daily Task & Reminder Timer")
        grid = QGridLayout(custom_group)
        grid.setVerticalSpacing(6)
        grid.setHorizontalSpacing(8)

        grid.addWidget(QLabel("What to do:"), 0, 0)
        self.entry_timer_name = QLineEdit()
        self.entry_timer_name.setPlaceholderText("Reminder description (e.g., Check server backup, Call back, Review PR)")
        self.entry_timer_name.returnPressed.connect(self._start_custom_timer)
        grid.addWidget(self.entry_timer_name, 0, 1, 1, 3)

        grid.addWidget(QLabel("Client / Ticket #:"), 1, 0)
        self.entry_timer_ref = QLineEdit()
        self.entry_timer_ref.setPlaceholderText("Optional — Client name or Ticket ID (e.g., Acme Corp / #4821)")
        self.entry_timer_ref.returnPressed.connect(self._start_custom_timer)
        grid.addWidget(self.entry_timer_ref, 1, 1, 1, 3)

        grid.addWidget(QLabel("Link / Note:"), 2, 0)
        attach_row = QHBoxLayout()
        attach_row.setSpacing(6)
        self.entry_timer_url = QLineEdit()
        self.entry_timer_url.setPlaceholderText("🔗 Optional Link / URL / File path")
        self.entry_timer_url.returnPressed.connect(self._start_custom_timer)
        self.entry_timer_note = QLineEdit()
        self.entry_timer_note.setPlaceholderText("📝 Optional short note")
        self.entry_timer_note.returnPressed.connect(self._start_custom_timer)
        attach_row.addWidget(self.entry_timer_url, 1)
        attach_row.addWidget(self.entry_timer_note, 1)
        grid.addLayout(attach_row, 2, 1, 1, 3)

        grid.addWidget(QLabel("Countdown:"), 3, 0)
        dur_row = QHBoxLayout()
        dur_row.setSpacing(6)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(0, 24)
        self.spin_h.setSuffix(" h")
        self.spin_h.setMinimumWidth(64)

        self.spin_m = QSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setValue(15)
        self.spin_m.setSuffix(" min")
        self.spin_m.setMinimumWidth(74)

        self.spin_s = QSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setSuffix(" sec")
        self.spin_s.setMinimumWidth(70)

        dur_row.addWidget(self.spin_h)
        dur_row.addWidget(self.spin_m)
        dur_row.addWidget(self.spin_s)
        dur_row.addStretch()
        grid.addLayout(dur_row, 3, 1)

        self.chk_repeat = QCheckBox("Repeat automatically")
        grid.addWidget(self.chk_repeat, 3, 2)

        btn_start = QPushButton("Start Timer ▶")
        btn_start.setObjectName("primaryBtn")
        btn_start.setMinimumHeight(30)
        btn_start.setMinimumWidth(120)
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.clicked.connect(self._start_custom_timer)
        grid.addWidget(btn_start, 3, 3)

        layout.addWidget(custom_group)
        layout.addStretch()

    def _compose_timer_label(self, default_label: str) -> str:
        desc = self.entry_timer_name.text().strip()
        ref = self.entry_timer_ref.text().strip()
        base = desc or default_label
        if ref:
            return f"[{ref}] {base}"
        return base

    def _start_preset_timer(self, preset_label: str, seconds: int) -> None:
        title = self._compose_timer_label(preset_label)
        cat = "🎫 Ticket" if self.entry_timer_ref.text().strip() else "📌 General"
        url = self.entry_timer_url.text().strip()
        note = self.entry_timer_note.text().strip()
        self._quick_add_timer(title, seconds, cat, url=url, note=note)
        self.entry_timer_name.clear()
        self.entry_timer_ref.clear()
        self.entry_timer_url.clear()
        self.entry_timer_note.clear()

    # ── Tab 2: RDV (Rendez-vous Scheduler) ───────────────────────────────────

    def _init_rdv_tab(self, parent: QWidget) -> None:
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Left Column: MiniCalendar & Day Inspector
        cal_group = QGroupBox("📅 Calendar")
        cal_layout = QVBoxLayout(cal_group)
        cal_layout.setSpacing(4)

        self.mini_calendar = MiniCalendar(self, on_date_selected=self._on_calendar_date_selected)
        self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
        cal_layout.addWidget(self.mini_calendar)

        self.lbl_day_agenda = QLabel(f"{datetime.date.today().strftime('%b %d')}: No scheduled events")
        self.lbl_day_agenda.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 4px 6px; border-radius: 4px;"
        )
        cal_layout.addWidget(self.lbl_day_agenda)
        layout.addWidget(cal_group, 1)

        # Right Column: Appointment Details & Time Picker
        details_group = QGroupBox("⏰ Appointment Details")
        d_layout = QVBoxLayout(details_group)
        d_layout.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Event / Client:"))
        self.entry_rdv_name = QLineEdit("Team Sync")
        self.entry_rdv_name.setPlaceholderText("Client name, ticket #, or appointment description")
        title_row.addWidget(self.entry_rdv_name, 1)
        d_layout.addLayout(title_row)

        self.time_picker = BigButtonsTimePicker(self, initial_hour=14, initial_minute=0)
        d_layout.addWidget(self.time_picker)

        rdv_attach_row = QHBoxLayout()
        rdv_attach_row.setSpacing(5)
        self.entry_rdv_url = QLineEdit()
        self.entry_rdv_url.setPlaceholderText("🔗 Link / URL / Path (optional)")
        self.entry_rdv_note = QLineEdit()
        self.entry_rdv_note.setPlaceholderText("📝 Short note (optional)")
        rdv_attach_row.addWidget(self.entry_rdv_url, 1)
        rdv_attach_row.addWidget(self.entry_rdv_note, 1)
        d_layout.addLayout(rdv_attach_row)

        meta_grid = QGridLayout()
        meta_grid.setSpacing(4)

        meta_grid.addWidget(QLabel("Category:"), 0, 0)
        self.combo_rdv_cat = QComboBox()
        self.combo_rdv_cat.addItems(CATEGORIES)
        meta_grid.addWidget(self.combo_rdv_cat, 0, 1, 1, 3)

        meta_grid.addWidget(QLabel("Alert:"), 1, 0)
        self.combo_rdv_lead = QComboBox()
        self.combo_rdv_lead.addItems(["At time (0m)", "5m before", "10m before", "15m before"])
        meta_grid.addWidget(self.combo_rdv_lead, 1, 1)

        meta_grid.addWidget(QLabel("Repeat:"), 1, 2)
        self.combo_rdv_repeat = QComboBox()
        self.combo_rdv_repeat.addItems(["None", "Daily", "Weekly", "Monthly"])
        meta_grid.addWidget(self.combo_rdv_repeat, 1, 3)
        meta_grid.setColumnStretch(1, 1)
        meta_grid.setColumnStretch(3, 1)
        d_layout.addLayout(meta_grid)

        action_row = QHBoxLayout()
        btn_export = QPushButton("Export .ics")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_calendar)

        btn_import = QPushButton("Import .ics")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self._import_calendar)

        btn_add_rdv = QPushButton("Add RDV 📅")
        btn_add_rdv.setObjectName("primaryBtn")
        btn_add_rdv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rdv.clicked.connect(self._add_rendez_vous)

        action_row.addWidget(btn_export)
        action_row.addWidget(btn_import)
        action_row.addStretch()
        action_row.addWidget(btn_add_rdv)
        d_layout.addLayout(action_row)

        layout.addWidget(details_group, 1)

    # ── Tab 3: Activity (Full-Height Timers & Rendez-vous Columns) ───────────

    def _init_activity_tab(self, parent: QWidget) -> None:
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Left column: All Timers (expands full vertical height of the tab)
        t_group = QGroupBox("⏳ All Timers")
        t_layout = QVBoxLayout(t_group)
        t_layout.setSpacing(5)

        t_hdr = QHBoxLayout()
        self.lbl_timer_count = QLabel("0 active")
        self.lbl_timer_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        t_hdr.addWidget(self.lbl_timer_count)
        t_hdr.addStretch()

        btn_t_pause = QPushButton("⏯ Pause/Resume")
        btn_t_pause.setFixedHeight(22)
        btn_t_pause.clicked.connect(self._activity_pause_timer)
        btn_t_del = QPushButton("🗑️ Delete")
        btn_t_del.setObjectName("dangerBtn")
        btn_t_del.setFixedHeight(22)
        btn_t_del.clicked.connect(self._activity_delete_timer)
        t_hdr.addWidget(btn_t_pause)
        t_hdr.addWidget(btn_t_del)
        t_layout.addLayout(t_hdr)

        self.activity_timer_lb = QListWidget()
        self.activity_timer_lb.setMinimumHeight(145)
        self.activity_timer_lb.itemSelectionChanged.connect(self._on_activity_timer_select)
        t_layout.addWidget(self.activity_timer_lb, 1)

        t_detail_row = QHBoxLayout()
        t_detail_row.setSpacing(5)
        self.timer_detail = QLabel("Select a timer to view details.")
        self.timer_detail.setWordWrap(True)
        self.timer_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 5px 6px; border-radius: 4px;"
        )
        t_detail_row.addWidget(self.timer_detail, 1)

        self.btn_activity_timer_link = QPushButton("🔗 Open Link")
        self.btn_activity_timer_link.setObjectName("successBtn")
        self.btn_activity_timer_link.setFixedHeight(24)
        self.btn_activity_timer_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activity_timer_link.setVisible(False)
        self.btn_activity_timer_link.clicked.connect(self._open_selected_activity_timer_link)
        t_detail_row.addWidget(self.btn_activity_timer_link)
        t_layout.addLayout(t_detail_row)
        layout.addWidget(t_group, 1)

        # Right column: All Rendez-vous (expands full vertical height of the tab)
        r_group = QGroupBox("📅 All Rendez-vous")
        r_layout = QVBoxLayout(r_group)
        r_layout.setSpacing(5)

        r_hdr = QHBoxLayout()
        self.lbl_rdv_count = QLabel("0 scheduled")
        self.lbl_rdv_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        r_hdr.addWidget(self.lbl_rdv_count)
        r_hdr.addStretch()

        btn_r_del = QPushButton("🗑️ Delete")
        btn_r_del.setObjectName("dangerBtn")
        btn_r_del.setFixedHeight(22)
        btn_r_del.clicked.connect(self._activity_delete_rdv)
        r_hdr.addWidget(btn_r_del)
        r_layout.addLayout(r_hdr)

        self.activity_rdv_lb = QListWidget()
        self.activity_rdv_lb.setMinimumHeight(145)
        self.activity_rdv_lb.itemSelectionChanged.connect(self._on_activity_rdv_select)
        r_layout.addWidget(self.activity_rdv_lb, 1)

        r_detail_row = QHBoxLayout()
        r_detail_row.setSpacing(5)
        self.rdv_detail = QLabel("Select an RDV to view details.")
        self.rdv_detail.setWordWrap(True)
        self.rdv_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 5px 6px; border-radius: 4px;"
        )
        r_detail_row.addWidget(self.rdv_detail, 1)

        self.btn_activity_rdv_link = QPushButton("🔗 Open Link")
        self.btn_activity_rdv_link.setObjectName("successBtn")
        self.btn_activity_rdv_link.setFixedHeight(24)
        self.btn_activity_rdv_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activity_rdv_link.setVisible(False)
        self.btn_activity_rdv_link.clicked.connect(self._open_selected_activity_rdv_link)
        r_detail_row.addWidget(self.btn_activity_rdv_link)
        r_layout.addLayout(r_detail_row)
        layout.addWidget(r_group, 1)

    # ── Tab 4: Scratchpad (Time Notes) ───────────────────────────────────────

    def _init_scratchpad_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        lbl_sp = QLabel("📝 Time Notes Scratchpad")
        lbl_sp.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        toolbar.addWidget(lbl_sp)

        status_txt = f"Saved {self.scratchpad_state.updated_at}" if self.scratchpad_state.updated_at else "Auto-save ready"
        self.lbl_scratchpad_status = QLabel(status_txt)
        self.lbl_scratchpad_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        toolbar.addWidget(self.lbl_scratchpad_status)
        toolbar.addStretch()

        btn_stamp = QPushButton("🕒 +Timestamp (Ctrl+T)")
        btn_stamp.setObjectName("primaryBtn")
        btn_stamp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_stamp.clicked.connect(self._insert_scratchpad_timestamp)
        toolbar.addWidget(btn_stamp)

        btn_copy = QPushButton("📋 Copy All")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._copy_scratchpad)
        toolbar.addWidget(btn_copy)

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_scratchpad)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        self.scratchpad_text = QPlainTextEdit()
        self.scratchpad_text.setPlaceholderText(
            "Jot down quick time notes, client names, ticket numbers, or call timestamps here...\n"
            "Press Ctrl+T to insert the current timestamp."
        )
        self.scratchpad_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        if self.scratchpad_state.content:
            self.scratchpad_text.setPlainText(self.scratchpad_state.content)
        self.scratchpad_text.textChanged.connect(self._on_scratchpad_modified)
        layout.addWidget(self.scratchpad_text, 1)

        shortcut_ts = QShortcut(QKeySequence("Ctrl+T"), self.scratchpad_text)
        shortcut_ts.activated.connect(self._insert_scratchpad_timestamp)

    # ── Tab 5: Completed / Triggered History ─────────────────────────────────

    def _init_history_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        h_group = QGroupBox("📜 Completed & Triggered Reminders History")
        h_layout = QVBoxLayout(h_group)
        h_layout.setSpacing(6)

        h_hdr = QHBoxLayout()
        self.lbl_history_count = QLabel("0 logged")
        self.lbl_history_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        h_hdr.addWidget(self.lbl_history_count)
        h_hdr.addStretch()

        self.btn_open_history_link = QPushButton("🔗 Open Link")
        self.btn_open_history_link.setObjectName("successBtn")
        self.btn_open_history_link.setFixedHeight(23)
        self.btn_open_history_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_history_link.setVisible(False)
        self.btn_open_history_link.clicked.connect(self._open_selected_history_link)
        h_hdr.addWidget(self.btn_open_history_link)

        btn_copy_h = QPushButton("📋 Copy Selected")
        btn_copy_h.setFixedHeight(23)
        btn_copy_h.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_h.clicked.connect(self._copy_selected_history)
        h_hdr.addWidget(btn_copy_h)

        btn_clear_h = QPushButton("🧹 Clear History")
        btn_clear_h.setObjectName("dangerBtn")
        btn_clear_h.setFixedHeight(23)
        btn_clear_h.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_h.clicked.connect(self._clear_history)
        h_hdr.addWidget(btn_clear_h)
        h_layout.addLayout(h_hdr)

        self.activity_history_lb = QListWidget()
        self.activity_history_lb.setMinimumHeight(140)
        self.activity_history_lb.itemSelectionChanged.connect(self._on_activity_history_select)
        h_layout.addWidget(self.activity_history_lb, 1)

        self.history_detail = QLabel("Select a history entry above to inspect full completion details.")
        self.history_detail.setWordWrap(True)
        self.history_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 6px 8px; border-radius: 4px;"
        )
        h_layout.addWidget(self.history_detail)

        layout.addWidget(h_group, 1)
        self._load_history_list()

    # ── Tab 6: Settings ──────────────────────────────────────────────────────

    def _init_settings_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        s_group = QGroupBox("🔊 Sound, Volume & System Preferences")
        s_layout = QVBoxLayout(s_group)
        s_layout.setSpacing(8)

        # Sound preset + preview
        row_tone = QHBoxLayout()
        row_tone.addWidget(QLabel("Alarm Tone:"))
        self.combo_sound = QComboBox()
        for key, label in SOUND_PRESETS.items():
            self.combo_sound.addItem(f"{key} — {label}", key)
        idx = self.combo_sound.findData(self.app_config.sound_type)
        if idx >= 0:
            self.combo_sound.setCurrentIndex(idx)
        row_tone.addWidget(self.combo_sound, 1)

        self.btn_preview = QPushButton("🔊 Preview")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.clicked.connect(self._toggle_preview)
        row_tone.addWidget(self.btn_preview)
        s_layout.addLayout(row_tone)

        # Volume slider
        row_vol = QHBoxLayout()
        self.lbl_volume = QLabel(f"Master Volume: {self.app_config.volume}%")
        self.lbl_volume.setFixedWidth(160)
        row_vol.addWidget(self.lbl_volume)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.app_config.volume)
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"Master Volume: {v}%"))
        row_vol.addWidget(self.slider_volume, 1)
        s_layout.addLayout(row_vol)

        # Popup & Mini HUD Opacity slider (60% to 100%, default 90%; Main Window stays 100% opaque)
        row_opacity = QHBoxLayout()
        self.lbl_opacity = QLabel(f"Popup & HUD Opacity: {self.app_config.overlay_opacity}%")
        self.lbl_opacity.setFixedWidth(160)
        row_opacity.addWidget(self.lbl_opacity)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 100)
        self.slider_opacity.setValue(self.app_config.overlay_opacity)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        row_opacity.addWidget(self.slider_opacity, 1)
        s_layout.addLayout(row_opacity)

        # Custom audio file
        row_file = QHBoxLayout()
        row_file.addWidget(QLabel("Custom Audio:"))
        self.lbl_sound_path = QLabel(self.app_config.custom_sound_path or "No file chosen")
        self.lbl_sound_path.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; padding: 4px 6px; border-radius: 4px;"
        )
        row_file.addWidget(self.lbl_sound_path, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_audio)
        row_file.addWidget(btn_browse)
        s_layout.addLayout(row_file)

        # Checkboxes & Snooze
        row_opts = QHBoxLayout()
        self.chk_escalate = QCheckBox("Gradual volume escalation")
        self.chk_escalate.setChecked(self.app_config.gradual_escalation)
        row_opts.addWidget(self.chk_escalate)

        self.chk_startup = QCheckBox("Launch at Windows boot")
        self.chk_startup.setChecked(is_startup_enabled())
        row_opts.addWidget(self.chk_startup)
        row_opts.addStretch()
        s_layout.addLayout(row_opts)

        row_bottom = QHBoxLayout()
        row_bottom.addWidget(QLabel("Default Snooze:"))
        self.combo_snooze = QComboBox()
        for opt in SNOOZE_OPTIONS:
            self.combo_snooze.addItem(f"{opt} min", opt)
        s_idx = self.combo_snooze.findData(self.app_config.default_snooze_minutes)
        if s_idx >= 0:
            self.combo_snooze.setCurrentIndex(s_idx)
        row_bottom.addWidget(self.combo_snooze)

        self.lbl_settings_saved = QLabel("")
        self.lbl_settings_saved.setStyleSheet(f"color: {COLORS['accent_success']}; font-weight: bold;")
        row_bottom.addWidget(self.lbl_settings_saved)
        row_bottom.addStretch()

        btn_save = QPushButton("Save Settings ✓")
        btn_save.setObjectName("successBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_settings)
        row_bottom.addWidget(btn_save)
        s_layout.addLayout(row_bottom)

        layout.addWidget(s_group)
        layout.addStretch()

    # ── Bottom Active Queue (Visible Across All 6 Tabs, Tall Multi-Row View) ─

    def _build_active_queue(self, parent_layout: QVBoxLayout) -> None:
        q_group = QGroupBox("Active Reminders Queue")
        q_layout = QVBoxLayout(q_group)
        q_layout.setContentsMargins(8, 6, 8, 6)
        q_layout.setSpacing(4)

        hdr_row = QHBoxLayout()
        self.lbl_queue_status = QLabel("All quiet")
        self.lbl_queue_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        hdr_row.addWidget(self.lbl_queue_status)
        hdr_row.addStretch()

        btn_pause_sel = QPushButton("⏯ Pause / Resume")
        btn_pause_sel.setFixedHeight(22)
        btn_pause_sel.clicked.connect(self._toggle_selected_pause)
        hdr_row.addWidget(btn_pause_sel)

        btn_del_sel = QPushButton("🗑️ Delete")
        btn_del_sel.setObjectName("dangerBtn")
        btn_del_sel.setFixedHeight(22)
        btn_del_sel.clicked.connect(self._delete_selected)
        hdr_row.addWidget(btn_del_sel)
        q_layout.addLayout(hdr_row)

        self.listbox = QListWidget()
        self.listbox.setMinimumHeight(155)
        q_layout.addWidget(self.listbox, 1)

        parent_layout.addWidget(q_group, 3)

    # ── Action Slots & Backend Wiring ────────────────────────────────────────

    def _quick_add_timer(
        self,
        name: str,
        seconds: int,
        category: str = "📌 General",
        url: str = "",
        note: str = "",
    ) -> None:
        self.scheduler.add_item(
            kind="timer",
            name=name,
            seconds_from_now=seconds,
            original_duration=seconds,
            category=category,
            url=url,
            note=note,
        )
        self.smart_feedback.setText(f"✅ Started '{name}' ({seconds // 60}m)")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self._refresh_loop()

    def _on_smart_input_submit(self) -> None:
        query = self.smart_entry.text().strip()
        parsed = NaturalParser.parse(query)
        if not parsed:
            self.smart_feedback.setText('❌ Unrecognized. Try: "Ring in 15 min", "Call Sam in 2 days", "RDV at 4PM"')
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 11px; border: none;")
            return

        if parsed["kind"] == "timer":
            self.scheduler.add_item(
                kind="timer",
                name=parsed["name"],
                seconds_from_now=parsed["seconds_from_now"],
                original_duration=parsed["original_duration"],
            )
        else:
            self.scheduler.add_item(
                kind="rendez-vous",
                name=parsed["name"],
                seconds_from_now=parsed["seconds_from_now"],
            )
            self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())

        self.smart_feedback.setText(f"✅ Scheduled {parsed['display_str']}")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self.smart_entry.clear()
        self._refresh_loop()

    def _start_custom_timer(self) -> None:
        total_sec = self.spin_h.value() * 3600 + self.spin_m.value() * 60 + self.spin_s.value()
        if total_sec <= 0:
            QMessageBox.warning(self, "Invalid Duration", "Timer duration must be greater than 0 seconds.")
            return

        full_name = self._compose_timer_label("Reminder")
        has_ref = bool(self.entry_timer_ref.text().strip())
        cat = "🎫 Ticket" if has_ref else "📌 General"
        repeat = total_sec if self.chk_repeat.isChecked() else 0

        self.scheduler.add_item(
            kind="timer",
            name=full_name,
            seconds_from_now=total_sec,
            repeat_sec=repeat,
            original_duration=total_sec,
            category=cat,
            url=self.entry_timer_url.text().strip(),
            note=self.entry_timer_note.text().strip(),
        )
        self.smart_feedback.setText(f"✅ Started timer '{full_name}'")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self.entry_timer_name.clear()
        self.entry_timer_ref.clear()
        self.entry_timer_url.clear()
        self.entry_timer_note.clear()
        self._refresh_loop()

    def _add_rendez_vous(self) -> None:
        name = self.entry_rdv_name.text().strip() or "Meeting"
        d_val = self.mini_calendar.selected_date
        h, m = self.time_picker.get_time()
        rule = self.combo_rdv_repeat.currentText().lower()
        cat = self.combo_rdv_cat.currentText()
        url = self.entry_rdv_url.text().strip()
        note = self.entry_rdv_note.text().strip()

        lead_str = self.combo_rdv_lead.currentText()
        lead_time = 5 if "5m" in lead_str else (10 if "10m" in lead_str else (15 if "15m" in lead_str else 0))

        dt = datetime.datetime.combine(d_val, datetime.time(h, m))
        delta = (dt - datetime.datetime.now()).total_seconds()
        if delta <= 0:
            QMessageBox.warning(self, "Past Date/Time", "Please choose a future date and time.")
            return

        self.scheduler.add_item(
            kind="rendez-vous",
            name=name,
            seconds_from_now=delta,
            repeat_rule=rule,
            category=cat,
            lead_time_min=lead_time,
            url=url,
            note=note,
            anchor_day=d_val.day if rule == "monthly" else 0,
        )
        self.entry_rdv_url.clear()
        self.entry_rdv_note.clear()
        self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
        self._on_calendar_date_selected(d_val)
        self.smart_feedback.setText(f"✅ Scheduled RDV '{name}' on {dt.strftime('%b %d at %H:%M')}")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self._refresh_loop()

    def _on_calendar_date_selected(self, d_val: datetime.date) -> None:
        events = self.scheduler.get_events_for_date(d_val)
        if events:
            titles = ", ".join(f"'{ev.name}'" for ev in events[:2])
            more = f" (+{len(events) - 2})" if len(events) > 2 else ""
            self.lbl_day_agenda.setText(f"{d_val.strftime('%b %d')}: {titles}{more}")
            self.lbl_day_agenda.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['accent']}; "
                f"font-size: 11px; font-weight: bold; padding: 4px 6px; border-radius: 4px;"
            )
        else:
            self.lbl_day_agenda.setText(f"{d_val.strftime('%b %d')}: No scheduled events")
            self.lbl_day_agenda.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
                f"font-size: 11px; padding: 4px 6px; border-radius: 4px;"
            )

    def _toggle_active_timer_pause(self) -> None:
        active = self.scheduler.get_active_timer()
        if active:
            now_paused = self.scheduler.toggle_pause(active.id)
            self.btn_ring_play_pause.setText("▶ Resume" if now_paused else "⏯ Pause")
        else:
            nearest = self.scheduler.get_nearest_item()
            if nearest:
                self.scheduler.toggle_pause(nearest.id)
        self._refresh_loop()

    def _stop_active_timer(self) -> None:
        active = self.scheduler.get_active_timer()
        if active:
            self.scheduler.remove_item(active.id)
            self.btn_ring_play_pause.setText("⏯ Pause")
            self._refresh_loop()

    def _toggle_selected_pause(self) -> None:
        row = self.listbox.currentRow()
        if 0 <= row < len(self.scheduler.items):
            self.scheduler.toggle_pause(self.scheduler.items[row].id)
            self._refresh_loop()

    def _delete_selected(self) -> None:
        row = self.listbox.currentRow()
        if 0 <= row < len(self.scheduler.items):
            self.scheduler.remove_item(self.scheduler.items[row].id)
            self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
            self._refresh_loop()

    # ── Calendar Import / Export ─────────────────────────────────────────────

    def _export_calendar(self) -> None:
        rdv_items = [it.to_dict() for it in self.scheduler.items if it.kind == "rendez-vous"]
        if not rdv_items:
            QMessageBox.information(self, "Export", "No rendez-vous events to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Calendar", "events.ics", "iCalendar Files (*.ics)")
        if path and CalendarManager.export_to_ics(rdv_items, path):
            self.smart_feedback.setText(f"✅ Exported {len(rdv_items)} event(s) to {os.path.basename(path)}")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")

    def _import_calendar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Calendar", "", "iCalendar Files (*.ics)")
        if path:
            events = CalendarManager.import_from_ics(path)
            added = 0
            now = time.time()
            for ev in events:
                if ev["target_time"] > now:
                    self.scheduler.add_item(
                        kind="rendez-vous",
                        name=ev["name"],
                        seconds_from_now=ev["target_time"] - now,
                        repeat_rule=ev.get("repeat_rule", "none"),
                        url=ev.get("url", ""),
                        note=ev.get("note", ""),
                    )
                    added += 1
            self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
            self.smart_feedback.setText(f"✅ Imported {added} upcoming event(s)")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
            self._refresh_loop()

    # ── Scratchpad Actions ───────────────────────────────────────────────────

    def _insert_scratchpad_timestamp(self) -> None:
        stamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        self.scratchpad_text.insertPlainText(stamp)
        self.scratchpad_text.setFocus()
        self._save_scratchpad_now()

    def _copy_scratchpad(self) -> None:
        content = self.scratchpad_text.toPlainText().strip()
        if content:
            QGuiApplication.clipboard().setText(content)
            self.lbl_scratchpad_status.setText("✅ Copied to clipboard")
            self.lbl_scratchpad_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px;")

    def _clear_scratchpad(self) -> None:
        if not self.scratchpad_text.toPlainText().strip():
            return
        reply = QMessageBox.question(
            self,
            "Clear Scratchpad",
            "Clear all time notes from the scratchpad?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.scratchpad_text.clear()
            self._save_scratchpad_now()

    def _on_scratchpad_modified(self) -> None:
        self._scratchpad_save_timer.start()

    def _save_scratchpad_now(self) -> None:
        now_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.scratchpad_state.content = self.scratchpad_text.toPlainText()
        self.scratchpad_state.updated_at = now_stamp
        Storage.save_scratchpad(self.scratchpad_state)
        self.lbl_scratchpad_status.setText(f"Saved {now_stamp}")
        self.lbl_scratchpad_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

    # ── Activity & History Helpers ───────────────────────────────────────────

    def _fmt_remain(self, item: ScheduledItem, now: float) -> str:
        rem = int(item.remaining_paused if item.is_paused else max(0.0, item.target_time - now))
        prefix = "⏸ PAUSED " if item.is_paused else ""
        m, s = divmod(rem, 60)
        h, m = divmod(m, 60)
        return f"{prefix}{h:02d}:{m:02d}:{s:02d}"

    def _fmt_target(self, item: ScheduledItem) -> str:
        return datetime.datetime.fromtimestamp(item.target_time).strftime("%b %d %H:%M:%S")

    def _on_activity_timer_select(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            it = self._activity_timer_items[row]
            now = time.time()
            rep = "Yes" if it.repeat_sec > 0 else "No"
            parts = [f"📌 {it.name}", f"⏱ {self._fmt_remain(it, now)}", f"🔔 {self._fmt_target(it)} (Repeat: {rep})"]
            if it.note:
                parts.append(f"📝 {it.note}")
            if it.url:
                parts.append(f"🔗 {it.url}")
            self.timer_detail.setText("   |   ".join(parts))
            self.btn_activity_timer_link.setVisible(bool(it.url))
            self.btn_activity_timer_link.setToolTip(normalize_link_target(it.url) if it.url else "")
        else:
            self.btn_activity_timer_link.setVisible(False)

    def _on_activity_rdv_select(self) -> None:
        row = self.activity_rdv_lb.currentRow()
        if 0 <= row < len(self._activity_rdv_items):
            it = self._activity_rdv_items[row]
            now = time.time()
            cat = it.category if it.category and it.category != "General" else "—"
            rep = it.repeat_rule.capitalize() if it.repeat_rule and it.repeat_rule != "none" else "None"
            lead = f"{it.lead_time_min}m early" if it.lead_time_min else "On time"
            parts = [
                f"📌 {it.name}",
                f"⏱ {self._fmt_remain(it, now)}",
                f"📅 {self._fmt_target(it)} ({cat}, {lead}, {rep})",
            ]
            if it.note:
                parts.append(f"📝 {it.note}")
            if it.url:
                parts.append(f"🔗 {it.url}")
            self.rdv_detail.setText("   |   ".join(parts))
            self.btn_activity_rdv_link.setVisible(bool(it.url))
            self.btn_activity_rdv_link.setToolTip(normalize_link_target(it.url) if it.url else "")
        else:
            self.btn_activity_rdv_link.setVisible(False)

    def _open_selected_activity_timer_link(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            url = self._activity_timer_items[row].url
            if url:
                open_attachment_link(url)

    def _open_selected_activity_rdv_link(self) -> None:
        row = self.activity_rdv_lb.currentRow()
        if 0 <= row < len(self._activity_rdv_items):
            url = self._activity_rdv_items[row].url
            if url:
                open_attachment_link(url)

    def _activity_pause_timer(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            self.scheduler.toggle_pause(self._activity_timer_items[row].id)
            self._refresh_loop()

    def _activity_delete_timer(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            self.scheduler.remove_item(self._activity_timer_items[row].id)
            self.timer_detail.setText("Select a timer to view details.")
            self.btn_activity_timer_link.setVisible(False)
            self._refresh_loop()

    def _activity_delete_rdv(self) -> None:
        row = self.activity_rdv_lb.currentRow()
        if 0 <= row < len(self._activity_rdv_items):
            self.scheduler.remove_item(self._activity_rdv_items[row].id)
            self.rdv_detail.setText("Select an RDV to view details.")
            self.btn_activity_rdv_link.setVisible(False)
            self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
            self._refresh_loop()

    def _load_history_list(self) -> None:
        if not hasattr(self, "activity_history_lb"):
            return
        self._history_items = Storage.load_history()
        self.activity_history_lb.clear()
        for h in self._history_items:
            cat = h.get("category", "")
            icon = cat.split()[0] if cat and cat not in ("General", "📌 General") else "📌"
            status = h.get("status", "Triggered")
            time_part = h.get("completed_at", "")
            badges = (" 🔗" if h.get("url") else "") + (" 📝" if h.get("note") else "")
            self.activity_history_lb.addItem(f"{icon} {h.get('name', 'Event')}{badges} — [{status}] {time_part}")
        cnt = len(self._history_items)
        self.lbl_history_count.setText(f"{cnt} completed / triggered entry(s)" if cnt else "0 logged")
        if hasattr(self, "btn_open_history_link") and self.activity_history_lb.currentRow() < 0:
            self.btn_open_history_link.setVisible(False)

    def _on_activity_history_select(self) -> None:
        row = self.activity_history_lb.currentRow()
        if 0 <= row < len(self._history_items):
            h = self._history_items[row]
            url = str(h.get("url", "") or "").strip()
            note = str(h.get("note", "") or "").strip()
            parts = [
                f"📌 {h.get('name', 'Event')}",
                f"🏷 {h.get('kind', '').capitalize()} ({h.get('category', 'General')})",
                f"⚡ {h.get('status', 'Completed')} at {h.get('completed_at', '')}",
            ]
            if note:
                parts.append(f"📝 {note}")
            if url:
                parts.append(f"🔗 {url}")
            self.history_detail.setText("   |   ".join(parts))
            self.btn_open_history_link.setVisible(bool(url))
            self.btn_open_history_link.setToolTip(normalize_link_target(url) if url else "")
        else:
            self.btn_open_history_link.setVisible(False)

    def _open_selected_history_link(self) -> None:
        row = self.activity_history_lb.currentRow()
        if 0 <= row < len(self._history_items):
            url = str(self._history_items[row].get("url", "") or "").strip()
            if url:
                open_attachment_link(url)

    def _copy_selected_history(self) -> None:
        row = self.activity_history_lb.currentRow()
        if 0 <= row < len(self._history_items):
            h = self._history_items[row]
            line = f"[{h.get('completed_at', '')}] {h.get('name', 'Event')} ({h.get('status', 'Completed')})"
            if h.get("note"):
                line += f" | Note: {h['note']}"
            if h.get("url"):
                line += f" | Link: {h['url']}"
            QGuiApplication.clipboard().setText(line)
            self.history_detail.setText(f"✅ Copied to clipboard: {line}")

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Clear all completed history entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            Storage.clear_history()
            self._load_history_list()
            self.btn_open_history_link.setVisible(False)
            self.history_detail.setText("Select a history entry above to inspect full completion details.")

    # ── Settings & Audio Handlers ────────────────────────────────────────────

    def _toggle_preview(self) -> None:
        if self.is_previewing:
            self.sound_player.stop_preview()
            self.btn_preview.setText("🔊 Preview")
            self.is_previewing = False
        else:
            snd_type = self.combo_sound.currentData() or "gentle"
            custom_p = self.lbl_sound_path.text()
            vol = self.slider_volume.value()
            self.sound_player.start_preview(snd_type, "" if custom_p == "No file chosen" else custom_p, volume=vol)
            self.btn_preview.setText("⏹ Stop")
            self.is_previewing = True
            QTimer.singleShot(3500, self._reset_preview_btn)

    def _reset_preview_btn(self) -> None:
        self.btn_preview.setText("🔊 Preview")
        self.is_previewing = False

    def _browse_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav);;All Files (*.*)")
        if path:
            self.lbl_sound_path.setText(path)
            idx = self.combo_sound.findData("custom")
            if idx >= 0:
                self.combo_sound.setCurrentIndex(idx)

    def _on_opacity_slider_changed(self, value: int) -> None:
        clamped = max(60, min(100, int(value)))
        self.lbl_opacity.setText(f"Popup & HUD Opacity: {clamped}%")
        ratio = clamped / 100.0
        if self.hud:
            self.hud.set_hud_opacity(ratio)
        AlarmDialog.set_active_popups_opacity(ratio)

    def _save_settings(self) -> None:
        custom_text = self.lbl_sound_path.text()
        self.app_config.sound_type = self.combo_sound.currentData() or "gentle"
        self.app_config.custom_sound_path = "" if custom_text == "No file chosen" else custom_text
        self.app_config.volume = self.slider_volume.value()
        self.app_config.overlay_opacity = max(60, min(100, self.slider_opacity.value()))
        self.app_config.default_snooze_minutes = int(self.combo_snooze.currentData() or 5)
        self.app_config.gradual_escalation = self.chk_escalate.isChecked()
        self.app_config.start_on_boot = self.chk_startup.isChecked()

        Storage.save_config(self.app_config)
        self.sound_player.update_config(self.app_config)
        self._on_opacity_slider_changed(self.app_config.overlay_opacity)
        set_startup_enabled(self.app_config.start_on_boot)

        self.lbl_settings_saved.setText("✅ Saved!")
        QTimer.singleShot(3000, lambda: self.lbl_settings_saved.setText(""))

    # ── Mini HUD Controller ──────────────────────────────────────────────────

    def _toggle_hud(self) -> None:
        if self.hud and self.hud.isVisible():
            self._save_hud_pos()
            self.hud.hide()
            self.hud_enabled = False
            self.btn_hud_toggle.setText("📌 HUD: OFF")
        else:
            self._show_hud()

    def _show_hud(self) -> None:
        opacity_ratio = max(0.60, min(1.0, self.app_config.overlay_opacity / 100.0))
        if self.hud is None:
            self.hud = FloatingMiniHUD(
                master=self,
                on_toggle_pause=self._toggle_active_timer_pause,
                on_bring_main_to_front=lambda: self.window().showNormal(),
                on_close=self._on_hud_close,
                initial_x=self.app_config.hud_x,
                initial_y=self.app_config.hud_y,
                opacity=opacity_ratio,
            )
        else:
            self.hud.set_hud_opacity(opacity_ratio)
        self.hud.show()
        self.hud.raise_()
        self.hud_enabled = True
        self.btn_hud_toggle.setText("📌 HUD: ON")

    def _on_hud_close(self) -> None:
        self._save_hud_pos()
        self.hud_enabled = False
        self.btn_hud_toggle.setText("📌 HUD: OFF")

    def _save_hud_pos(self) -> None:
        if self.hud:
            pos = self.hud.pos()
            self.app_config.hud_x = pos.x()
            self.app_config.hud_y = pos.y()
            self.app_config.hud_enabled = self.hud_enabled
            Storage.save_config(self.app_config)

    # ── 1-Second QTimer Live Refresh Loop ────────────────────────────────────

    def _refresh_loop(self) -> None:
        cur_row = self.listbox.currentRow()
        self.listbox.clear()
        now = time.time()

        nearest_item: Optional[ScheduledItem] = None
        nearest_delta: float = 99999999.0
        active_timer: Optional[ScheduledItem] = None

        for it in self.scheduler.items:
            if it.is_paused:
                remain = it.remaining_paused
                status_prefix = "⏸ [PAUSED] "
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
            cat_icon = f"[{it.category.split()[0]}] " if it.category and it.category not in ("General", "📌 General") else ""
            icon = "⏳" if it.kind == "timer" else "📅"
            rep = " 🔁" if (it.repeat_sec > 0 or it.repeat_rule != "none") else ""
            attach = (" 🔗" if it.url else "") + (" 📝" if it.note else "")
            item_widget = QListWidgetItem(
                f"{icon} {status_prefix}{cat_icon}{it.name}{rep}{attach} — {h:02d}:{m:02d}:{s:02d}"
            )
            if it.note or it.url:
                tip_lines = [it.name]
                if it.note:
                    tip_lines.append(f"📝 {it.note}")
                if it.url:
                    tip_lines.append(f"🔗 {it.url}")
                item_widget.setToolTip("\n".join(tip_lines))

            if not it.is_paused and remain < 60:
                item_widget.setForeground(QColor(COLORS["accent_danger"]))
            elif not it.is_paused and remain < 300:
                item_widget.setForeground(QColor(COLORS["accent_warning"]))

            self.listbox.addItem(item_widget)

        if 0 <= cur_row < self.listbox.count():
            self.listbox.setCurrentRow(cur_row)

        total_active = len(self.scheduler.items)
        self.lbl_queue_status.setText(f"{total_active} active reminder(s)" if total_active else "All quiet")

        # Update Radial Progress Ring
        if active_timer:
            rem = active_timer.remaining_paused if active_timer.is_paused else max(0.0, active_timer.target_time - now)
            tot = max(1.0, active_timer.original_duration)
            self.ring.update_countdown(
                remaining_sec=rem,
                total_sec=tot,
                title=active_timer.name,
                is_repeating=active_timer.repeat_sec > 0,
                is_paused=active_timer.is_paused,
            )
            self.btn_ring_play_pause.setText("▶ Resume" if active_timer.is_paused else "⏯ Pause")
        elif nearest_item:
            rem = nearest_item.remaining_paused if nearest_item.is_paused else max(0.0, nearest_item.target_time - now)
            tot = max(1.0, nearest_item.original_duration or rem)
            self.ring.update_countdown(
                remaining_sec=rem,
                total_sec=tot,
                title=nearest_item.name,
                is_repeating=nearest_item.repeat_rule != "none",
                is_paused=nearest_item.is_paused,
            )
            self.btn_ring_play_pause.setText("⏯ Pause")
        else:
            self.ring.set_idle()
            self.btn_ring_play_pause.setText("⏯ Pause")

        # Update Floating Mini HUD
        if self.hud and self.hud.isVisible():
            hud_item = active_timer or nearest_item
            if hud_item:
                rem = hud_item.remaining_paused if hud_item.is_paused else max(0.0, hud_item.target_time - now)
                is_ticket = hud_item.category == "🎫 Ticket"
                self.hud.update_status(hud_item.name, rem, is_paused=hud_item.is_paused, is_sla=is_ticket)
            else:
                self.hud.set_idle()

        self._refresh_activity_tab(now)

    def _refresh_activity_tab(self, now: float) -> None:
        timers = [it for it in self.scheduler.items if it.kind == "timer"]
        rdvs = [it for it in self.scheduler.items if it.kind == "rendez-vous"]

        t_row = self.activity_timer_lb.currentRow()
        self.activity_timer_lb.blockSignals(True)
        self.activity_timer_lb.clear()
        self._activity_timer_items = timers
        for it in timers:
            rem = int(it.remaining_paused if it.is_paused else max(0.0, it.target_time - now))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            p_badge = " ⏸" if it.is_paused else ""
            r_badge = " 🔁" if it.repeat_sec > 0 else ""
            a_badge = (" 🔗" if it.url else "") + (" 📝" if it.note else "")
            self.activity_timer_lb.addItem(f"⏳{p_badge}{r_badge} {it.name}{a_badge} — {h:02d}:{m:02d}:{s:02d}")
        if 0 <= t_row < self.activity_timer_lb.count():
            self.activity_timer_lb.setCurrentRow(t_row)
        self.activity_timer_lb.blockSignals(False)
        self._on_activity_timer_select()
        self.lbl_timer_count.setText(f"{len(timers)} active")

        r_row = self.activity_rdv_lb.currentRow()
        self.activity_rdv_lb.blockSignals(True)
        self.activity_rdv_lb.clear()
        self._activity_rdv_items = rdvs
        for it in rdvs:
            rem = int(it.remaining_paused if it.is_paused else max(0.0, it.target_time - now))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            cat_icon = it.category.split()[0] if it.category and it.category not in ("General", "📌 General") else "📌"
            r_badge = " 🔁" if it.repeat_rule and it.repeat_rule != "none" else ""
            a_badge = (" 🔗" if it.url else "") + (" 📝" if it.note else "")
            self.activity_rdv_lb.addItem(f"{cat_icon}{r_badge} {it.name}{a_badge} — {h:02d}:{m:02d}:{s:02d}")
        if 0 <= r_row < self.activity_rdv_lb.count():
            self.activity_rdv_lb.setCurrentRow(r_row)
        self.activity_rdv_lb.blockSignals(False)
        self._on_activity_rdv_select()
        self.lbl_rdv_count.setText(f"{len(rdvs)} scheduled")

    # ── Bottom-Right Alarm Popups & Missed Alerts ────────────────────────────

    def _check_missed_alarms(self) -> None:
        if self.scheduler.missed_items:
            names = ", ".join(f"'{it.name}'" for it in self.scheduler.missed_items[:3])
            more = f" +{len(self.scheduler.missed_items) - 3} more" if len(self.scheduler.missed_items) > 3 else ""
            single = self.scheduler.missed_items[0] if len(self.scheduler.missed_items) == 1 else None
            AlarmDialog(
                master=self,
                title_text="Missed While Closed",
                reminder_name=f"{names}{more}",
                category="⚠️ Missed",
                url=single.url if single else "",
                note=single.note if single else "",
                config=self.app_config,
            )
            self.scheduler.missed_items.clear()

    def _handle_wake_missed_ui(self, items: List[ScheduledItem]) -> None:
        names = ", ".join(f"'{it.name}'" for it in items[:3])
        single = items[0] if len(items) == 1 else None
        AlarmDialog(
            master=self,
            title_text="Missed During PC Sleep",
            reminder_name=names,
            category="⚠️ Wake Drift",
            url=single.url if single else "",
            note=single.note if single else "",
            config=self.app_config,
        )

    def _popup_alarm(self, item: ScheduledItem) -> None:
        self.sound_player.start_alarm(config=self.app_config)

        now_str = datetime.datetime.now().strftime("%b %d, %H:%M:%S")
        Storage.add_history_entry(
            HistoryEntry(
                name=item.name,
                kind=item.kind,
                category=item.category,
                completed_at=now_str,
                status="Triggered",
                url=item.url,
                note=item.note,
            )
        )
        self._load_history_list()

        def dismiss() -> None:
            self.sound_player.stop_alarm()
            Storage.add_history_entry(
                HistoryEntry(
                    name=item.name,
                    kind=item.kind,
                    category=item.category,
                    completed_at=datetime.datetime.now().strftime("%b %d, %H:%M:%S"),
                    status="Dismissed",
                    url=item.url,
                    note=item.note,
                )
            )
            self._load_history_list()

        def open_link_action() -> None:
            self.sound_player.stop_alarm()
            Storage.add_history_entry(
                HistoryEntry(
                    name=item.name,
                    kind=item.kind,
                    category=item.category,
                    completed_at=datetime.datetime.now().strftime("%b %d, %H:%M:%S"),
                    status="Opened Link",
                    url=item.url,
                    note=item.note,
                )
            )
            self._load_history_list()

        def snooze(minutes: int) -> None:
            self.sound_player.stop_alarm()
            Storage.add_history_entry(
                HistoryEntry(
                    name=f"[Snooze {minutes}m] {item.name}",
                    kind=item.kind,
                    category=item.category,
                    completed_at=datetime.datetime.now().strftime("%b %d, %H:%M:%S"),
                    status=f"Snoozed {minutes}m",
                    url=item.url,
                    note=item.note,
                )
            )
            self._load_history_list()
            self.scheduler.add_item(
                kind=item.kind,
                name=f"[Snooze] {item.name}",
                seconds_from_now=minutes * 60,
                original_duration=minutes * 60,
                category=item.category,
                url=item.url,
                note=item.note,
            )
            self._refresh_loop()

        AlarmDialog(
            master=self,
            title_text=item.name,
            reminder_name="Timer finished" if item.kind == "timer" else "Rendez-vous appointment",
            on_dismiss=dismiss,
            on_snooze=snooze,
            on_open_link=open_link_action,
            category=item.category,
            url=item.url,
            note=item.note,
            config=self.app_config,
        )


class MainApp(QMainWindow):
    """Standalone PySide6 application shell wrapping TimerRendezVousWidget with System Tray & Global Hotkey."""

    def __init__(self, start_minimized: bool = False):
        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} ⏰")
        self.resize(UI_DIMENSIONS["window_width"], UI_DIMENSIONS["window_height"])
        self.setMinimumSize(600, 720)
        self.setStyleSheet(DARK_QSS)

        self.module_widget = TimerRendezVousWidget(self)
        self.setCentralWidget(self.module_widget)

        # Wire thread-safe tray signals
        self.module_widget.bridge.toggleVisibilityRequested.connect(self.toggle_visibility)
        self.module_widget.bridge.quitRequested.connect(self.quit_app)

        self.tray = TrayManager(
            on_toggle=lambda: self.module_widget.bridge.toggleVisibilityRequested.emit(),
            on_exit=lambda: self.module_widget.bridge.quitRequested.emit(),
            on_toggle_pause=lambda: self.module_widget.bridge.togglePauseRequested.emit(),
            on_toggle_hud=lambda: self.module_widget.bridge.toggleHudRequested.emit(),
        )
        self.tray.start()

        # Sync tray tooltip every second
        self._tray_timer = QTimer(self)
        self._tray_timer.setInterval(1000)
        self._tray_timer.timeout.connect(self._update_tray_tooltip)
        self._tray_timer.start()

        self._setup_hotkey()

        if start_minimized:
            self.hide()
        else:
            self.show()

    def _update_tray_tooltip(self) -> None:
        nearest = self.module_widget.scheduler.get_nearest_item()
        if nearest:
            rem = max(0, int(nearest.target_time - time.time()))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            tooltip = f"Next: {nearest.name} ({h:02d}:{m:02d}:{s:02d})"
        else:
            tooltip = f"{APP_TITLE}: All quiet"
        self.tray.update_tooltip(tooltip)

    def _setup_hotkey(self) -> None:
        self._hotkey_listener = GlobalHotkeyListener(
            HOTKEY,
            lambda: self.module_widget.bridge.toggleVisibilityRequested.emit(),
        )
        self._hotkey_listener.start()
        shortcut = QShortcut(QKeySequence("Ctrl+F7"), self)
        shortcut.activated.connect(self.toggle_visibility)

    def closeEvent(self, event) -> None:
        """Minimize to system tray when window [X] is clicked."""
        event.ignore()
        self.hide_to_tray()

    def hide_to_tray(self) -> None:
        self.module_widget._save_scratchpad_now()
        self.hide()

    def toggle_visibility(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide_to_tray()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def quit_app(self) -> None:
        self.module_widget._save_scratchpad_now()
        self.module_widget._save_hud_pos()
        if hasattr(self, "_hotkey_listener") and self._hotkey_listener:
            self._hotkey_listener.stop()
        if self.module_widget.hud:
            self.module_widget.hud.close()
        self.tray.stop()
        self._qt_app.quit()

    def mainloop(self) -> None:
        """Compatibility launcher method for run.py."""
        sys.exit(self._qt_app.exec())
