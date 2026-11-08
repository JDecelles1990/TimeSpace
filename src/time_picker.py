"""PySide6 Big-Buttons 24h Time Picker widget with responsive grid layout for Appointment Details."""
from typing import Tuple, Optional, Callable, Dict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from src.config import COLORS


class BigButtonsTimePicker(QWidget):
    """Compact, responsive 24-hour time selector with digital readout, steppers, and quick presets."""

    timeChanged = Signal(int, int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_hour: int = 14,
        initial_minute: int = 0,
        on_change: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__(parent)
        self.hour: int = initial_hour % 24
        self.minute: int = (initial_minute // 15) * 15
        self._legacy_on_change = on_change
        self.min_btns: Dict[int, QPushButton] = {}
        self.setMinimumWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        # Row 1: Compact Digital Display + Hour Steppers + Minute Presets in a responsive grid
        top_grid = QGridLayout()
        top_grid.setContentsMargins(0, 0, 0, 0)
        top_grid.setSpacing(3)

        disp_frame = QFrame()
        disp_frame.setMinimumWidth(0)
        disp_frame.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 5px;"
        )
        disp_layout = QHBoxLayout(disp_frame)
        disp_layout.setContentsMargins(6, 2, 6, 2)

        self.lbl_time = QLabel("14:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet(
            f"color: {COLORS['accent']}; font-family: 'Consolas', monospace; font-size: 16px; font-weight: bold; border: none;"
        )
        disp_layout.addWidget(self.lbl_time)
        top_grid.addWidget(disp_frame, 0, 0, 1, 2)

        btn_h_down = QPushButton("−1h")
        btn_h_up = QPushButton("+1h")
        for b, delta in ((btn_h_down, -1), (btn_h_up, 1)):
            b.setMinimumWidth(0)
            b.setFixedHeight(24)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setStyleSheet("padding: 1px 4px; font-size: 11px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, d=delta: self._step_hour(d))
        top_grid.addWidget(btn_h_down, 0, 2)
        top_grid.addWidget(btn_h_up, 0, 3)

        for col_idx, m_val in enumerate((0, 15, 30, 45)):
            btn_m = QPushButton(f":{m_val:02d}")
            btn_m.setMinimumWidth(0)
            btn_m.setFixedHeight(24)
            btn_m.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn_m.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_m.clicked.connect(lambda _checked=False, mv=m_val: self._set_minute(mv))
            top_grid.addWidget(btn_m, 1, col_idx)
            self.min_btns[m_val] = btn_m

        for c in range(4):
            top_grid.setColumnStretch(c, 1)
        layout.addLayout(top_grid)

        # Row 2: Responsive Quick Hour Presets
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(3)

        for label, h_val in (("09:00", 9), ("12:00", 12), ("14:00", 14), ("17:00", 17), ("18:00", 18)):
            btn_p = QPushButton(label)
            btn_p.setMinimumWidth(0)
            btn_p.setFixedHeight(22)
            btn_p.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
                f"font-size: 10px; padding: 1px 3px; border-radius: 3px;"
            )
            btn_p.clicked.connect(lambda _checked=False, hv=h_val: self._set_preset(hv, 0))
            preset_row.addWidget(btn_p, 1)

        layout.addLayout(preset_row)
        self._refresh_display()

    def _step_hour(self, delta: int) -> None:
        self.hour = (self.hour + delta) % 24
        self._refresh_display()

    def _set_minute(self, val: int) -> None:
        self.minute = val % 60
        self._refresh_display()

    def _set_preset(self, h: int, m: int) -> None:
        self.hour = h % 24
        self.minute = m % 60
        self._refresh_display()

    def set_time(self, h: int, m: int) -> None:
        """Programmatically set the 24-hour time (used when inline-editing an active RDV)."""
        self.hour = h % 24
        self.minute = m % 60
        self._refresh_display()

    def _refresh_display(self) -> None:
        self.lbl_time.setText(f"{self.hour:02d}:{self.minute:02d}")
        for m_val, btn in self.min_btns.items():
            if m_val == self.minute:
                btn.setStyleSheet(
                    f"background-color: {COLORS['accent']}; color: #ffffff; font-weight: bold; "
                    f"font-size: 11px; padding: 1px 4px; border: 1px solid {COLORS['accent']}; border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
                    f"font-size: 11px; padding: 1px 4px; border: 1px solid {COLORS['border']}; border-radius: 4px;"
                )
        self.timeChanged.emit(self.hour, self.minute)
        if self._legacy_on_change:
            self._legacy_on_change(self.hour, self.minute)

    def get_time(self) -> Tuple[int, int]:
        return self.hour, self.minute
