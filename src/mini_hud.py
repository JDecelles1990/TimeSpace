"""Floating Mini HUD: glowing Cyber-Aurora Neon Glass pill and animated upcoming-alarms popover."""
from dataclasses import dataclass
import html
import math
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import COLORS, FONT_FAMILY, UI_DIMENSIONS


@dataclass
class HudAlarmEntry:
    """Typed snapshot of a scheduled timer or RDV rendered inside HudUpcomingPopover."""

    id: str
    kind: str
    name: str
    remaining_sec: float
    ring_time_str: str
    is_paused: bool = False
    is_repeating: bool = False
    category: str = "General"
    note: str = ""


def _alpha_color(hex_color: str, alpha: int) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def _format_hud_countdown(seconds: float) -> str:
    """Format non-negative seconds as HH:MM:SS (>=1h) or MM:SS."""
    rem = max(0, int(seconds))
    m, s = divmod(rem, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def _truncate_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def _urgency_color_for_entry(entry: HudAlarmEntry) -> str:
    if entry.is_paused:
        return COLORS["glow_gold"]
    if entry.remaining_sec < 60:
        return COLORS["glow_magenta"]
    if entry.remaining_sec < 300:
        return COLORS["glow_gold"]
    if entry.kind == "rendez-vous":
        return COLORS["glow_cyan"]
    return COLORS["glow_green"]


class HudUpcomingPopover(QWidget):
    """Frameless translucent Cyber-Aurora popover showing queued alarms with animated glow & auto-dismiss."""

    _GLOW_PAD = 12
    _CARD_WIDTH = 318
    _DISPLAY_MS = 4500
    _LEAVE_GRACE_MS = 1500
    _MAX_ROWS = 6

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._target_opacity: float = 0.94
        self._hiding: bool = False
        self._hovered: bool = False
        self._anchor_pos: QPoint = QPoint(0, 0)
        self._glide_dir: int = 1
        self._shimmer_pos: float = -1.0
        self._pulse_phase: float = 0.0
        self._dismiss_ratio: float = 1.0
        self._entries: List[HudAlarmEntry] = []
        self._primary_id: Optional[str] = None
        self._display_duration_ms: int = self._DISPLAY_MS
        self._remaining_ms: int = self._DISPLAY_MS

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            self._GLOW_PAD + 14,
            self._GLOW_PAD + 10,
            self._GLOW_PAD + 12,
            self._GLOW_PAD + 12,
        )
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(6)

        self._lbl_header = QLabel("✨ UPCOMING ALARMS")
        self._lbl_header.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._lbl_header.setStyleSheet(
            f"background: transparent; border: none; color: {COLORS['glow_cyan']}; "
            f"font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 10px; font-weight: 700;"
        )
        hdr.addWidget(self._lbl_header)
        hdr.addStretch(1)

        self._lbl_badge = QLabel("0 queued")
        self._lbl_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._lbl_badge.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['glow_specular']}; "
            f"border: 1px solid {COLORS['border_shine']}; border-radius: 7px; "
            f"padding: 1px 7px; font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 10px; font-weight: 600;"
        )
        hdr.addWidget(self._lbl_badge)
        layout.addLayout(hdr)

        self._lbl_body = QLabel(self)
        self._lbl_body.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._lbl_body.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_body.setWordWrap(True)
        self._lbl_body.setFixedWidth(self._CARD_WIDTH)
        self._lbl_body.setStyleSheet(
            f"background: transparent; border: none; color: {COLORS['text']}; "
            f"font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 11px;"
        )
        layout.addWidget(self._lbl_body)

        self._opacity_anim = QVariantAnimation(self)
        self._opacity_anim.valueChanged.connect(self._on_opacity_step)
        self._opacity_anim.finished.connect(self._on_opacity_finished)

        self._glide_anim = QVariantAnimation(self)
        self._glide_anim.setDuration(200)
        self._glide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._glide_anim.valueChanged.connect(self._on_glide_step)

        self._shimmer_anim = QVariantAnimation(self)
        self._shimmer_anim.setDuration(420)
        self._shimmer_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._shimmer_anim.setStartValue(-0.30)
        self._shimmer_anim.setEndValue(1.30)
        self._shimmer_anim.valueChanged.connect(self._on_shimmer_step)
        self._shimmer_anim.finished.connect(self._on_shimmer_finished)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(40)
        self._tick_timer.timeout.connect(self._on_tick)

        self.setWindowOpacity(0.0)
        self.hide()

    def _on_opacity_step(self, val) -> None:
        self.setWindowOpacity(max(0.0, min(1.0, float(val))))

    def _on_opacity_finished(self) -> None:
        if self._hiding and self.windowOpacity() <= 0.02:
            self._hiding = False
            self._hovered = False
            self._tick_timer.stop()
            self.hide()

    def _on_glide_step(self, val) -> None:
        self.move(self._anchor_pos.x(), int(val))

    def _on_shimmer_step(self, val) -> None:
        self._shimmer_pos = float(val)
        self.update()

    def _on_shimmer_finished(self) -> None:
        self._shimmer_pos = -1.0
        self.update()

    def _on_tick(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.085) % (2.0 * math.pi)
        if not self._hiding and not self._hovered:
            self._remaining_ms = max(0, self._remaining_ms - self._tick_timer.interval())
            denom = max(1, self._display_duration_ms)
            self._dismiss_ratio = max(0.0, min(1.0, self._remaining_ms / denom))
            if self._remaining_ms <= 0:
                self.hide_popover()
        self.update()

    def _build_entries_html(self, entries: List[HudAlarmEntry], primary_id: Optional[str]) -> Tuple[str, str, str]:
        others = [e for e in entries if e.id != primary_id] if primary_id else list(entries)

        if others:
            hdr_text = "✨ OTHER UPCOMING ALARMS"
            badge_text = f"+{len(others)} more"
            rows: List[str] = []
            for idx, entry in enumerate(others[: self._MAX_ROWS]):
                icon = "⏳" if entry.kind == "timer" else "📅"
                pause_tag = "⏸ " if entry.is_paused else ""
                rep_tag = " 🔁" if entry.is_repeating else ""
                cd_color = _urgency_color_for_entry(entry)
                cd_text = _format_hud_countdown(entry.remaining_sec)
                safe_name = html.escape(_truncate_text(entry.name, 30))
                safe_ring = html.escape(entry.ring_time_str)
                note_part = ""
                if entry.note:
                    note_part = f" · 📝 {html.escape(_truncate_text(entry.note.strip(), 28))}"

                sep_css = f"border-top: 1px solid {COLORS['border']}; padding-top: 5px; margin-top: 5px;" if idx > 0 else ""
                rows.append(
                    f"<div style='{sep_css}'>"
                    f"<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                    f"<td style='color:{COLORS['glow_specular']}; font-weight:600; font-size:11px;'>"
                    f"{icon} {pause_tag}{safe_name}{rep_tag}</td>"
                    f"<td align='right' style='color:{cd_color}; font-weight:700; font-size:11px; white-space:nowrap;'>"
                    f"{cd_text}</td>"
                    f"</tr></table>"
                    f"<div style='color:{COLORS['text_muted']}; font-size:10px; margin-top:1px;'>"
                    f"🔔 {safe_ring}{note_part}</div>"
                    f"</div>"
                )
            if len(others) > self._MAX_ROWS:
                extra = len(others) - self._MAX_ROWS
                rows.append(
                    f"<div style='color:{COLORS['glow_violet_light']}; font-size:10px; font-weight:600; margin-top:6px;'>"
                    f"+{extra} more queued in TimeSpace…</div>"
                )
            return hdr_text, badge_text, "".join(rows)

        if entries:
            active = entries[0]
            hdr_text = "✨ ACTIVE ALARM"
            badge_text = "Only 1"
            icon = "⏳" if active.kind == "timer" else "📅"
            pause_tag = "⏸ PAUSED · " if active.is_paused else ""
            rep_tag = " 🔁" if active.is_repeating else ""
            cd_color = _urgency_color_for_entry(active)
            cd_text = _format_hud_countdown(active.remaining_sec)
            safe_name = html.escape(active.name)
            safe_ring = html.escape(active.ring_time_str)
            note_html = (
                f"<div style='color:{COLORS['text_muted']}; font-size:10px; margin-top:2px;'>"
                f"📝 {html.escape(_truncate_text(active.note.strip(), 46))}</div>"
                if active.note
                else ""
            )
            body_html = (
                f"<div>"
                f"<div style='color:{COLORS['glow_specular']}; font-weight:700; font-size:11px;'>"
                f"{icon} {safe_name}{rep_tag}</div>"
                f"<div style='color:{cd_color}; font-weight:700; font-size:11px; margin-top:2px;'>"
                f"{pause_tag}{cd_text} · <span style='color:{COLORS['text_muted']}; font-weight:400;'>🔔 {safe_ring}</span></div>"
                f"{note_html}"
                f"<div style='border-top: 1px solid {COLORS['border']}; margin-top:6px; padding-top:4px; "
                f"color:{COLORS['text_muted']}; font-size:10px;'>No other upcoming alarms queued.</div>"
                f"</div>"
            )
            return hdr_text, badge_text, body_html

        return (
            "✅ ALL QUIET",
            "0 active",
            f"<div style='color:{COLORS['text_muted']}; font-size:11px;'>"
            f"No upcoming timers or appointments scheduled.</div>",
        )

    def _populate_content(self, entries: List[HudAlarmEntry], primary_id: Optional[str]) -> None:
        self._entries = list(entries)
        self._primary_id = primary_id
        hdr_text, badge_text, body_html = self._build_entries_html(self._entries, self._primary_id)
        self._lbl_header.setText(hdr_text)
        self._lbl_badge.setText(badge_text)
        self._lbl_body.setText(body_html)
        self._lbl_body.adjustSize()
        if self.layout() is not None:
            self.layout().activate()
        self.resize(self.sizeHint())

    def _compute_anchor(self, hud_rect: QRect) -> Tuple[QPoint, int]:
        w, h = self.width(), self.height()
        pad = self._GLOW_PAD
        # Align left edge of popover card with HUD card
        x = hud_rect.left()
        y_below = hud_rect.bottom() - pad + 4
        y_above = hud_rect.top() - h + pad - 4

        screen = QGuiApplication.screenAt(hud_rect.center()) or QGuiApplication.primaryScreen()
        glide_dir = 1
        y = y_below
        if screen is not None:
            avail = screen.availableGeometry()
            if y_below + h - pad > avail.bottom() and y_above + pad >= avail.top():
                y = y_above
                glide_dir = -1
            x = max(avail.left() - pad + 4, min(x, avail.right() - w + pad - 4))
            y = max(avail.top() - pad + 4, min(y, avail.bottom() - h + pad - 4))
        return QPoint(x, y), glide_dir

    def show_popover(
        self,
        hud_rect: QRect,
        entries: List[HudAlarmEntry],
        primary_id: Optional[str],
        duration_ms: int = _DISPLAY_MS,
    ) -> None:
        """Display the glowing upcoming-alarms popover anchored near *hud_rect*."""
        self._display_duration_ms = max(1000, int(duration_ms))
        self._remaining_ms = self._display_duration_ms
        self._dismiss_ratio = 1.0
        self._hiding = False
        self._hovered = False

        self._populate_content(entries, primary_id)
        self._anchor_pos, self._glide_dir = self._compute_anchor(hud_rect)

        self._opacity_anim.stop()
        self._glide_anim.stop()
        self._shimmer_anim.stop()

        start_y = self._anchor_pos.y() - (8 * self._glide_dir)
        self.move(self._anchor_pos.x(), start_y)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_anim.setDuration(200)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(self._target_opacity)
        self._opacity_anim.start()

        self._glide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._glide_anim.setStartValue(start_y)
        self._glide_anim.setEndValue(self._anchor_pos.y())
        self._glide_anim.start()

        self._shimmer_anim.start()
        self._tick_timer.start()

    def update_entries(
        self,
        entries: List[HudAlarmEntry],
        primary_id: Optional[str],
        hud_rect: Optional[QRect] = None,
    ) -> None:
        """Refresh queued alarm rows/countdowns live without resetting the dismiss timer."""
        if not self.isVisible() or self._hiding:
            return
        old_size = self.size()
        self._populate_content(entries, primary_id)
        if hud_rect is not None:
            self._anchor_pos, self._glide_dir = self._compute_anchor(hud_rect)
            if self._glide_anim.state() != self._glide_anim.State.Running:
                self.move(self._anchor_pos)
        elif self.size() != old_size:
            self.update()

    def reposition(self, hud_rect: QRect) -> None:
        """Keep the open popover anchored while the user drags the HUD."""
        if not self.isVisible():
            return
        self._anchor_pos, self._glide_dir = self._compute_anchor(hud_rect)
        if self._glide_anim.state() != self._glide_anim.State.Running:
            self.move(self._anchor_pos)

    def set_target_opacity(self, opacity: float) -> None:
        self._target_opacity = max(0.60, min(1.0, float(opacity)))
        if (
            self.isVisible()
            and not self._hiding
            and self._opacity_anim.state() != self._opacity_anim.State.Running
        ):
            self.setWindowOpacity(self._target_opacity)

    def hide_popover(self, immediate: bool = False) -> None:
        """Fade and glide out smoothly (or hide immediately on HUD close/shutdown)."""
        if immediate:
            self._tick_timer.stop()
            self._opacity_anim.stop()
            self._glide_anim.stop()
            self._shimmer_anim.stop()
            self._hiding = False
            self._hovered = False
            self.setWindowOpacity(0.0)
            self.hide()
            return

        if not self.isVisible() or self._hiding:
            return

        self._hiding = True
        self._opacity_anim.stop()
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._opacity_anim.setDuration(180)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

        self._glide_anim.stop()
        self._glide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._glide_anim.setStartValue(self.y())
        self._glide_anim.setEndValue(self._anchor_pos.y() - (6 * self._glide_dir))
        self._glide_anim.start()

    def enterEvent(self, event) -> None:
        self._hovered = True
        if self._shimmer_anim.state() != self._shimmer_anim.State.Running:
            self._shimmer_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        if not self._hiding:
            self._remaining_ms = max(900, min(self._remaining_ms, self._LEAVE_GRACE_MS))
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = float(self._GLOW_PAD)
        card = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        radius = 10.0
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        hover_boost = 1.0 if self._hovered else 0.0

        c_start = COLORS["glow_cyan"]
        c_mid = COLORS["glow_violet_light"]
        c_end = COLORS["glow_green"]

        # 1. Breathing 4-layer outer neon aura
        for spread, base_a in ((8.5, 11), (5.8, 22), (3.2, 42), (1.4, 68)):
            glow_rect = card.adjusted(-spread, -spread, spread, spread)
            alpha = int(base_a + (10 * pulse) + (14 * hover_boost))
            glow_grad = QLinearGradient(glow_rect.topLeft(), glow_rect.bottomRight())
            glow_grad.setColorAt(0.0, _alpha_color(c_start, alpha))
            glow_grad.setColorAt(0.55, _alpha_color(c_mid, alpha))
            glow_grad.setColorAt(1.0, _alpha_color(c_end, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_grad)
            painter.drawRoundedRect(glow_rect, radius + spread * 0.5, radius + spread * 0.5)

        # 2. Cyber-Aurora dark translucent glass card fill + subtle internal aurora glow
        card_path = QPainterPath()
        card_path.addRoundedRect(card, radius, radius)

        bg_grad = QLinearGradient(card.topLeft(), card.bottomRight())
        bg_grad.setColorAt(0.0, _alpha_color(COLORS["surface_light"], 248))
        bg_grad.setColorAt(0.5, _alpha_color(COLORS["surface"], 246))
        bg_grad.setColorAt(1.0, _alpha_color(COLORS["bg_dark"], 250))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_grad)
        painter.drawPath(card_path)

        painter.save()
        painter.setClipPath(card_path)

        # Gentle drifting top-left aurora radial wash inside glass
        drift_x = card.left() + card.width() * (0.28 + 0.14 * math.sin(self._pulse_phase * 0.65))
        aurora_spot = QRadialGradient(QPointF(drift_x, card.top() + 14.0), card.width() * 0.65)
        aurora_spot.setColorAt(0.0, _alpha_color(COLORS["glow_cyan"], int(26 + 12 * pulse + 12 * hover_boost)))
        aurora_spot.setColorAt(0.55, _alpha_color(COLORS["glow_violet"], int(16 + 8 * pulse)))
        aurora_spot.setColorAt(1.0, _alpha_color(COLORS["bg_dark"], 0))
        painter.fillRect(card, aurora_spot)

        # Top specular glass sheen
        gloss_rect = QRectF(card.left(), card.top(), card.width(), min(32.0, card.height() * 0.35))
        gloss_grad = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], 26))
        gloss_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
        painter.fillRect(gloss_rect, gloss_grad)

        # Animated reveal / hover shimmer ribbon
        if -0.30 <= self._shimmer_pos <= 1.30:
            cx = card.left() + card.width() * self._shimmer_pos
            band_w = max(48.0, card.width() * 0.32)
            shimmer_grad = QLinearGradient(
                QPointF(cx - band_w, card.top()),
                QPointF(cx + band_w, card.bottom()),
            )
            shimmer_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], 0))
            shimmer_grad.setColorAt(0.5, _alpha_color(COLORS["glow_specular"], 40))
            shimmer_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
            painter.fillRect(card, shimmer_grad)

        # Left vertical glowing neon accent pill
        pill_x = card.left() + 5.0
        pill_top = card.top() + 8.0
        pill_bot = card.bottom() - 8.0
        if pill_bot > pill_top + 2:
            pill_grad = QLinearGradient(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))
            pill_grad.setColorAt(0.0, QColor(c_start))
            pill_grad.setColorAt(0.5, QColor(c_mid))
            pill_grad.setColorAt(1.0, QColor(c_end))
            pill_pen = QPen(pill_grad, 2.5)
            pill_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pill_pen)
            painter.drawLine(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))

        # Bottom depleting auto-dismiss neon bar
        bar_margin = 10.0
        bar_w = max(0.0, (card.width() - 2 * bar_margin) * self._dismiss_ratio)
        if bar_w > 1.5:
            bar_y = card.bottom() - 4.0
            bar_rect = QRectF(card.left() + bar_margin, bar_y, bar_w, 2.2)
            bar_grad = QLinearGradient(bar_rect.topLeft(), bar_rect.topRight())
            bar_grad.setColorAt(0.0, QColor(c_mid))
            bar_grad.setColorAt(0.5, QColor(c_start))
            bar_grad.setColorAt(1.0, QColor(c_end))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bar_grad)
            painter.drawRoundedRect(bar_rect, 1.1, 1.1)

        painter.restore()

        # 3. Animated iridescent neon border
        shift = 0.5 + 0.5 * math.cos(self._pulse_phase)
        b_p1 = QPointF(card.left() + card.width() * 0.25 * shift, card.top())
        b_p2 = QPointF(card.right() - card.width() * 0.25 * shift, card.bottom())
        border_grad = QLinearGradient(b_p1, b_p2)
        border_grad.setColorAt(0.0, QColor(c_start))
        border_grad.setColorAt(0.5, QColor(c_mid))
        border_grad.setColorAt(1.0, QColor(c_end))
        border_pen = QPen(border_grad, 1.65 if self._hovered else 1.4)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card, radius, radius)


class FloatingMiniHUD(QWidget):
    """Frameless translucent Cyber-Aurora floating desktop HUD with upcoming-alarms popover."""

    _GLOW_PAD = 10
    _CARD_RADIUS = 11.0

    def __init__(
        self,
        master: Optional[QWidget] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_bring_main_to_front: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        on_get_upcoming_items: Optional[Callable[[], List[HudAlarmEntry]]] = None,
        initial_x: int = 120,
        initial_y: int = 80,
        opacity: float = 0.90,
    ):
        super().__init__(None)
        self.on_toggle_pause = on_toggle_pause
        self.on_bring_main_to_front = on_bring_main_to_front
        self.on_close_cb = on_close
        self.on_get_upcoming_items = on_get_upcoming_items
        self._drag_pos: Optional[QPoint] = None

        self._target_opacity: float = max(0.60, min(1.0, float(opacity)))
        self._pulse_phase: float = 0.0
        self._hover_level: float = 0.0
        self._shimmer_pos: float = -1.0
        self._mouse_x_ratio: float = 0.5
        self._mode: str = "idle"
        self._progress_ratio: float = 0.0
        self._current_item_id: Optional[str] = None
        self._other_count: int = 0
        self._is_paused: bool = False
        self._has_active: bool = False

        self.setWindowTitle("Mini HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.width_px: int = UI_DIMENSIONS["hud_width"]
        self.height_px: int = UI_DIMENSIONS["hud_height"]
        self.setFixedSize(self.width_px, self.height_px)
        self._move_safely(initial_x, initial_y)

        self._upcoming_popover = HudUpcomingPopover()
        self._upcoming_popover.set_target_opacity(self._target_opacity)

        self._setup_animations()
        self._build_ui()
        self.set_hud_opacity(self._target_opacity)

    def _move_safely(self, x: int, y: int) -> None:
        screens = QGuiApplication.screens()
        if screens:
            center_pt = QPoint(x + self.width_px // 2, y + self.height_px // 2)
            visible_on_any = any(s.availableGeometry().contains(center_pt) for s in screens)
            if not visible_on_any:
                avail = (QGuiApplication.primaryScreen() or screens[0]).availableGeometry()
                x = max(avail.left(), min(x, avail.right() - self.width_px))
                y = max(avail.top(), min(y, avail.bottom() - self.height_px))
        self.move(x, y)

    def _setup_animations(self) -> None:
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._on_pulse_tick)

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_step)

        self._shimmer_anim = QVariantAnimation(self)
        self._shimmer_anim.setDuration(380)
        self._shimmer_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._shimmer_anim.setStartValue(-0.30)
        self._shimmer_anim.setEndValue(1.30)
        self._shimmer_anim.valueChanged.connect(self._on_shimmer_step)
        self._shimmer_anim.finished.connect(self._on_shimmer_finished)

        self._show_fade_anim = QVariantAnimation(self)
        self._show_fade_anim.setDuration(180)
        self._show_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._show_fade_anim.valueChanged.connect(self._on_show_fade_step)

    def _on_pulse_tick(self) -> None:
        speed = 0.14 if self._mode == "urgent" else (0.095 if self._mode == "warning" else 0.07)
        self._pulse_phase = (self._pulse_phase + speed) % (2.0 * math.pi)
        self.update()

    def _on_hover_step(self, val) -> None:
        self._hover_level = max(0.0, min(1.0, float(val)))
        self.update()

    def _on_shimmer_step(self, val) -> None:
        self._shimmer_pos = float(val)
        self.update()

    def _on_shimmer_finished(self) -> None:
        self._shimmer_pos = -1.0
        self.update()

    def _on_show_fade_step(self, val) -> None:
        self.setWindowOpacity(max(0.0, min(1.0, float(val))))

    def _build_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(
            self._GLOW_PAD + 12,
            self._GLOW_PAD + 5,
            self._GLOW_PAD + 8,
            self._GLOW_PAD + 7,
        )
        row.setSpacing(5)

        self.lbl_icon = QLabel("⏳")
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_icon.setStyleSheet("background: transparent; border: none; font-size: 13px;")
        row.addWidget(self.lbl_icon)

        self.lbl_title = QLabel("All Quiet")
        self.lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_title.setStyleSheet(
            f"background: transparent; border: none; font-weight: 600; "
            f"color: {COLORS['text']}; font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 11px;"
        )
        row.addWidget(self.lbl_title, 1)

        self.lbl_countdown = QLabel("--:--")
        self.lbl_countdown.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_countdown.setStyleSheet(
            f"background: transparent; border: none; font-weight: 700; "
            f"color: {COLORS['glow_cyan']}; font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 12px;"
        )
        row.addWidget(self.lbl_countdown)

        self.btn_upcoming = QPushButton("📋")
        self.btn_upcoming.setFixedSize(24, 24)
        self.btn_upcoming.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upcoming.setToolTip("Show upcoming alarms")
        self.btn_upcoming.clicked.connect(self._handle_show_upcoming)
        row.addWidget(self.btn_upcoming)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(24, 24)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setToolTip("Pause active alarm")
        self.btn_pause.clicked.connect(self._handle_pause)
        row.addWidget(self.btn_pause)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(20, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Hide Floating Mini HUD")
        self.btn_close.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {COLORS['text_muted']}; "
            f"border: 1px solid transparent; border-radius: 5px; padding: 0px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {COLORS['glow_magenta']}, stop:1 {COLORS['accent_danger']}); "
            f"color: {COLORS['glow_specular']}; border: 1px solid {COLORS['glow_specular']}; }}"
            f"QPushButton:pressed {{ background-color: {COLORS['accent_danger']}; }}"
        )
        self.btn_close.clicked.connect(self.close_hud)
        row.addWidget(self.btn_close)

        self._style_action_buttons()

    def _style_action_buttons(self) -> None:
        upcoming_open = self._upcoming_popover.isVisible()
        if upcoming_open:
            up_border = COLORS["glow_cyan"]
            up_top = COLORS["accent"]
            up_bot = COLORS["glow_violet"]
        elif self._other_count > 0:
            up_border = COLORS["glow_cyan"]
            up_top = COLORS["surface_light"]
            up_bot = COLORS["surface"]
        else:
            up_border = COLORS["border_shine"]
            up_top = COLORS["surface_light"]
            up_bot = COLORS["surface"]

        self.btn_upcoming.setStyleSheet(
            f"QPushButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {up_top}, stop:1 {up_bot}); color: {COLORS['glow_specular']}; "
            f"border: 1px solid {up_border}; border-radius: 5px; padding: 0px; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {COLORS['glow_cyan']}, stop:1 {COLORS['glow_violet']}); "
            f"color: {COLORS['glow_specular']}; border: 1px solid {COLORS['glow_specular']}; }}"
            f"QPushButton:pressed {{ background-color: {COLORS['glow_cyan']}; color: {COLORS['bg_dark']}; }}"
        )

        if self._other_count > 0:
            self.btn_upcoming.setToolTip(f"Show other upcoming alarms (+{self._other_count})")
        else:
            self.btn_upcoming.setToolTip("Show upcoming alarms")

        if not self._has_active:
            self.btn_pause.setText("⏸")
            self.btn_pause.setToolTip("No active alarm")
            self.btn_pause.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['surface']}; color: {COLORS['text_muted']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 5px; padding: 0px; font-size: 11px; }}"
                f"QPushButton:hover {{ border: 1px solid {COLORS['border_shine']}; color: {COLORS['text']}; }}"
            )
        elif self._is_paused:
            self.btn_pause.setText("▶")
            self.btn_pause.setToolTip("Resume paused alarm")
            self.btn_pause.setStyleSheet(
                f"QPushButton {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {COLORS['glow_green']}, stop:1 {COLORS['glow_cyan']}); "
                f"color: {COLORS['bg_dark']}; font-weight: bold; "
                f"border: 1px solid {COLORS['glow_specular']}; border-radius: 5px; padding: 0px; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {COLORS['glow_specular']}, stop:1 {COLORS['glow_green']}); "
                f"border: 1px solid {COLORS['glow_specular']}; }}"
                f"QPushButton:pressed {{ background-color: {COLORS['accent_success']}; }}"
            )
        else:
            self.btn_pause.setText("⏸")
            self.btn_pause.setToolTip("Pause active alarm")
            self.btn_pause.setStyleSheet(
                f"QPushButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                f"stop:0 {COLORS['surface_light']}, stop:1 {COLORS['surface']}); "
                f"color: {COLORS['glow_specular']}; "
                f"border: 1px solid {COLORS['border_shine']}; border-radius: 5px; padding: 0px; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {COLORS['glow_violet']}, stop:1 {COLORS['glow_cyan']}); "
                f"color: {COLORS['glow_specular']}; border: 1px solid {COLORS['glow_specular']}; }}"
                f"QPushButton:pressed {{ background-color: {COLORS['accent']}; }}"
            )

    def _palette_for_mode(self) -> Tuple[str, str, str]:
        if self._mode == "urgent":
            return COLORS["glow_magenta"], COLORS["accent_danger"], COLORS["glow_gold"]
        if self._mode == "warning":
            return COLORS["glow_gold"], COLORS["accent_warning"], COLORS["glow_cyan"]
        if self._mode == "paused":
            return COLORS["glow_gold"], COLORS["border_shine"], COLORS["glow_violet_light"]
        if self._mode == "idle":
            return COLORS["border_shine"], COLORS["glow_violet"], COLORS["glow_cyan"]
        return COLORS["glow_violet_light"], COLORS["glow_cyan"], COLORS["glow_green"]

    def _start_hover_anim(self, target: float, duration_ms: int) -> None:
        self._hover_anim.stop()
        self._hover_anim.setDuration(duration_ms)
        self._hover_anim.setStartValue(self._hover_level)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, event) -> None:
        self._start_hover_anim(1.0, 180)
        if self._shimmer_anim.state() != self._shimmer_anim.State.Running:
            self._shimmer_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        local_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(local_pos):
            self._start_hover_anim(0.0, 220)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.width() > 0:
            self._mouse_x_ratio = max(0.05, min(0.95, event.position().x() / float(self.width())))
            self.update()
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            if self._upcoming_popover.isVisible():
                self._upcoming_popover.reposition(self._card_screen_rect())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, _event) -> None:
        if self.on_bring_main_to_front:
            self.on_bring_main_to_front()

    def showEvent(self, event) -> None:
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self._show_fade_anim.stop()
        self.setWindowOpacity(0.0)
        self._show_fade_anim.setStartValue(0.0)
        self._show_fade_anim.setEndValue(self._target_opacity)
        self._show_fade_anim.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._anim_timer.stop()
        self._hover_anim.stop()
        self._shimmer_anim.stop()
        self._show_fade_anim.stop()
        self._upcoming_popover.hide_popover(immediate=True)
        self._style_action_buttons()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        self._anim_timer.stop()
        self._hover_anim.stop()
        self._shimmer_anim.stop()
        self._show_fade_anim.stop()
        self._upcoming_popover.hide_popover(immediate=True)
        self._upcoming_popover.close()
        super().closeEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = float(self._GLOW_PAD)
        card = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        radius = self._CARD_RADIUS
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        c_start, c_mid, c_end = self._palette_for_mode()

        idle_damp = 0.55 if self._mode == "idle" else 1.0
        urgent_boost = 1.25 if self._mode == "urgent" else 1.0
        hover = self._hover_level

        # 1. Breathing outer neon aura
        for spread, base_a in ((7.8, 11), (5.2, 22), (2.9, 40), (1.3, 64)):
            glow_rect = card.adjusted(-spread, -spread, spread, spread)
            alpha = int((base_a + 14 * pulse * urgent_boost + 18 * hover) * idle_damp)
            glow_grad = QLinearGradient(glow_rect.topLeft(), glow_rect.bottomRight())
            glow_grad.setColorAt(0.0, _alpha_color(c_start, alpha))
            glow_grad.setColorAt(0.55, _alpha_color(c_mid, alpha))
            glow_grad.setColorAt(1.0, _alpha_color(c_end, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_grad)
            painter.drawRoundedRect(glow_rect, radius + spread * 0.45, radius + spread * 0.45)

        # 2. Translucent Cyber-Aurora glass card fill
        card_path = QPainterPath()
        card_path.addRoundedRect(card, radius, radius)

        bg_grad = QLinearGradient(card.topLeft(), card.bottomRight())
        bg_grad.setColorAt(0.0, _alpha_color(COLORS["surface_light"], 244))
        bg_grad.setColorAt(0.5, _alpha_color(COLORS["surface"], 242))
        bg_grad.setColorAt(1.0, _alpha_color(COLORS["bg_dark"], 248))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_grad)
        painter.drawPath(card_path)

        painter.save()
        painter.setClipPath(card_path)

        # Dynamic spotlight: drifts slowly at rest, tracks cursor on hover
        rest_x = 0.5 + 0.28 * math.sin(self._pulse_phase * 0.6)
        spot_ratio = rest_x * (1.0 - hover) + self._mouse_x_ratio * hover
        spot_center = QPointF(card.left() + card.width() * spot_ratio, card.center().y())
        spot_r = card.width() * (0.45 + 0.12 * hover)
        spot_grad = QRadialGradient(spot_center, spot_r)
        spot_alpha = int((22 + 12 * pulse + 34 * hover) * idle_damp)
        spot_grad.setColorAt(0.0, _alpha_color(c_mid, spot_alpha))
        spot_grad.setColorAt(0.6, _alpha_color(c_start, int(spot_alpha * 0.45)))
        spot_grad.setColorAt(1.0, _alpha_color(COLORS["bg_dark"], 0))
        painter.fillRect(card, spot_grad)

        # Top glossy reflection band
        gloss_rect = QRectF(card.left(), card.top(), card.width(), card.height() * 0.46)
        gloss_grad = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], int(26 + 16 * hover)))
        gloss_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
        painter.fillRect(gloss_rect, gloss_grad)

        # Hover / toggle diagonal shimmer ribbon
        if -0.30 <= self._shimmer_pos <= 1.30:
            cx = card.left() + card.width() * self._shimmer_pos
            band_w = max(38.0, card.width() * 0.24)
            shimmer_grad = QLinearGradient(
                QPointF(cx - band_w, card.top()),
                QPointF(cx + band_w, card.bottom()),
            )
            shimmer_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], 0))
            shimmer_grad.setColorAt(0.5, _alpha_color(COLORS["glow_specular"], 52))
            shimmer_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
            painter.fillRect(card, shimmer_grad)

        # Left vertical neon accent pill
        pill_x = card.left() + 5.0
        pill_top = card.top() + 7.5
        pill_bot = card.bottom() - 7.5
        if pill_bot > pill_top + 2:
            pill_grad = QLinearGradient(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))
            pill_grad.setColorAt(0.0, QColor(c_start))
            pill_grad.setColorAt(0.55, QColor(c_mid))
            pill_grad.setColorAt(1.0, QColor(c_end))
            pill_pen = QPen(pill_grad, 2.6)
            pill_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pill_pen)
            painter.drawLine(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))

        # Bottom live countdown micro-progress strip
        if self._has_active and self._progress_ratio > 0.005:
            bar_margin = 10.0
            full_w = max(0.0, card.width() - 2 * bar_margin)
            fill_w = full_w * self._progress_ratio
            bar_y = card.bottom() - 3.6
            track_rect = QRectF(card.left() + bar_margin, bar_y, full_w, 2.2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_alpha_color(COLORS["border"], 140))
            painter.drawRoundedRect(track_rect, 1.1, 1.1)

            if fill_w > 1.5:
                fill_rect = QRectF(card.left() + bar_margin, bar_y, fill_w, 2.2)
                bar_grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
                bar_grad.setColorAt(0.0, QColor(c_start))
                bar_grad.setColorAt(0.55, QColor(c_mid))
                bar_grad.setColorAt(1.0, QColor(c_end))
                painter.setBrush(bar_grad)
                painter.drawRoundedRect(fill_rect, 1.1, 1.1)

        painter.restore()

        # 3. Shifting iridescent neon border
        shift = 0.5 + 0.5 * math.cos(self._pulse_phase)
        b_p1 = QPointF(card.left() + card.width() * 0.3 * shift, card.top())
        b_p2 = QPointF(card.right() - card.width() * 0.3 * shift, card.bottom())
        border_grad = QLinearGradient(b_p1, b_p2)
        border_grad.setColorAt(0.0, QColor(c_start))
        border_grad.setColorAt(0.5, QColor(c_mid))
        border_grad.setColorAt(1.0, QColor(c_end))
        border_w = 1.5 + 0.6 * hover
        border_pen = QPen(border_grad, border_w)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card, radius, radius)

    def _card_screen_rect(self) -> QRect:
        g = self.frameGeometry()
        p = self._GLOW_PAD
        return g.adjusted(p, p, -p, -p)

    def _handle_pause(self) -> None:
        if self.on_toggle_pause:
            self.on_toggle_pause()

    def _handle_show_upcoming(self) -> None:
        self.show_upcoming_popover()

    def is_upcoming_visible(self) -> bool:
        return self._upcoming_popover.isVisible() and not self._upcoming_popover._hiding

    def show_upcoming_popover(self, duration_ms: int = HudUpcomingPopover._DISPLAY_MS) -> None:
        """Toggle or display the glowing upcoming-alarms popover below/above the HUD."""
        if self._upcoming_popover.isVisible() and not self._upcoming_popover._hiding:
            self._upcoming_popover.hide_popover()
            self._style_action_buttons()
            return

        if self._shimmer_anim.state() != self._shimmer_anim.State.Running:
            self._shimmer_anim.start()
        entries = self.on_get_upcoming_items() if self.on_get_upcoming_items else []
        self._upcoming_popover.set_target_opacity(self._target_opacity)
        self._upcoming_popover.show_popover(
            self._card_screen_rect(),
            entries=entries,
            primary_id=self._current_item_id,
            duration_ms=duration_ms,
        )
        self._style_action_buttons()

    def refresh_upcoming_entries(self, entries: List[HudAlarmEntry]) -> None:
        """Update an already-visible upcoming popover with fresh countdowns/entries."""
        if self._upcoming_popover.isVisible():
            self._upcoming_popover.update_entries(
                entries,
                self._current_item_id,
                hud_rect=self._card_screen_rect(),
            )
            self._style_action_buttons()

    def update_status(
        self,
        name: str,
        remaining_sec: float,
        is_paused: bool = False,
        is_sla: bool = False,
        total_sec: float = 0.0,
        other_count: int = 0,
        item_id: Optional[str] = None,
    ) -> None:
        """Update live status display, glow palette, progress strip, and Pause/Play affordance."""
        self._has_active = True
        self._is_paused = bool(is_paused)
        self._current_item_id = item_id
        self._other_count = max(0, int(other_count))

        if total_sec > 0.0:
            self._progress_ratio = max(0.0, min(1.0, remaining_sec / total_sec))
        else:
            self._progress_ratio = 0.0

        time_str = _format_hud_countdown(remaining_sec)

        if is_paused:
            self._mode = "paused"
            self.lbl_icon.setText("⏸️")
            self.lbl_countdown.setText(f"⏸ {time_str}")
            cd_color = COLORS["glow_gold"]
        elif remaining_sec <= 0:
            self._mode = "urgent"
            self.lbl_icon.setText("🚨")
            self.lbl_countdown.setText("🚨 00:00")
            cd_color = COLORS["glow_magenta"]
        elif remaining_sec < 60:
            self._mode = "urgent"
            self.lbl_icon.setText("🚨" if is_sla else "⏱️")
            self.lbl_countdown.setText(time_str)
            cd_color = COLORS["glow_magenta"]
        elif remaining_sec < 300:
            self._mode = "warning"
            self.lbl_icon.setText("⚡" if is_sla else "⏳")
            self.lbl_countdown.setText(time_str)
            cd_color = COLORS["glow_gold"]
        else:
            self._mode = "normal"
            self.lbl_icon.setText("🎫" if is_sla else "⏳")
            self.lbl_countdown.setText(time_str)
            cd_color = COLORS["glow_cyan"]

        self.lbl_countdown.setStyleSheet(
            f"background: transparent; border: none; font-weight: 700; "
            f"color: {cd_color}; font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 12px;"
        )

        display_name = name if len(name) <= 17 else name[:15] + ".."
        self.lbl_title.setText(display_name)
        self._style_action_buttons()
        self.update()

    def set_idle(self) -> None:
        self._has_active = False
        self._is_paused = False
        self._current_item_id = None
        self._other_count = 0
        self._progress_ratio = 0.0
        self._mode = "idle"
        self.lbl_icon.setText("✅")
        self.lbl_title.setText("All Quiet")
        self.lbl_countdown.setText("00:00")
        self.lbl_countdown.setStyleSheet(
            f"background: transparent; border: none; font-weight: 700; "
            f"color: {COLORS['text_muted']}; font-family: \"{FONT_FAMILY}\", sans-serif; font-size: 12px;"
        )
        self._style_action_buttons()
        self.update()

    def set_hud_opacity(self, opacity: float) -> None:
        """Update HUD & upcoming-popover window opacity (clamped to 0.60..1.00)."""
        clamped = max(0.60, min(1.0, float(opacity)))
        self._target_opacity = clamped
        if self._show_fade_anim.state() != self._show_fade_anim.State.Running:
            self.setWindowOpacity(clamped)
        self._upcoming_popover.set_target_opacity(clamped)

    def close_hud(self) -> None:
        self._upcoming_popover.hide_popover(immediate=True)
        self.hide()
        if self.on_close_cb:
            self.on_close_cb()
