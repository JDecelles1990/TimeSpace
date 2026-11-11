"""Compact borderless bottom-right Alarm Notification Popup built with PySide6."""
from typing import Callable, Optional, List
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
)
from src.config import COLORS, UI_DIMENSIONS, SNOOZE_OPTIONS, AppConfig
from src.notifications import show_toast, open_attachment_link, normalize_link_target


class AlarmDialog(QDialog):
    """Compact always-on-top notification card anchored at the bottom-right of the screen."""

    _active_popups: List["AlarmDialog"] = []

    def __init__(
        self,
        master: Optional[QWidget] = None,
        title_text: str = "Alarm",
        reminder_name: str = "Reminder",
        on_dismiss: Optional[Callable[[], None]] = None,
        on_snooze: Optional[Callable[[int], None]] = None,
        on_open_link: Optional[Callable[[], None]] = None,
        category: str = "",
        url: str = "",
        note: str = "",
        config: Optional[AppConfig] = None,
        meeting_mode: bool = False,
    ):
        super().__init__(master)
        self.on_dismiss = on_dismiss
        self.on_snooze = on_snooze
        self.on_open_link = on_open_link
        self.category = category
        self.url: str = (url or "").strip()
        self.note: str = (note or "").strip()
        self.config: AppConfig = config or AppConfig()
        self.meeting_mode: bool = meeting_mode
        self.default_snooze: int = self.config.default_snooze_minutes
        self._drag_pos: Optional[QPoint] = None

        self.setWindowTitle("⏰ Alarm Alert!")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        opacity = max(0.60, min(1.0, self.config.overlay_opacity / 100.0))
        self.setWindowOpacity(opacity)

        has_rich_content = bool(self.note or self.url)
        self.width_px: int = UI_DIMENSIONS["toast_width"]
        self.height_px: int = (
            UI_DIMENSIONS["toast_height_rich"] if has_rich_content else UI_DIMENSIONS["toast_height"]
        )
        self.setFixedSize(self.width_px, self.height_px)

        AlarmDialog._active_popups = [p for p in AlarmDialog._active_popups if p.isVisible()]
        preceding_popups = list(AlarmDialog._active_popups)
        AlarmDialog._active_popups.append(self)

        # Native Windows Action Center Toast
        badge_prefix = f"[{category}] " if category and category != "General" else ""
        toast_body = f"{reminder_name} — {self.note}" if self.note else f"Time is up! {reminder_name}"
        show_toast(f"{badge_prefix}{title_text}", toast_body)

        self._build_ui(title_text, reminder_name)
        self._position_bottom_right(preceding_popups)
        self.show()
        self.raise_()

    @classmethod
    def set_active_popups_opacity(cls, opacity: float) -> None:
        """Live-update opacity across all currently visible bottom-right popup cards."""
        clamped = max(0.60, min(1.0, float(opacity)))
        cls._active_popups = [p for p in cls._active_popups if p.isVisible()]
        for popup in cls._active_popups:
            popup.setWindowOpacity(clamped)

    def _position_bottom_right(self, preceding_popups: Optional[List["AlarmDialog"]] = None) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            stack_offset = sum(p.height_px + 10 for p in (preceding_popups or []))
            x = avail.right() - self.width_px - UI_DIMENSIONS["toast_margin_right"]
            y = avail.bottom() - self.height_px - stack_offset - 12
            self.move(max(10, x), max(10, y))

    def _build_ui(self, title_text: str, reminder_name: str) -> None:
        is_sla = "SLA" in self.category or "SLA" in title_text
        accent_border = COLORS["accent_danger"] if is_sla else COLORS["accent_warning"]

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_dark']}; "
            f"border: 1.5px solid {accent_border}; border-radius: 6px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        # Top row: Badge + Close
        top_row = QHBoxLayout()
        cat_label = f" • {self.category.upper()}" if self.category and self.category != "General" else ""
        lbl_badge = QLabel(f"⏰ ALARM{cat_label}")
        lbl_badge.setStyleSheet(
            f"background-color: {COLORS['surface']}; color: {accent_border}; "
            f"font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px; border: none;"
        )
        top_row.addWidget(lbl_badge)

        if self.meeting_mode:
            lbl_muted = QLabel("🤫 MUTED")
            lbl_muted.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['glow_cyan']}; "
                f"font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px; border: none;"
            )
            lbl_muted.setToolTip("Meeting Mode is active: audio chime was suppressed.")
            top_row.addWidget(lbl_muted)

        top_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_muted']}; border: none; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_danger']}; color: #ffffff; border-radius: 3px; }}"
        )
        btn_close.clicked.connect(self._handle_dismiss)
        top_row.addWidget(btn_close)
        card_layout.addLayout(top_row)

        # Title & Subtitle
        lbl_title = QLabel(title_text)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold; border: none;")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(reminder_name)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")
        card_layout.addWidget(lbl_desc)

        if self.note:
            elided_note = self.note if len(self.note) <= 92 else self.note[:89] + "..."
            lbl_note = QLabel(f"📝 {elided_note}")
            lbl_note.setWordWrap(True)
            lbl_note.setToolTip(self.note)
            lbl_note.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['text']}; "
                f"font-size: 11px; padding: 3px 6px; border-radius: 3px; border: none;"
            )
            card_layout.addWidget(lbl_note)

        card_layout.addStretch()

        # Action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(5)
        btn_dismiss = QPushButton("✓ Dismiss")
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_danger']}; color: #ffffff; "
            f"font-weight: bold; padding: 4px 10px; border-radius: 4px; border: none; }}"
            f"QPushButton:hover {{ background-color: #dc2626; }}"
        )
        btn_dismiss.clicked.connect(self._handle_dismiss)
        action_row.addWidget(btn_dismiss)

        if self.url:
            btn_open = QPushButton("🔗 Open Link")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setToolTip(normalize_link_target(self.url))
            btn_open.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['accent_success']}; color: #ffffff; "
                f"font-weight: bold; padding: 4px 10px; border-radius: 4px; border: none; }}"
                f"QPushButton:hover {{ background-color: #059669; }}"
            )
            btn_open.clicked.connect(self._handle_open_link)
            action_row.addWidget(btn_open)

        action_row.addStretch()

        self.combo_snooze = QComboBox()
        for opt in SNOOZE_OPTIONS:
            self.combo_snooze.addItem(f"{opt}m", opt)
        idx = self.combo_snooze.findData(self.default_snooze)
        if idx >= 0:
            self.combo_snooze.setCurrentIndex(idx)
        self.combo_snooze.setFixedWidth(56)
        action_row.addWidget(self.combo_snooze)

        btn_snooze = QPushButton("💤 Snooze")
        btn_snooze.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_snooze.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent']}; color: #ffffff; "
            f"font-weight: bold; padding: 4px 9px; border-radius: 4px; border: none; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}"
        )
        btn_snooze.clicked.connect(self._handle_snooze)
        action_row.addWidget(btn_snooze)

        card_layout.addLayout(action_row)
        root_layout.addWidget(card)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _cleanup(self) -> None:
        if self in AlarmDialog._active_popups:
            AlarmDialog._active_popups.remove(self)
        self.close()
        self.deleteLater()

    def _handle_dismiss(self) -> None:
        self._cleanup()
        if self.on_dismiss:
            self.on_dismiss()

    def _handle_open_link(self) -> None:
        open_attachment_link(self.url)
        self._cleanup()
        if self.on_open_link:
            self.on_open_link()
        elif self.on_dismiss:
            self.on_dismiss()

    def _handle_snooze(self) -> None:
        mins = int(self.combo_snooze.currentData() or self.default_snooze)
        self._cleanup()
        if self.on_snooze:
            self.on_snooze(mins)
