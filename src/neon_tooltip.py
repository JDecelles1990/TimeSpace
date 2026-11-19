"""Custom Cyber-Aurora Neon Glass animated tooltip widget and application-wide filter."""
import html
from typing import Optional, Tuple

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QHelpEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QPushButton,
    QTabBar,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from src.config import COLORS, FONT_FAMILY


_ROLE_PALETTES = {
    "default": (COLORS["glow_violet_light"], COLORS["glow_cyan"], COLORS["glow_green"]),
    "primary": (COLORS["glow_cyan"], COLORS["accent_hover"], COLORS["glow_violet_light"]),
    "success": (COLORS["glow_green"], COLORS["glow_cyan"], COLORS["glow_specular"]),
    "danger": (COLORS["glow_magenta"], COLORS["accent_danger"], COLORS["glow_violet_light"]),
    "warning": (COLORS["glow_gold"], COLORS["accent_warning"], COLORS["glow_cyan"]),
}


def _alpha_color(hex_color: str, alpha: int) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(alpha)
    return c


def _format_tooltip_html(raw_text: str) -> str:
    """Format plain tooltip text into crisp Cyber-Aurora rich text (escaping HTML safely)."""
    stripped = raw_text.strip()
    if not stripped:
        return ""
    if stripped.startswith("<") and stripped.endswith(">"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) == 1:
        return (
            f"<span style='color:{COLORS['glow_specular']}; font-weight:600;'>"
            f"{html.escape(lines[0])}</span>"
        )

    parts = [
        f"<div style='color:{COLORS['glow_specular']}; font-weight:700; margin-bottom:2px;'>"
        f"{html.escape(lines[0])}</div>"
    ]
    for extra in lines[1:]:
        if extra.strip():
            parts.append(
                f"<div style='color:{COLORS['text']}; font-weight:400; margin-top:1px;'>"
                f"{html.escape(extra)}</div>"
            )
    return "".join(parts)


class NeonToolTip(QWidget):
    """Frameless translucent Cyber-Aurora tooltip card with neon aura, shimmer sweep, and fade/glide transitions."""

    _GLOW_PAD = 10
    _MAX_TEXT_WIDTH = 330
    _TARGET_OPACITY = 0.97

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
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._accent_role: str = "default"
        self._current_text: str = ""
        self._shimmer_pos: float = -1.0
        self._hiding: bool = False
        self._target_pos: QPoint = QPoint(0, 0)

        layout = QVBoxLayout(self)
        # Extra left padding clears the glowing inner left neon accent pill
        layout.setContentsMargins(
            self._GLOW_PAD + 14,
            self._GLOW_PAD + 7,
            self._GLOW_PAD + 11,
            self._GLOW_PAD + 7,
        )
        layout.setSpacing(0)

        self._label = QLabel(self)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setStyleSheet(
            f"QLabel {{ background: transparent; border: none; "
            f"color: {COLORS['glow_specular']}; font-family: \"{FONT_FAMILY}\", sans-serif; "
            f"font-size: 11px; }}"
        )
        layout.addWidget(self._label)

        # Opacity fade-in / fade-out animation
        self._opacity_anim = QVariantAnimation(self)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_anim.valueChanged.connect(self._on_opacity_step)
        self._opacity_anim.finished.connect(self._on_opacity_finished)

        # Vertical glide-in animation (+6px -> 0px)
        self._glide_anim = QVariantAnimation(self)
        self._glide_anim.setDuration(165)
        self._glide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._glide_anim.valueChanged.connect(self._on_glide_step)

        # Subtle glossy light-ribbon sweep across the card on reveal
        self._shimmer_anim = QVariantAnimation(self)
        self._shimmer_anim.setDuration(360)
        self._shimmer_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._shimmer_anim.setStartValue(-0.25)
        self._shimmer_anim.setEndValue(1.25)
        self._shimmer_anim.valueChanged.connect(self._on_shimmer_step)
        self._shimmer_anim.finished.connect(self._on_shimmer_finished)

        # Auto-dismiss safety timer (matches standard desktop tooltip timeout)
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(8000)
        self._auto_hide_timer.timeout.connect(self.hide_tip)

        self.setWindowOpacity(0.0)
        self.hide()

    def _on_opacity_step(self, val) -> None:
        self.setWindowOpacity(max(0.0, min(1.0, float(val))))

    def _on_opacity_finished(self) -> None:
        if self._hiding and self.windowOpacity() <= 0.02:
            self._hiding = False
            self.hide()

    def _on_glide_step(self, val) -> None:
        self.move(self._target_pos.x(), int(val))

    def _on_shimmer_step(self, val) -> None:
        self._shimmer_pos = float(val)
        self.update()

    def _on_shimmer_finished(self) -> None:
        self._shimmer_pos = -1.0
        self.update()

    def _palette(self) -> Tuple[str, str, str]:
        return _ROLE_PALETTES.get(self._accent_role, _ROLE_PALETTES["default"])

    def _compute_clamped_pos(self, global_pos: QPoint) -> QPoint:
        w, h = self.width(), self.height()
        # Offset slightly below and right of cursor; compensate for outer glow margin
        x = global_pos.x() + 14 - self._GLOW_PAD
        y = global_pos.y() + 18 - self._GLOW_PAD

        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if x + w - self._GLOW_PAD > avail.right():
                x = global_pos.x() - w + self._GLOW_PAD - 8
            if y + h - self._GLOW_PAD > avail.bottom():
                y = global_pos.y() - h + self._GLOW_PAD - 10
            x = max(avail.left() - self._GLOW_PAD + 4, min(x, avail.right() - w + self._GLOW_PAD - 4))
            y = max(avail.top() - self._GLOW_PAD + 4, min(y, avail.bottom() - h + self._GLOW_PAD - 4))
        return QPoint(x, y)

    def show_tip(self, text: str, global_pos: QPoint, accent_role: str = "default") -> None:
        """Display or smoothly update the animated Cyber-Aurora tooltip near *global_pos*."""
        cleaned = (text or "").strip()
        if not cleaned:
            self.hide_tip()
            return

        already_visible = self.isVisible() and not self._hiding
        text_changed = (cleaned != self._current_text) or (accent_role != self._accent_role)

        self._current_text = cleaned
        self._accent_role = accent_role if accent_role in _ROLE_PALETTES else "default"
        self._hiding = False

        if text_changed or not already_visible:
            self._label.setWordWrap(False)
            self._label.setMinimumWidth(0)
            self._label.setMaximumWidth(16777215)
            self._label.setText(_format_tooltip_html(cleaned))
            self._label.adjustSize()

            if self._label.sizeHint().width() > self._MAX_TEXT_WIDTH:
                self._label.setWordWrap(True)
                self._label.setFixedWidth(self._MAX_TEXT_WIDTH)
                self._label.adjustSize()
            else:
                self._label.setMaximumWidth(self._MAX_TEXT_WIDTH)

            if self.layout() is not None:
                self.layout().activate()
            self.resize(self.sizeHint())

        self._target_pos = self._compute_clamped_pos(global_pos)
        self._auto_hide_timer.start()

        if not already_visible:
            self._opacity_anim.stop()
            self._glide_anim.stop()
            self._shimmer_anim.stop()

            start_y = self._target_pos.y() + 6
            self.move(self._target_pos.x(), start_y)
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()

            self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._opacity_anim.setDuration(165)
            self._opacity_anim.setStartValue(0.0)
            self._opacity_anim.setEndValue(self._TARGET_OPACITY)
            self._opacity_anim.start()

            self._glide_anim.setStartValue(start_y)
            self._glide_anim.setEndValue(self._target_pos.y())
            self._glide_anim.start()

            self._shimmer_anim.start()
        else:
            self.move(self._target_pos)
            self.raise_()
            if text_changed:
                self._shimmer_anim.stop()
                self._shimmer_anim.start()
            self.update()

    def hide_tip(self, immediate: bool = False) -> None:
        """Smoothly fade out the tooltip (or hide immediately during shutdown)."""
        self._auto_hide_timer.stop()
        if not self.isVisible():
            self._hiding = False
            return
        if immediate:
            self._opacity_anim.stop()
            self._glide_anim.stop()
            self._shimmer_anim.stop()
            self._hiding = False
            self.setWindowOpacity(0.0)
            self.hide()
            return
        if self._hiding:
            return
        self._hiding = True
        self._opacity_anim.stop()
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._opacity_anim.setDuration(115)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = float(self._GLOW_PAD)
        card = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        radius = 7.0
        c_start, c_mid, c_end = self._palette()

        # 1. Soft multi-layered outer neon aura
        for spread, alpha in ((7.5, 10), (5.0, 22), (3.0, 42), (1.4, 68)):
            glow_rect = card.adjusted(-spread, -spread, spread, spread)
            glow_grad = QLinearGradient(glow_rect.topLeft(), glow_rect.bottomRight())
            g1 = QColor(c_start)
            g1.setAlpha(alpha)
            g2 = QColor(c_mid)
            g2.setAlpha(alpha)
            glow_grad.setColorAt(0.0, g1)
            glow_grad.setColorAt(1.0, g2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_grad)
            painter.drawRoundedRect(glow_rect, radius + spread * 0.5, radius + spread * 0.5)

        # 2. Cyber-Aurora dark translucent glass card fill
        card_path = QPainterPath()
        card_path.addRoundedRect(card, radius, radius)

        bg_grad = QLinearGradient(card.topLeft(), card.bottomRight())
        bg_grad.setColorAt(0.0, _alpha_color(COLORS["surface_light"], 248))
        bg_grad.setColorAt(0.5, _alpha_color(COLORS["surface"], 246))
        bg_grad.setColorAt(1.0, _alpha_color(COLORS["bg_dark"], 250))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_grad)
        painter.drawPath(card_path)

        # 3. Subtle glossy top glass reflection & animated shimmer sweep (clipped to card)
        painter.save()
        painter.setClipPath(card_path)

        gloss_rect = QRectF(card.left(), card.top(), card.width(), card.height() * 0.44)
        gloss_grad = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], 26))
        gloss_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
        painter.fillRect(gloss_rect, gloss_grad)

        if -0.25 <= self._shimmer_pos <= 1.25:
            cx = card.left() + card.width() * self._shimmer_pos
            band_w = max(44.0, card.width() * 0.34)
            shimmer_grad = QLinearGradient(
                QPointF(cx - band_w, card.top()),
                QPointF(cx + band_w, card.bottom()),
            )
            shimmer_grad.setColorAt(0.0, _alpha_color(COLORS["glow_specular"], 0))
            shimmer_grad.setColorAt(0.5, _alpha_color(COLORS["glow_specular"], 34))
            shimmer_grad.setColorAt(1.0, _alpha_color(COLORS["glow_specular"], 0))
            painter.fillRect(card, shimmer_grad)

        # 4. Left neon accent bar inside card
        pill_x = card.left() + 4.5
        pill_top = card.top() + 5.5
        pill_bot = card.bottom() - 5.5
        if pill_bot > pill_top + 2:
            pill_grad = QLinearGradient(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))
            pill_grad.setColorAt(0.0, QColor(c_start))
            pill_grad.setColorAt(0.55, QColor(c_mid))
            pill_grad.setColorAt(1.0, QColor(c_end))
            pill_pen = QPen(pill_grad, 2.4)
            pill_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pill_pen)
            painter.drawLine(QPointF(pill_x, pill_top), QPointF(pill_x, pill_bot))

        painter.restore()

        # 5. Iridescent outer neon border
        border_grad = QLinearGradient(card.topLeft(), card.bottomRight())
        border_grad.setColorAt(0.0, QColor(c_start))
        border_grad.setColorAt(0.5, QColor(c_mid))
        border_grad.setColorAt(1.0, QColor(c_end))
        border_pen = QPen(border_grad, 1.35)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card, radius, radius)


class NeonToolTipFilter(QObject):
    """App-wide event filter intercepting QEvent.ToolTip to show animated Cyber-Aurora tooltips."""

    _APP_WINDOW_CLASSES = (
        "MainApp",
        "FloatingMiniHUD",
        "AlarmDialog",
        "AHKHotstringsDialog",
        "AHKItemEditDialog",
    )

    def __init__(self, root: QWidget) -> None:
        super().__init__(root)
        self._root = root
        self._alive = True
        self._tooltip = NeonToolTip()
        self._active_target: Optional[QWidget] = None
        root.destroyed.connect(self._mark_dead)

    def _mark_dead(self) -> None:
        self._alive = False
        try:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except RuntimeError:
            pass
        self.cleanup()

    def cleanup(self) -> None:
        try:
            self._tooltip.hide_tip(immediate=True)
            self._tooltip.close()
        except RuntimeError:
            pass

    @property
    def tooltip_widget(self) -> NeonToolTip:
        return self._tooltip

    def _belongs_to_app(self, widget: QWidget) -> bool:
        if widget is self._tooltip or self._tooltip.isAncestorOf(widget):
            return False
        if widget is self._root or self._root.isAncestorOf(widget):
            return True
        win = widget.window()
        if win is not None:
            if win.__class__.__name__ in self._APP_WINDOW_CLASSES:
                return True
            parent = win.parent()
            if isinstance(parent, QWidget) and (parent is self._root or self._root.isAncestorOf(parent)):
                return True
        return False

    @staticmethod
    def _accent_role_for_widget(widget: QWidget) -> str:
        """Read-only role inspection (never mutates buttons or widgets)."""
        if isinstance(widget, QPushButton):
            obj = widget.objectName()
            if obj == "dangerBtn":
                return "danger"
            if obj == "successBtn":
                return "success"
            if obj == "primaryBtn":
                return "primary"
            if "Admin" in widget.text():
                return "warning"
        return "default"

    @staticmethod
    def _resolve_tooltip(watched: QWidget, local_pos: QPoint) -> Tuple[str, str]:
        """Resolve tooltip text and accent role for widgets, QTabBars, and QAbstractItemView items."""
        parent = watched.parent()
        if isinstance(parent, QAbstractItemView) and watched is parent.viewport():
            idx = parent.indexAt(local_pos)
            if idx.isValid():
                tip = idx.data(Qt.ItemDataRole.ToolTipRole)
                if tip:
                    return str(tip), "default"
            tip = parent.toolTip()
            return (tip, "default") if tip else ("", "default")

        if isinstance(watched, QTabBar):
            tab_idx = watched.tabAt(local_pos)
            if tab_idx >= 0:
                tab_tip = watched.tabToolTip(tab_idx)
                if tab_tip:
                    return tab_tip, "primary"
            tip = watched.toolTip()
            return (tip, "default") if tip else ("", "default")

        cur: Optional[QWidget] = watched
        while cur is not None:
            tip = cur.toolTip()
            if tip:
                return tip, NeonToolTipFilter._accent_role_for_widget(cur)
            if cur.isWindow():
                break
            nxt = cur.parent()
            cur = nxt if isinstance(nxt, QWidget) else None
        return "", "default"

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if not getattr(self, "_alive", False):
            return False
        try:
            if not isinstance(watched, QWidget):
                return False
            et = event.type()

            if et == QEvent.Type.ToolTip and isinstance(event, QHelpEvent):
                if not self._belongs_to_app(watched):
                    return False
                tip_text, role = self._resolve_tooltip(watched, event.pos())
                if tip_text:
                    QToolTip.hideText()
                    self._active_target = watched
                    self._tooltip.show_tip(tip_text, event.globalPos(), accent_role=role)
                    event.accept()
                    return True
                self._tooltip.hide_tip()
                return False

            if self._tooltip.isVisible():
                if et == QEvent.Type.MouseMove and watched is self._active_target:
                    parent = watched.parent()
                    is_item_vp = isinstance(parent, QAbstractItemView) and watched is parent.viewport()
                    if is_item_vp or isinstance(watched, QTabBar):
                        local_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                        tip_text, role = self._resolve_tooltip(watched, local_pos)
                        if not tip_text:
                            self._tooltip.hide_tip()
                        elif tip_text != self._tooltip._current_text or role != self._tooltip._accent_role:
                            gpos = (
                                event.globalPosition().toPoint()
                                if hasattr(event, "globalPosition")
                                else watched.mapToGlobal(local_pos)
                            )
                            self._tooltip.show_tip(tip_text, gpos, accent_role=role)
                elif et in (
                    QEvent.Type.Leave,
                    QEvent.Type.HoverLeave,
                ):
                    if watched is self._active_target:
                        self._active_target = None
                        self._tooltip.hide_tip()
                elif et in (
                    QEvent.Type.MouseButtonPress,
                    QEvent.Type.Wheel,
                    QEvent.Type.KeyPress,
                ):
                    self._active_target = None
                    self._tooltip.hide_tip()
                elif et == QEvent.Type.FocusOut and watched is self._active_target:
                    self._active_target = None
                    self._tooltip.hide_tip()
                elif et == QEvent.Type.WindowDeactivate and watched.isWindow():
                    self._active_target = None
                    self._tooltip.hide_tip()
                elif et == QEvent.Type.Hide and watched is self._active_target:
                    self._active_target = None
                    self._tooltip.hide_tip(immediate=True)
        except RuntimeError:
            return False
        return False
