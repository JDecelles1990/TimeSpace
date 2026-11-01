"""Floating Mini HUD: compact, draggable, always-on-top PySide6 desktop widget for IT Helpdesk / multi-monitor setups."""
from typing import Optional, Callable
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QVBoxLayout
from src.config import COLORS, UI_DIMENSIONS


class FloatingMiniHUD(QWidget):
    def __init__(
        self,
        master: Optional[QWidget] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_bring_main_to_front: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        initial_x: int = 120,
        initial_y: int = 80,
        opacity: float = 0.90,
    ):
        super().__init__(None)
        self.on_toggle_pause = on_toggle_pause
        self.on_bring_main_to_front = on_bring_main_to_front
        self.on_close_cb = on_close
        self._drag_pos: Optional[QPoint] = None

        self.setWindowTitle("Mini HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.set_hud_opacity(opacity)

        self.width_px: int = UI_DIMENSIONS["hud_width"]
        self.height_px: int = UI_DIMENSIONS["hud_height"]
        self.setFixedSize(self.width_px, self.height_px)
        self.move(initial_x, initial_y)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self._set_border_color(COLORS["accent"])
        row = QHBoxLayout(self.card)
        row.setContentsMargins(8, 3, 6, 3)
        row.setSpacing(6)

        self.lbl_icon = QLabel("⏳")
        self.lbl_icon.setStyleSheet("border: none; font-size: 13px;")
        row.addWidget(self.lbl_icon)

        self.lbl_title = QLabel("All Quiet")
        self.lbl_title.setStyleSheet(f"border: none; font-weight: bold; color: {COLORS['text']}; font-size: 11px;")
        row.addWidget(self.lbl_title, 1)

        self.lbl_countdown = QLabel("--:--")
        self.lbl_countdown.setStyleSheet(f"border: none; font-weight: bold; color: {COLORS['accent']}; font-size: 12px;")
        row.addWidget(self.lbl_countdown)

        self.btn_pause = QPushButton("⏯")
        self.btn_pause.setFixedSize(22, 22)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['surface_light']}; color: {COLORS['text']}; "
            f"border: none; border-radius: 3px; padding: 0px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent']}; color: #ffffff; }}"
        )
        self.btn_pause.clicked.connect(self._handle_pause)
        row.addWidget(self.btn_pause)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {COLORS['text_muted']}; "
            f"border: none; border-radius: 3px; padding: 0px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_danger']}; color: #ffffff; }}"
        )
        btn_close.clicked.connect(self.close_hud)
        row.addWidget(btn_close)

        outer.addWidget(self.card)

    def _set_border_color(self, color: str) -> None:
        self.card.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_dark']}; border: 1.5px solid {color}; border-radius: 5px; }}"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, _event) -> None:
        if self.on_bring_main_to_front:
            self.on_bring_main_to_front()

    def _handle_pause(self) -> None:
        if self.on_toggle_pause:
            self.on_toggle_pause()

    def update_status(self, name: str, remaining_sec: float, is_paused: bool = False, is_sla: bool = False) -> None:
        """Update live status display and adapt colors based on SLA urgency."""
        if is_paused:
            rem = int(remaining_sec)
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            self.lbl_countdown.setText(f"⏸ {h:02d}:{m:02d}:{s:02d}")
            self.lbl_countdown.setStyleSheet(f"border: none; font-weight: bold; color: {COLORS['text_muted']}; font-size: 12px;")
            self.lbl_icon.setText("⏸️")
            self._set_border_color("#52525b")
        elif remaining_sec <= 0:
            self.lbl_countdown.setText("🚨 00:00")
            self.lbl_countdown.setStyleSheet(f"border: none; font-weight: bold; color: {COLORS['accent_danger']}; font-size: 12px;")
            self.lbl_icon.setText("🚨")
            self._set_border_color(COLORS["accent_danger"])
        else:
            rem = int(remaining_sec)
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

            if remaining_sec < 60:
                color = COLORS["accent_danger"]
                icon = "🚨" if is_sla else "⏱️"
            elif remaining_sec < 300:
                color = COLORS["accent_warning"]
                icon = "⚡" if is_sla else "⏳"
            else:
                color = "#818cf8"
                icon = "🎫" if is_sla else "⏳"

            self.lbl_countdown.setText(time_str)
            self.lbl_countdown.setStyleSheet(f"border: none; font-weight: bold; color: {color}; font-size: 12px;")
            self.lbl_icon.setText(icon)
            self._set_border_color(color)

        display_name = name if len(name) <= 16 else name[:14] + ".."
        self.lbl_title.setText(display_name)

    def set_idle(self) -> None:
        self.lbl_icon.setText("✅")
        self.lbl_title.setText("All Quiet")
        self.lbl_countdown.setText("00:00")
        self.lbl_countdown.setStyleSheet(f"border: none; font-weight: bold; color: {COLORS['text_muted']}; font-size: 12px;")
        self._set_border_color(COLORS["surface_light"])

    def set_hud_opacity(self, opacity: float) -> None:
        """Update HUD window opacity (clamped to 0.60..1.00)."""
        self.setWindowOpacity(max(0.60, min(1.0, float(opacity))))

    def close_hud(self) -> None:
        self.hide()
        if self.on_close_cb:
            self.on_close_cb()
