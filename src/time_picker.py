"""Ergonomic Big-Buttons Time Picker Widget built with PySide6."""
from typing import Tuple, Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from src.config import COLORS


class BigButtonsTimePicker(QWidget):
    timeChanged = Signal(int, int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_hour: int = 14,
        initial_minute: int = 0,
        on_change: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__(parent)
        self.hour: int = initial_hour
        self.minute: int = initial_minute
        if on_change:
            self.timeChanged.connect(on_change)

        self._build_ui()
        self._update_display()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Stepper row
        stepper_row = QHBoxLayout()
        stepper_row.setSpacing(4)

        btn_h_minus = QPushButton("−")
        btn_h_minus.setFixedSize(26, 26)
        btn_h_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_h_minus.clicked.connect(lambda: self._adjust_hour(-1))

        self.lbl_hour = QLabel("14")
        self.lbl_hour.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hour.setFixedWidth(32)
        self.lbl_hour.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['accent']}; "
            f"background-color: {COLORS['surface_light']}; border-radius: 4px; padding: 2px;"
        )

        btn_h_plus = QPushButton("+")
        btn_h_plus.setFixedSize(26, 26)
        btn_h_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_h_plus.clicked.connect(lambda: self._adjust_hour(1))

        lbl_colon = QLabel(":")
        lbl_colon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_colon.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text_muted']};")

        btn_m_minus = QPushButton("−")
        btn_m_minus.setFixedSize(26, 26)
        btn_m_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_m_minus.clicked.connect(lambda: self._adjust_minute(-5))

        self.lbl_minute = QLabel("00")
        self.lbl_minute.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_minute.setFixedWidth(32)
        self.lbl_minute.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['accent']}; "
            f"background-color: {COLORS['surface_light']}; border-radius: 4px; padding: 2px;"
        )

        btn_m_plus = QPushButton("+")
        btn_m_plus.setFixedSize(26, 26)
        btn_m_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_m_plus.clicked.connect(lambda: self._adjust_minute(5))

        stepper_row.addStretch()
        stepper_row.addWidget(btn_h_minus)
        stepper_row.addWidget(self.lbl_hour)
        stepper_row.addWidget(btn_h_plus)
        stepper_row.addWidget(lbl_colon)
        stepper_row.addWidget(btn_m_minus)
        stepper_row.addWidget(self.lbl_minute)
        stepper_row.addWidget(btn_m_plus)
        stepper_row.addStretch()
        layout.addLayout(stepper_row)

        # Quick Minute Chips (:00, :15, :30, :45)
        chip_row = QHBoxLayout()
        chip_row.setSpacing(4)
        for min_val in [0, 15, 30, 45]:
            btn = QPushButton(f":{min_val:02d}")
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, m=min_val: self.set_minute(m))
            chip_row.addWidget(btn)
        layout.addLayout(chip_row)

        # Quick Time Presets
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for label, h, m in [("09:00", 9, 0), ("12:00", 12, 0), ("15:00", 15, 0), ("18:00", 18, 0)]:
            btn = QPushButton(label)
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, hh=h, mm=m: self.set_time(hh, mm))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

    def _adjust_hour(self, delta: int) -> None:
        self.hour = (self.hour + delta) % 24
        self._update_display()

    def _adjust_minute(self, delta: int) -> None:
        self.minute = (self.minute + delta) % 60
        self._update_display()

    def set_minute(self, m: int) -> None:
        self.minute = m % 60
        self._update_display()

    def set_time(self, h: int, m: int) -> None:
        self.hour = h % 24
        self.minute = m % 60
        self._update_display()

    def _update_display(self) -> None:
        self.lbl_hour.setText(f"{self.hour:02d}")
        self.lbl_minute.setText(f"{self.minute:02d}")
        self.timeChanged.emit(self.hour, self.minute)

    def get_time(self) -> Tuple[int, int]:
        return self.hour, self.minute
