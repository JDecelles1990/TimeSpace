"""Radial Circular Progress Ring for countdown visualization drawn with PySide6 QPainter."""
import math
from typing import Optional
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget
from src.config import COLORS, FONT_FAMILY, UI_DIMENSIONS


class CircularProgressRing(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        size: int = UI_DIMENSIONS["ring_size"],
        ring_width: int = UI_DIMENSIONS["ring_width"],
    ):
        super().__init__(parent)
        self.size_px = size
        self.ring_width = ring_width
        self.setFixedSize(self.size_px, self.size_px)

        self._ratio: float = 0.0
        self._arc_color: str = COLORS["surface_light"]
        self._time_text: str = "--:--"
        self._title_text: str = "All Quiet"
        self._badge_text: str = ""
        self._badge_color: str = COLORS["accent_warning"]

    def update_countdown(
        self,
        remaining_sec: float,
        total_sec: float,
        title: str = "",
        is_repeating: bool = False,
        is_paused: bool = False,
    ) -> None:
        """Update the arc progress and central time readout."""
        remaining_sec = max(0.0, remaining_sec)
        total_sec = max(1.0, total_sec)

        self._ratio = min(1.0, remaining_sec / total_sec)

        if is_paused:
            self._arc_color = COLORS["surface_light"]
        elif self._ratio < 0.10:
            self._arc_color = COLORS["accent_danger"]
        elif self._ratio < 0.25:
            self._arc_color = COLORS["accent_warning"]
        else:
            self._arc_color = COLORS["accent"]

        total_int = int(math.ceil(remaining_sec))
        m, s = divmod(total_int, 60)
        h, m = divmod(m, 60)
        self._time_text = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

        truncated = title if len(title) <= 14 else title[:12] + "…"
        self._title_text = truncated or "Countdown"

        if is_paused:
            self._badge_text = "⏸ PAUSED"
            self._badge_color = COLORS["accent_warning"]
        elif is_repeating:
            self._badge_text = "🔁 Repeat"
            self._badge_color = COLORS["accent_success"]
        else:
            self._badge_text = ""

        self.update()

    def set_idle(self) -> None:
        """Reset ring to calm waiting state."""
        self._ratio = 0.0
        self._arc_color = COLORS["surface_light"]
        self._time_text = "--:--"
        self._title_text = "All Quiet"
        self._badge_text = ""
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = self.ring_width + 4
        rect = QRectF(pad, pad, self.size_px - 2 * pad, self.size_px - 2 * pad)

        # Track circle
        track_pen = QPen(QColor(COLORS["surface"]), self.ring_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Progress arc (clockwise from 12 o'clock = 90 * 16)
        if self._ratio > 0.001:
            arc_pen = QPen(QColor(self._arc_color), self.ring_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            start_angle = 90 * 16
            span_angle = -int(self._ratio * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # Time readout
        painter.setPen(QColor(COLORS["text"]))
        time_font = QFont(FONT_FAMILY, max(12, int(self.size_px * 0.13)), QFont.Weight.Bold)
        painter.setFont(time_font)
        time_rect = QRectF(0, self.size_px * 0.26, self.size_px, 28)
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, self._time_text)

        # Title readout
        painter.setPen(QColor(COLORS["text_muted"]))
        title_font = QFont(FONT_FAMILY, 8)
        painter.setFont(title_font)
        title_rect = QRectF(8, self.size_px * 0.52, self.size_px - 16, 18)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self._title_text)

        # Badge readout
        if self._badge_text:
            painter.setPen(QColor(self._badge_color))
            badge_font = QFont(FONT_FAMILY, 7, QFont.Weight.Bold)
            painter.setFont(badge_font)
            badge_rect = QRectF(8, self.size_px * 0.67, self.size_px - 16, 16)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._badge_text)
