"""PySide6 UI Module for TimeSpace (Dual-Mode: F7Hub Embeddable QWidget & Standalone QMainWindow)."""
import os
import re
import sys
import time
import datetime
from typing import Optional, List, Tuple, Callable

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QUrl, QPoint, QEvent
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
    QColor,
    QGuiApplication,
    QDesktopServices,
    QFont,
    QIcon,
    QPixmap,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QSlider,
    QFileDialog,
    QMessageBox,
    QFrame,
    QTextEdit,
    QPlainTextEdit,
    QMenu,
    QColorDialog,
    QSplitter,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)

from src.config import (
    APP_TITLE,
    HOTKEY,
    MEETING_HOTKEY,
    COLORS,
    UI_DIMENSIONS,
    DARK_QSS,
    SOUND_PRESETS,
    CATEGORIES,
    QUICK_TIMER_PRESETS,
    SNOOZE_OPTIONS,
    SCRATCHPAD_TEXT_COLORS,
    AppConfig,
    HistoryEntry,
    ScratchpadState,
)
from src.storage import Storage
from src.scheduler import ReminderScheduler, ScheduledItem
from src.sound import SoundPlayer
from src.tray import TrayManager
from src.notifications import show_toast
from src.startup import is_startup_enabled, set_startup_enabled
from src.natural_parser import NaturalParser
from src.calendar_export import CalendarManager
from src.circular_ring import CircularProgressRing
from src.calendar_widget import MiniCalendar
from src.time_picker import BigButtonsTimePicker
from src.alarm_dialog import AlarmDialog
from src.mini_hud import FloatingMiniHUD
from src.hotkey_manager import GlobalHotkeyListener
from src.go_tab import GoTroubleshootingTab
from src.ahk_manager import AHKProcessManager, find_ahk_v2_exe, generate_ahk_v2_script
from src.ahk_dialog import AHKHotstringsDialog
from src.storage import DEFAULT_AHK_SCRIPT_FILE
from src.meeting_detector import is_microphone_in_use, get_active_microphone_apps


_URL_TOKEN_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


class ButtonGlowFilter(QObject):
    """Adds a violet (hover) / cyan-green (pressed) neon glow to QPushButtons."""

    def __init__(self, root: QWidget) -> None:
        super().__init__(root)
        self._root = root

    @staticmethod
    def _apply(btn: QPushButton, color: str, blur: int) -> None:
        eff = QGraphicsDropShadowEffect(btn)
        eff.setOffset(0, 0)
        eff.setBlurRadius(blur)
        eff.setColor(QColor(color))
        btn.setGraphicsEffect(eff)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QPushButton) and self._root.isAncestorOf(watched):
            et = event.type()
            if et in (QEvent.Type.Enter, QEvent.Type.HoverEnter) and watched.isEnabled():
                self._apply(watched, COLORS["glow_violet"], 22)
            elif et == QEvent.Type.MouseButtonPress and watched.isEnabled():
                self._apply(watched, COLORS["glow_cyan"], 30)
            elif et == QEvent.Type.MouseButtonRelease:
                if watched.underMouse():
                    self._apply(watched, COLORS["glow_violet"], 22)
                else:
                    watched.setGraphicsEffect(None)
            elif et in (QEvent.Type.Leave, QEvent.Type.HoverLeave, QEvent.Type.Hide):
                watched.setGraphicsEffect(None)
        return False


def normalize_link_target(raw_target: str) -> str:
    """Normalize a user-provided web link or local path into an openable URL/path."""
    cleaned = raw_target.strip().rstrip(".,;:!?)")
    if not cleaned:
        return ""
    if cleaned.lower().startswith("www."):
        return f"https://{cleaned}"
    return cleaned


def open_attachment_link(raw_target: str) -> bool:
    """Open a web URL, custom URI scheme, or local file path via OS handler."""
    target = normalize_link_target(raw_target)
    if not target:
        return False
    if os.path.exists(target):
        return QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(target)))
    qurl = QUrl(target)
    if not qurl.scheme():
        qurl = QUrl(f"https://{target}")
    return QDesktopServices.openUrl(qurl)


class ScratchpadUrlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter that visually styles web links (http/https/www) in Scratchpad editors."""

    def __init__(self, document):
        super().__init__(document)
        self._link_fmt = QTextCharFormat()
        self._link_fmt.setForeground(QColor(COLORS["accent_link"]))
        self._link_fmt.setFontUnderline(True)

    def highlightBlock(self, text: str) -> None:
        for match in _URL_TOKEN_RE.finditer(text):
            start, end = match.span()
            self.setFormat(start, end - start, self._link_fmt)


class ScratchpadEditor(QTextEdit):
    """Rich-text Scratchpad editor supporting bold, text colors, and clickable web links."""

    linkActivated = Signal(str)
    scheduleContextRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAcceptRichText(True)
        self._url_highlighter = ScratchpadUrlHighlighter(self.document())

    def contextMenuEvent(self, event) -> None:
        menu = self.createStandardContextMenu()
        menu.setStyleSheet(DARK_QSS)
        menu.addSeparator()
        act_sched = menu.addAction("⏰ Schedule Highlighted / Line as Timer or RDV...")
        act_sched.triggered.connect(lambda: self.scheduleContextRequested.emit())
        menu.exec(event.globalPos())

    def _url_at_pos(self, pos: QPoint) -> str:
        cursor = self.cursorForPosition(pos)
        block_text = cursor.block().text()
        col = cursor.positionInBlock()
        for match in _URL_TOKEN_RE.finditer(block_text):
            start, end = match.span()
            if start <= col <= end:
                return match.group(0).rstrip(".,;:!?)")
        return ""

    def mouseMoveEvent(self, event) -> None:
        url = self._url_at_pos(event.pos())
        if url:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"Click to open: {normalize_link_target(url)}")
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            self.setToolTip("")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                url = self._url_at_pos(event.pos())
                if url:
                    self.linkActivated.emit(url)
                    event.accept()
                    return
        super().mouseReleaseEvent(event)


class RichScratchpadPane(QWidget):
    """Reusable rich-text Scratchpad component with Bold, Color, Timestamp, Ctrl+F Find, Schedule Selection (⏰), Export to C:\\Temp (💾), Copy, Clear, and URL detection."""

    contentModified = Signal()
    scheduleRequested = Signal(str, str, int)

    def __init__(
        self,
        title: str,
        placeholder: str = "",
        initial_text: str = "",
        initial_html: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setMinimumWidth(0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(3)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(3)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 11px;")
        toolbar.addWidget(self.lbl_title)

        self.lbl_status = QLabel("Auto-save")
        self.lbl_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()

        self.btn_find = QPushButton("🔍")
        self.btn_find.setFixedHeight(22)
        self.btn_find.setToolTip("Find text in scratchpad (Ctrl+F)")
        self.btn_find.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_find.clicked.connect(self.toggle_find_bar)
        toolbar.addWidget(self.btn_find)

        self.btn_bold = QPushButton("𝐁")
        self.btn_bold.setFixedHeight(22)
        self.btn_bold.setToolTip("Toggle bold on highlighted text (Ctrl+B)")
        self.btn_bold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bold.clicked.connect(self.toggle_bold)
        toolbar.addWidget(self.btn_bold)

        self.btn_color = QPushButton("🎨")
        self.btn_color.setFixedHeight(22)
        self.btn_color.setToolTip("Change color of highlighted text")
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.clicked.connect(self.show_color_menu)
        toolbar.addWidget(self.btn_color)

        self.btn_stamp = QPushButton("🕒")
        self.btn_stamp.setObjectName("primaryBtn")
        self.btn_stamp.setFixedHeight(22)
        self.btn_stamp.setToolTip("Insert current timestamp (Ctrl+T)")
        self.btn_stamp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stamp.clicked.connect(self.insert_timestamp)
        toolbar.addWidget(self.btn_stamp)

        self.btn_schedule = QPushButton("⏰")
        self.btn_schedule.setObjectName("primaryBtn")
        self.btn_schedule.setFixedHeight(22)
        self.btn_schedule.setToolTip("Schedule highlighted text (or current line) as a Timer or RDV")
        self.btn_schedule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_schedule.clicked.connect(self.show_schedule_menu)
        toolbar.addWidget(self.btn_schedule)

        self.btn_export = QPushButton("💾")
        self.btn_export.setFixedHeight(22)
        self.btn_export.setToolTip("Export scratchpad notes to C:\\Temp (.md) (Ctrl+S)")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(lambda _c=False: self.export_notes())
        toolbar.addWidget(self.btn_export)

        self.btn_copy = QPushButton("📋")
        self.btn_copy.setFixedHeight(22)
        self.btn_copy.setToolTip("Copy notes to clipboard")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self.copy_all)
        toolbar.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("🧹")
        self.btn_clear.setObjectName("dangerBtn")
        self.btn_clear.setFixedHeight(22)
        self.btn_clear.setToolTip("Clear notes")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_notes)
        toolbar.addWidget(self.btn_clear)

        layout.addLayout(toolbar)

        # Collapsible Ctrl+F Find Bar
        self.find_bar = QFrame(self)
        self.find_bar.setVisible(False)
        self.find_bar.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 4px; }}"
        )
        fb_layout = QHBoxLayout(self.find_bar)
        fb_layout.setContentsMargins(4, 2, 4, 2)
        fb_layout.setSpacing(4)

        fb_layout.addWidget(QLabel("🔍"))
        self.entry_find = QLineEdit()
        self.entry_find.setMinimumWidth(0)
        self.entry_find.setPlaceholderText("Find in scratchpad... (Enter = Next)")
        self.entry_find.returnPressed.connect(lambda: self.find_in_notes(backward=False))
        self.entry_find.textChanged.connect(lambda _t: self.find_in_notes(backward=False, from_start=True))
        fb_layout.addWidget(self.entry_find, 1)

        self.btn_find_prev = QPushButton("▲")
        self.btn_find_prev.setFixedWidth(26)
        self.btn_find_prev.setFixedHeight(20)
        self.btn_find_prev.setToolTip("Previous match")
        self.btn_find_prev.clicked.connect(lambda: self.find_in_notes(backward=True))
        fb_layout.addWidget(self.btn_find_prev)

        self.btn_find_next = QPushButton("▼")
        self.btn_find_next.setFixedWidth(26)
        self.btn_find_next.setFixedHeight(20)
        self.btn_find_next.setToolTip("Next match")
        self.btn_find_next.clicked.connect(lambda: self.find_in_notes(backward=False))
        fb_layout.addWidget(self.btn_find_next)

        self.btn_find_close = QPushButton("✖")
        self.btn_find_close.setFixedWidth(24)
        self.btn_find_close.setFixedHeight(20)
        self.btn_find_close.setToolTip("Close search bar")
        self.btn_find_close.clicked.connect(self.hide_find_bar)
        fb_layout.addWidget(self.btn_find_close)

        layout.addWidget(self.find_bar)

        self.editor = ScratchpadEditor(self)
        self.editor.setMinimumHeight(70)
        self.editor.setPlaceholderText(
            placeholder
            or "Jot down notes, client names, ticket #, or URLs... Highlight text for 𝐁 Bold (Ctrl+B), 🎨 Color, or ⏰ Schedule."
        )
        self.editor.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        if initial_html and initial_text:
            self.editor.setHtml(initial_html)
        elif initial_text:
            self.editor.setPlainText(initial_text)
        self.editor.textChanged.connect(lambda: self.contentModified.emit())
        self.editor.linkActivated.connect(self._on_link_clicked)
        self.editor.scheduleContextRequested.connect(self.show_schedule_menu)
        layout.addWidget(self.editor, 1)

        shortcut_ts = QShortcut(QKeySequence("Ctrl+T"), self.editor)
        shortcut_ts.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut_ts.activated.connect(self.insert_timestamp)

        shortcut_bold = QShortcut(QKeySequence("Ctrl+B"), self.editor)
        shortcut_bold.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut_bold.activated.connect(self.toggle_bold)

        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_find.activated.connect(self.toggle_find_bar)

        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self.editor)
        shortcut_save.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut_save.activated.connect(lambda: self.export_notes())

    def toggle_find_bar(self) -> None:
        if self.find_bar.isVisible():
            self.hide_find_bar()
        else:
            self.find_bar.setVisible(True)
            sel = self.editor.textCursor().selectedText().strip()
            if sel and "\n" not in sel and "\u2029" not in sel:
                self.entry_find.setText(sel)
            self.entry_find.setFocus()
            self.entry_find.selectAll()

    def hide_find_bar(self) -> None:
        self.find_bar.setVisible(False)
        self.editor.setFocus()

    def find_in_notes(self, backward: bool = False, from_start: bool = False) -> bool:
        query = self.entry_find.text().strip()
        if not query:
            self.lbl_status.setText("Auto-save")
            self.lbl_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            return False

        if from_start:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)

        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        found = self.editor.find(query, flags)
        if not found:
            # Wrap around to start or end
            cursor = self.editor.textCursor()
            cursor.movePosition(
                QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start
            )
            self.editor.setTextCursor(cursor)
            found = self.editor.find(query, flags)

        if found:
            self.lbl_status.setText(f"🔍 Match '{query[:14]}'")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 10px;")
        else:
            self.lbl_status.setText(f"🔍 No match '{query[:14]}'")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 10px;")
        return found

    def _extract_selection_or_line(self) -> Tuple[str, str]:
        """Return (task_text, extracted_url) from current selection or current cursor line."""
        cursor = self.editor.textCursor()
        raw = cursor.selectedText().replace("\u2029", " ").strip()
        if not raw:
            raw = cursor.block().text().strip()
        if not raw:
            raw = self.editor.toPlainText().splitlines()[0].strip() if self.editor.toPlainText().strip() else ""
        if not raw:
            return "", ""

        url_match = _URL_TOKEN_RE.search(raw)
        extracted_url = url_match.group(0).rstrip(".,;:!?)") if url_match else ""
        task_text = re.sub(r"^[\s•\-\*\[\]\d\.:]+", "", raw).strip() or raw
        return task_text[:120], extracted_url

    def show_schedule_menu(self) -> None:
        task_text, extracted_url = self._extract_selection_or_line()
        if not task_text:
            self.lbl_status.setText("ℹ️ Select or type text first")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_warning']}; font-size: 10px;")
            return

        menu = QMenu(self)
        menu.setStyleSheet(DARK_QSS)
        preview = task_text if len(task_text) <= 28 else f"{task_text[:25]}..."

        parsed = NaturalParser.parse(task_text)
        if parsed:
            act_nlp = menu.addAction(f"⚡ Auto-Schedule: {parsed['display_str']}")
            act_nlp.triggered.connect(
                lambda _c=False, t=task_text, u=extracted_url: self.scheduleRequested.emit(t, u, 0)
            )
            menu.addSeparator()

        for label, mins in QUICK_TIMER_PRESETS:
            act_p = menu.addAction(f"⏳ Start {label} Timer: '{preview}'")
            act_p.triggered.connect(
                lambda _c=False, t=task_text, u=extracted_url, m=mins: self.scheduleRequested.emit(t, u, m)
            )

        menu.addSeparator()
        act_t_form = menu.addAction(f"📝 Send '{preview}' to 1. Timers Form")
        act_t_form.triggered.connect(
            lambda _c=False, t=task_text, u=extracted_url: self.scheduleRequested.emit(t, u, -1)
        )
        act_r_form = menu.addAction(f"📅 Send '{preview}' to 2. RDV Form")
        act_r_form.triggered.connect(
            lambda _c=False, t=task_text, u=extracted_url: self.scheduleRequested.emit(t, u, -2)
        )

        menu.exec(self.btn_schedule.mapToGlobal(QPoint(0, self.btn_schedule.height() + 2)))

    def export_notes(self, filepath: Optional[str] = None) -> Optional[str]:
        content = self.editor.toPlainText().strip()
        if not content:
            self.lbl_status.setText("Nothing to export")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_warning']}; font-size: 10px;")
            return None
        try:
            saved_path = Storage.export_scratchpad_note(self.lbl_title.text(), content, filepath=filepath)
            fname = os.path.basename(saved_path)
            self.lbl_status.setText(f"💾 {fname[:24]}")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 10px;")
            return saved_path
        except Exception:
            self.lbl_status.setText("Export failed")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 10px;")
            return None

    def toggle_bold(self) -> None:
        cursor = self.editor.textCursor()
        current_weight = cursor.charFormat().fontWeight()
        is_bold = current_weight >= QFont.Weight.Bold
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()
        self.contentModified.emit()

    def show_color_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(DARK_QSS)
        for label, hex_val in SCRATCHPAD_TEXT_COLORS:
            pix = QPixmap(12, 12)
            pix.fill(QColor(hex_val))
            action = menu.addAction(QIcon(pix), label)
            action.triggered.connect(lambda _c=False, hx=hex_val: self.apply_color(hx))
        menu.addSeparator()
        custom_act = menu.addAction("🎨 Custom Color...")
        custom_act.triggered.connect(self.pick_custom_color)
        menu.exec(self.btn_color.mapToGlobal(QPoint(0, self.btn_color.height() + 2)))

    def pick_custom_color(self) -> None:
        initial = self.editor.textCursor().charFormat().foreground().color()
        if not initial.isValid() or initial.name().lower() == "#000000":
            initial = QColor(COLORS["accent"])
        chosen = QColorDialog.getColor(initial, self, "Select Highlighted Text Color")
        if chosen.isValid():
            self.apply_color(chosen.name())

    def apply_color(self, hex_color: str) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()
        self.contentModified.emit()

    def insert_timestamp(self) -> None:
        stamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        self.editor.insertPlainText(stamp)
        self.editor.setFocus()
        self.contentModified.emit()

    def copy_all(self) -> None:
        content = self.editor.toPlainText().strip()
        if content:
            QGuiApplication.clipboard().setText(content)
            self.lbl_status.setText("✅ Copied")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 10px;")

    def clear_notes(self) -> None:
        if not self.editor.toPlainText().strip():
            return
        reply = QMessageBox.question(
            self,
            "Clear Scratchpad",
            f"Clear all notes from '{self.lbl_title.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.editor.clear()
            self.contentModified.emit()

    def _on_link_clicked(self, raw_url: str) -> None:
        if open_attachment_link(raw_url):
            self.lbl_status.setText(f"🔗 {normalize_link_target(raw_url)[:28]}")
            self.lbl_status.setStyleSheet(f"color: {COLORS['accent_link']}; font-size: 10px;")


class HistoryListWidget(QListWidget):
    """QListWidget subclass that emits deleteKeyPressed when the Delete key is pressed."""

    deleteKeyPressed = Signal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self.deleteKeyPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class SchedulerBridge(QObject):
    """Thread-safe Qt Signal bridge marshaling background daemon events onto the main Qt UI thread."""

    itemTriggered = Signal(object)
    wakeMissedTriggered = Signal(list)
    toggleVisibilityRequested = Signal()
    quitRequested = Signal()
    togglePauseRequested = Signal()
    toggleHudRequested = Signal()
    toggleMeetingModeRequested = Signal()


class TimerRendezVousWidget(QWidget):
    """
    Self-contained PySide6 Module Widget (`TimeSpaceWidget`).
    Can be embedded directly inside F7Hub's QMainWindow/QStackedWidget or hosted by standalone MainApp.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(DARK_QSS)
        self.setMinimumWidth(0)

        # Load Unified Typed State
        self.app_config: AppConfig = Storage.load_config()
        self.scratchpad_state: ScratchpadState = Storage.load_scratchpad()
        self.sound_player = SoundPlayer(self.app_config)
        self.is_previewing: bool = False

        # Inline Editing State for Active Timers & RDVs
        self._editing_timer_id: Optional[str] = None
        self._last_started_timer_id: Optional[str] = None
        self._editing_rdv_id: Optional[str] = None
        self._last_started_rdv_id: Optional[str] = None

        # Floating Mini HUD State
        self.hud: Optional[FloatingMiniHUD] = None
        self.hud_enabled: bool = self.app_config.hud_enabled

        # Thread-safe Qt Signal Bridge
        self.bridge = SchedulerBridge(self)
        self.bridge.itemTriggered.connect(self._on_item_triggered_main_thread)
        self.bridge.wakeMissedTriggered.connect(self._handle_wake_missed_ui)
        self.bridge.togglePauseRequested.connect(self._toggle_active_timer_pause)
        self.bridge.toggleHudRequested.connect(self._toggle_hud)
        self.bridge.toggleMeetingModeRequested.connect(self._toggle_meeting_mode)

        # Meeting Mode & Microphone State
        self._mic_active: bool = False

        # Initialize Background Scheduler
        self.scheduler = ReminderScheduler(
            on_trigger_callback=self._on_trigger_background,
            on_wake_missed_callback=self._on_wake_missed_background,
        )

        # Scratchpad Auto-Save Debounce Timer (600ms)
        self._scratchpad_save_timer = QTimer(self)
        self._scratchpad_save_timer.setSingleShot(True)
        self._scratchpad_save_timer.setInterval(600)
        self._scratchpad_save_timer.timeout.connect(self._save_scratchpad_now)

        # AutoHotkey v2 Process Manager
        self.ahk_manager = AHKProcessManager(self)
        self.ahk_manager.statusChanged.connect(self._on_ahk_status_changed)
        self.ahk_manager.errorOccurred.connect(self._on_ahk_error)
        self.ahk_dialog: Optional[AHKHotstringsDialog] = None

        # Build UI Layout
        self._activity_timer_items: List[ScheduledItem] = []
        self._activity_rdv_items: List[ScheduledItem] = []
        self._history_items: List[dict] = []
        self.tab_shortcuts: List[QShortcut] = []

        self._build_ui()
        self._setup_tab_navigation_shortcuts()
        self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
        self._on_calendar_date_selected(self.mini_calendar.selected_date)

        # 1-Second Live UI Refresh Loop
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_loop)
        self._refresh_timer.start()
        self._refresh_loop()

        # Deferred startup checks
        QTimer.singleShot(600, self._check_missed_alarms)
        if self.hud_enabled:
            QTimer.singleShot(800, self._show_hud)
        if self.app_config.ahk_auto_start:
            QTimer.singleShot(1200, self._auto_start_ahk_script)
        if self.app_config.start_on_boot and not is_startup_enabled():
            set_startup_enabled(True)

    # ── Background Thread Callbacks (Emit via Bridge) ────────────────────────

    def _on_trigger_background(self, item: ScheduledItem) -> None:
        meeting_tag = " [🤫 Meeting]" if self.is_meeting_mode_active() else ""
        show_toast(
            f"⏰ {item.name}{meeting_tag}",
            f"Your {item.kind} ({item.category}) has triggered!",
            url=item.url,
            note=item.note,
        )
        self.bridge.itemTriggered.emit(item)

    def _on_wake_missed_background(self, missed_list: List[ScheduledItem]) -> None:
        self.bridge.wakeMissedTriggered.emit(missed_list)

    def _on_item_triggered_main_thread(self, item: ScheduledItem) -> None:
        self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
        self._popup_alarm(item)

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 6, 8, 6)
        root_layout.setSpacing(4)

        self._build_header(root_layout)
        self._build_hero_deck(root_layout)
        self._build_tabs(root_layout)
        self._build_active_queue(root_layout)
        self._on_main_tab_changed(self.main_tabs.currentIndex())

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        hdr = QHBoxLayout()
        hdr.setContentsMargins(2, 0, 2, 0)
        hdr.setSpacing(6)

        title_lbl = QLabel(f"⏰ {APP_TITLE}")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        hdr.addWidget(title_lbl)

        sub_lbl = QLabel("Ctrl+F8 | Keys 1-7")
        sub_lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']};")
        hdr.addWidget(sub_lbl)

        hdr.addStretch()

        # Meeting Mode Button (Left-click toggle, Right-click timed presets)
        self.btn_meeting_mode = QPushButton("🔔 Normal")
        self.btn_meeting_mode.setFixedHeight(23)
        self.btn_meeting_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_meeting_mode.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_meeting_mode.customContextMenuRequested.connect(self._show_meeting_mode_menu)
        self.btn_meeting_mode.clicked.connect(self._toggle_meeting_mode)
        hdr.addWidget(self.btn_meeting_mode)

        # App Opacity Slider on the left side of the HUD button (min=45, max=100, default=90)
        self.lbl_header_opacity = QLabel(f"🔆 {self.app_config.app_opacity}%")
        self.lbl_header_opacity.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.lbl_header_opacity.setToolTip("TimeSpace Window Opacity (45% - 100%)")
        hdr.addWidget(self.lbl_header_opacity)

        self.slider_header_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_header_opacity.setRange(45, 100)
        self.slider_header_opacity.setValue(self.app_config.app_opacity)
        self.slider_header_opacity.setFixedWidth(80)
        self.slider_header_opacity.setToolTip("Adjust TimeSpace window transparency (min 45%, max 100%, default 90%)")
        self.slider_header_opacity.valueChanged.connect(self._on_app_opacity_changed)
        hdr.addWidget(self.slider_header_opacity)

        hud_label = "📌 HUD: ON" if self.hud_enabled else "📌 HUD"
        self.btn_hud_toggle = QPushButton(hud_label)
        self.btn_hud_toggle.setFixedHeight(23)
        self.btn_hud_toggle.setToolTip("Toggle Floating Mini HUD")
        self.btn_hud_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hud_toggle.clicked.connect(self._toggle_hud)
        hdr.addWidget(self.btn_hud_toggle)

        parent_layout.addLayout(hdr)

    def _build_hero_deck(self, parent_layout: QVBoxLayout) -> None:
        self.hero_deck_frame = QFrame()
        self.hero_deck_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }}"
        )
        deck_layout = QHBoxLayout(self.hero_deck_frame)
        deck_layout.setContentsMargins(6, 5, 6, 5)
        deck_layout.setSpacing(8)

        # Left: Radial Progress Ring + Compact Emoji Play/Pause & Stop
        ring_col = QVBoxLayout()
        ring_col.setSpacing(3)
        self.ring = CircularProgressRing(
            self,
            size=UI_DIMENSIONS["ring_size"],
            ring_width=UI_DIMENSIONS["ring_width"],
        )
        ring_col.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        ring_btns = QHBoxLayout()
        ring_btns.setSpacing(4)
        self.btn_ring_play_pause = QPushButton("⏸️")
        self.btn_ring_play_pause.setFixedHeight(22)
        self.btn_ring_play_pause.setFixedWidth(40)
        self.btn_ring_play_pause.setToolTip("Pause / Resume active timer")
        self.btn_ring_play_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ring_play_pause.clicked.connect(self._toggle_active_timer_pause)

        self.btn_ring_stop = QPushButton("⏹️")
        self.btn_ring_stop.setObjectName("dangerBtn")
        self.btn_ring_stop.setFixedHeight(22)
        self.btn_ring_stop.setFixedWidth(40)
        self.btn_ring_stop.setToolTip("Stop active timer")
        self.btn_ring_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ring_stop.clicked.connect(self._stop_active_timer)

        ring_btns.addStretch()
        ring_btns.addWidget(self.btn_ring_play_pause)
        ring_btns.addWidget(self.btn_ring_stop)
        ring_btns.addStretch()
        ring_col.addLayout(ring_btns)
        deck_layout.addLayout(ring_col)

        # Right: Natural Language Quick Bar
        right_col = QVBoxLayout()
        right_col.setSpacing(4)

        nl_title = QLabel("✨ Quick Natural Schedule")
        nl_title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px; border: none;")
        right_col.addWidget(nl_title)

        nl_row = QHBoxLayout()
        nl_row.setSpacing(4)
        self.smart_entry = QLineEdit()
        self.smart_entry.setMinimumWidth(0)
        self.smart_entry.setPlaceholderText("e.g. 'Ring in 20m', 'Call client in 2 days', 'RDV at 14:30'")
        self.smart_entry.returnPressed.connect(self._on_smart_input_submit)
        nl_row.addWidget(self.smart_entry, 1)

        btn_create = QPushButton("⚡")
        btn_create.setObjectName("primaryBtn")
        btn_create.setFixedWidth(36)
        btn_create.setFixedHeight(25)
        btn_create.setToolTip("Create reminder from natural language query")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._on_smart_input_submit)
        nl_row.addWidget(btn_create)
        right_col.addLayout(nl_row)

        self.smart_feedback = QLabel("Tip: 'in 30m', 'in 3 days', 'tomorrow at 9am', or use tabs 1–7 below")
        self.smart_feedback.setWordWrap(True)
        self.smart_feedback.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")
        right_col.addWidget(self.smart_feedback)
        right_col.addStretch()

        deck_layout.addLayout(right_col, 1)
        parent_layout.addWidget(self.hero_deck_frame)

    def _build_tabs(self, parent_layout: QVBoxLayout) -> None:
        self.main_tabs = QTabWidget()
        self.main_tabs.setMinimumWidth(0)

        self.tab_timers = QWidget()
        self.tab_rdv = QWidget()
        self.tab_activity = QWidget()
        self.tab_scratchpad = QWidget()
        self.tab_go = GoTroubleshootingTab(self, custom_targets=self.app_config.custom_go_targets)
        self.tab_history = QWidget()
        self.tab_settings = QWidget()

        self.main_tabs.addTab(self.tab_timers, "1. Timers ⏳")
        self.main_tabs.addTab(self.tab_rdv, "2. RDV 📅")
        self.main_tabs.addTab(self.tab_activity, "3. Activity 📋")
        self.main_tabs.addTab(self.tab_scratchpad, "4. Scratchpad 📝")
        self.main_tabs.addTab(self.tab_go, "5. Go ⏱️")
        self.main_tabs.addTab(self.tab_history, "6. History 📜")
        self.main_tabs.addTab(self.tab_settings, "7. Settings ⚙️")

        self._init_timers_tab(self.tab_timers)
        self._init_rdv_tab(self.tab_rdv)
        self._init_activity_tab(self.tab_activity)
        self._init_scratchpad_tab(self.tab_scratchpad)
        self._init_go_scratchpad()
        self._init_history_tab(self.tab_history)
        self._init_settings_tab(self.tab_settings)

        self.tab_go.sendToScratchpad.connect(self._append_to_scratchpad)
        self.tab_go.diagnostic_completed.connect(self._on_go_diagnostic_completed)
        self.tab_go.customTargetsChanged.connect(self._on_custom_go_targets_changed)
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)

        parent_layout.addWidget(self.main_tabs, 5)

    def _on_main_tab_changed(self, index: int) -> None:
        """Dynamically hide/show the top Hero Deck and bottom Active Reminders Queue per section."""
        current_tab = self.main_tabs.widget(index)
        # Hide top Hero Deck on 4. Scratchpad, 5. Go, and 7. Settings
        if hasattr(self, "hero_deck_frame"):
            hide_hero = current_tab in (self.tab_scratchpad, self.tab_go, self.tab_settings)
            self.hero_deck_frame.setVisible(not hide_hero)
        # Hide bottom Active Reminders Queue on 3. Activity, 4. Scratchpad, 5. Go, and 6. History
        if hasattr(self, "active_queue_group"):
            hide_queue = current_tab in (
                self.tab_activity,
                self.tab_scratchpad,
                self.tab_go,
                self.tab_history,
            )
            self.active_queue_group.setVisible(not hide_queue)

    # ── Tab Navigation Keyboard Shortcuts (Keys 1 to 7) ──────────────────────

    def _setup_tab_navigation_shortcuts(self) -> None:
        """Bind keys 1–7 (and Alt+1..Alt+7) to navigate directly between tabs 1–7."""
        keys = [
            Qt.Key.Key_1,
            Qt.Key.Key_2,
            Qt.Key.Key_3,
            Qt.Key.Key_4,
            Qt.Key.Key_5,
            Qt.Key.Key_6,
            Qt.Key.Key_7,
        ]
        for idx, k in enumerate(keys):
            alt_sc = QShortcut(QKeySequence(Qt.Modifier.ALT | k), self)
            alt_sc.activated.connect(lambda i=idx: self._activate_tab_shortcut(i))
            self.tab_shortcuts.append(alt_sc)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._button_glow_filter = ButtonGlowFilter(self)
            app.installEventFilter(self._button_glow_filter)
    def _activate_tab_shortcut(self, index: int) -> None:
        if 0 <= index < self.main_tabs.count():
            self.main_tabs.setCurrentIndex(index)
            self.main_tabs.tabBar().setFocus()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and self.isVisible():
            key = event.key()  # type: ignore[attr-defined]
            mods = event.modifiers()  # type: ignore[attr-defined]
            if key == Qt.Key.Key_Escape:
                fw = QApplication.focusWidget()
                if fw is not None and self.isAncestorOf(fw):
                    fw.clearFocus()
                    self.main_tabs.tabBar().setFocus()
                    return True
            if mods == Qt.KeyboardModifier.NoModifier and Qt.Key.Key_1 <= key <= Qt.Key.Key_7:
                fw = QApplication.focusWidget()
                is_typing_input = False
                if isinstance(fw, (QLineEdit, QSpinBox)):
                    is_typing_input = not fw.isReadOnly()
                elif isinstance(fw, (QTextEdit, QPlainTextEdit)):
                    is_typing_input = not fw.isReadOnly()
                elif isinstance(fw, QComboBox):
                    is_typing_input = fw.isEditable()
                if not is_typing_input:
                    tab_idx = int(key - Qt.Key.Key_1)
                    self._activate_tab_shortcut(tab_idx)
                    return True
        return super().eventFilter(watched, event)

    # ── Tab 1: Timers (Compact Presets, Non-Overlapping Countdown & Inline Editing) ──

    def _init_timers_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(5)

        group = QGroupBox("⏳ Task & Follow-up Timer")
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(6, 6, 6, 6)
        g_layout.setSpacing(5)

        # Row 1: What to do + optional Reference / Client / Ticket #
        details_row = QHBoxLayout()
        details_row.setSpacing(4)

        DetailsLbl = QLabel("Task:")
        details_row.addWidget(DetailsLbl)
        self.entry_timer_name = QLineEdit()
        self.entry_timer_name.setMinimumWidth(0)
        self.entry_timer_name.setPlaceholderText("What to do (e.g. Call back client, Check backup)")
        self.entry_timer_name.returnPressed.connect(self._start_custom_timer)
        details_row.addWidget(self.entry_timer_name, 3)

        details_row.addWidget(QLabel("Ref:"))
        self.entry_timer_ref = QLineEdit()
        self.entry_timer_ref.setMinimumWidth(0)
        self.entry_timer_ref.setPlaceholderText("Client / Ticket #")
        self.entry_timer_ref.returnPressed.connect(self._start_custom_timer)
        details_row.addWidget(self.entry_timer_ref, 2)
        g_layout.addLayout(details_row)

        # Row 2: Optional Link / URL + Short Note
        attach_row = QHBoxLayout()
        attach_row.setSpacing(4)

        attach_row.addWidget(QLabel("🔗"))
        self.entry_timer_url = QLineEdit()
        self.entry_timer_url.setMinimumWidth(0)
        self.entry_timer_url.setPlaceholderText("https://... or file path (optional)")
        self.entry_timer_url.returnPressed.connect(self._start_custom_timer)
        attach_row.addWidget(self.entry_timer_url, 3)

        attach_row.addWidget(QLabel("📝"))
        self.entry_timer_note = QLineEdit()
        self.entry_timer_note.setMinimumWidth(0)
        self.entry_timer_note.setPlaceholderText("Short note / context (optional)")
        self.entry_timer_note.returnPressed.connect(self._start_custom_timer)
        attach_row.addWidget(self.entry_timer_note, 2)
        g_layout.addLayout(attach_row)

        # Row 3: Compact Quick Start Presets (15m, 30m, 1h, 2h) + Inline Edit Active Button (✏️)
        presets_row = QHBoxLayout()
        presets_row.setSpacing(4)
        lbl_quick = QLabel("Quick:")
        lbl_quick.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        presets_row.addWidget(lbl_quick)

        for label, mins in QUICK_TIMER_PRESETS:
            btn = QPushButton(label)
            btn.setMinimumWidth(0)
            btn.setFixedHeight(24)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Start or update {label} timer")
            btn.clicked.connect(lambda _checked=False, m=mins, lb=label: self._start_preset_timer(m, lb))
            presets_row.addWidget(btn, 1)

        self.btn_edit_active_timer = QPushButton("✏️")
        self.btn_edit_active_timer.setFixedWidth(32)
        self.btn_edit_active_timer.setFixedHeight(24)
        self.btn_edit_active_timer.setToolTip("Edit active / last-started timer or RDV details")
        self.btn_edit_active_timer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_active_timer.clicked.connect(self._edit_active_or_selected_item)
        presets_row.addWidget(self.btn_edit_active_timer)

        g_layout.addLayout(presets_row)

        # Row 4: Non-Overlapping Custom H / M / S SpinBoxes + Repeat + ▶️ / 💾 Button
        custom_row = QHBoxLayout()
        custom_row.setSpacing(4)
        lbl_cd = QLabel("Countdown:")
        lbl_cd.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        custom_row.addWidget(lbl_cd)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(0, 99)
        self.spin_h.setSuffix(" h")
        self.spin_h.setMinimumWidth(75)
        self.spin_h.setMaximumWidth(110)
        self.spin_h.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.spin_m = QSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setValue(15)
        self.spin_m.setSuffix(" m")
        self.spin_m.setMinimumWidth(75)
        self.spin_m.setMaximumWidth(110)
        self.spin_m.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.spin_s = QSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setSuffix(" s")
        self.spin_s.setMinimumWidth(75)
        self.spin_s.setMaximumWidth(110)
        self.spin_s.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        custom_row.addWidget(self.spin_h)
        custom_row.addWidget(self.spin_m)
        custom_row.addWidget(self.spin_s)

        self.chk_repeat = QCheckBox("🔁")
        self.chk_repeat.setToolTip("Repeat timer continuously")
        custom_row.addWidget(self.chk_repeat)
        custom_row.addStretch()

        self.btn_start_timer = QPushButton("▶️")
        self.btn_start_timer.setObjectName("primaryBtn")
        self.btn_start_timer.setFixedWidth(40)
        self.btn_start_timer.setFixedHeight(25)
        self.btn_start_timer.setToolTip("Start custom timer")
        self.btn_start_timer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start_timer.clicked.connect(self._start_custom_timer)
        custom_row.addWidget(self.btn_start_timer)

        self.btn_cancel_timer_edit = QPushButton("✖")
        self.btn_cancel_timer_edit.setObjectName("dangerBtn")
        self.btn_cancel_timer_edit.setFixedWidth(28)
        self.btn_cancel_timer_edit.setFixedHeight(25)
        self.btn_cancel_timer_edit.setToolTip("Cancel editing active timer")
        self.btn_cancel_timer_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_timer_edit.setVisible(False)
        self.btn_cancel_timer_edit.clicked.connect(self._cancel_timer_edit_mode)
        custom_row.addWidget(self.btn_cancel_timer_edit)

        g_layout.addLayout(custom_row)

        layout.addWidget(group)
        layout.addStretch()

    def _compose_timer_label(self, fallback_label: str) -> str:
        """Combine 'What to do' and optional 'Client / Ticket #' reference into a clean title."""
        task = self.entry_timer_name.text().strip()
        ref = self.entry_timer_ref.text().strip()
        base = task if task else fallback_label
        if ref:
            return f"[{ref}] {base}"
        return base

    @staticmethod
    def _split_timer_label(full_name: str) -> Tuple[str, str]:
        """Extract optional '[Ref] Task' into (ref, task) for inline editing."""
        cleaned = re.sub(r"^\[\d+m Early\]\s*", "", full_name.strip())
        m = re.match(r"^\[([^\]]+)\]\s*(.*)$", cleaned)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return "", cleaned

    def _start_preset_timer(self, minutes: int, preset_label: str) -> None:
        full_name = self._compose_timer_label(f"{preset_label} Reminder")
        has_ref = bool(self.entry_timer_ref.text().strip())
        cat = "🎫 Ticket" if has_ref else "📌 General"
        url = self.entry_timer_url.text().strip()
        note = self.entry_timer_note.text().strip()
        secs = minutes * 60

        # If currently editing an active timer, update it with the preset duration & current inputs
        if self._editing_timer_id and self.scheduler.get_item(self._editing_timer_id):
            repeat = secs if self.chk_repeat.isChecked() else 0
            self.scheduler.update_item(
                self._editing_timer_id,
                name=full_name,
                seconds_from_now=secs,
                repeat_sec=repeat,
                category=cat,
                url=url,
                note=note,
            )
            self.smart_feedback.setText(f"💾 Updated '{full_name}' ({preset_label})")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
            self._cancel_timer_edit_mode()
            self._refresh_loop()
            return

        self._last_started_timer_id = self._quick_add_timer(full_name, secs, cat, url=url, note=note)

    # ── Tab 2: RDV (Responsive Appointment Details, Emoji Buttons & Inline Editing) ──

    def _init_rdv_tab(self, parent: QWidget) -> None:
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(6)

        # Left column: Mini Calendar + Selected Day Agenda Preview
        cal_col = QVBoxLayout()
        cal_col.setSpacing(3)
        self.mini_calendar = MiniCalendar(self, on_date_selected=self._on_calendar_date_selected)
        self.mini_calendar.setMinimumWidth(185)
        self.mini_calendar.setMaximumWidth(230)
        cal_col.addWidget(self.mini_calendar)

        self.lbl_day_agenda = QLabel("No events on selected date")
        self.lbl_day_agenda.setWordWrap(True)
        self.lbl_day_agenda.setMaximumWidth(230)
        self.lbl_day_agenda.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 10px; padding: 3px 5px; border-radius: 4px;"
        )
        cal_col.addWidget(self.lbl_day_agenda)
        layout.addLayout(cal_col)

        # Right column: Responsive Appointment Details
        details_group = QGroupBox("⏰ Appointment Details")
        details_group.setMinimumWidth(0)
        d_layout = QVBoxLayout(details_group)
        d_layout.setContentsMargins(6, 6, 6, 6)
        d_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title_row.addWidget(QLabel("Event:"))
        self.entry_rdv_name = QLineEdit("Team Sync")
        self.entry_rdv_name.setMinimumWidth(0)
        self.entry_rdv_name.setPlaceholderText("Client, ticket #, or appointment")
        title_row.addWidget(self.entry_rdv_name, 1)
        d_layout.addLayout(title_row)

        self.time_picker = BigButtonsTimePicker(self, initial_hour=14, initial_minute=0)
        d_layout.addWidget(self.time_picker)

        rdv_attach_row = QHBoxLayout()
        rdv_attach_row.setSpacing(4)
        self.entry_rdv_url = QLineEdit()
        self.entry_rdv_url.setMinimumWidth(0)
        self.entry_rdv_url.setPlaceholderText("🔗 Link / URL")
        self.entry_rdv_note = QLineEdit()
        self.entry_rdv_note.setMinimumWidth(0)
        self.entry_rdv_note.setPlaceholderText("📝 Short note")
        rdv_attach_row.addWidget(self.entry_rdv_url, 1)
        rdv_attach_row.addWidget(self.entry_rdv_note, 1)
        d_layout.addLayout(rdv_attach_row)

        meta_grid = QGridLayout()
        meta_grid.setSpacing(3)

        meta_grid.addWidget(QLabel("Cat:"), 0, 0)
        self.combo_rdv_cat = QComboBox()
        self.combo_rdv_cat.setMinimumWidth(0)
        self.combo_rdv_cat.addItems(CATEGORIES)
        meta_grid.addWidget(self.combo_rdv_cat, 0, 1, 1, 3)

        meta_grid.addWidget(QLabel("Alert:"), 1, 0)
        self.combo_rdv_lead = QComboBox()
        self.combo_rdv_lead.setMinimumWidth(0)
        self.combo_rdv_lead.addItems(["At time (0m)", "5m before", "10m before", "15m before"])
        meta_grid.addWidget(self.combo_rdv_lead, 1, 1)

        meta_grid.addWidget(QLabel("Repeat:"), 1, 2)
        self.combo_rdv_repeat = QComboBox()
        self.combo_rdv_repeat.setMinimumWidth(0)
        self.combo_rdv_repeat.addItems(["None", "Daily", "Weekly", "Monthly"])
        meta_grid.addWidget(self.combo_rdv_repeat, 1, 3)
        meta_grid.setColumnStretch(1, 1)
        meta_grid.setColumnStretch(3, 1)
        d_layout.addLayout(meta_grid)

        action_row = QHBoxLayout()
        action_row.setSpacing(4)

        btn_export = QPushButton("📤 .ics")
        btn_export.setMinimumWidth(0)
        btn_export.setToolTip("Export RDVs to .ics file")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_calendar)

        btn_import = QPushButton("📥 .ics")
        btn_import.setMinimumWidth(0)
        btn_import.setToolTip("Import RDVs from .ics file")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self._import_calendar)

        self.btn_edit_rdv = QPushButton("✏️")
        self.btn_edit_rdv.setFixedWidth(30)
        self.btn_edit_rdv.setToolTip("Edit active / selected RDV")
        self.btn_edit_rdv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_rdv.clicked.connect(self._edit_active_or_selected_rdv)

        self.btn_add_rdv = QPushButton("➕ RDV")
        self.btn_add_rdv.setObjectName("primaryBtn")
        self.btn_add_rdv.setMinimumWidth(0)
        self.btn_add_rdv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_rdv.clicked.connect(self._add_rendez_vous)

        self.btn_cancel_rdv_edit = QPushButton("✖")
        self.btn_cancel_rdv_edit.setObjectName("dangerBtn")
        self.btn_cancel_rdv_edit.setFixedWidth(26)
        self.btn_cancel_rdv_edit.setToolTip("Cancel RDV edit")
        self.btn_cancel_rdv_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_rdv_edit.setVisible(False)
        self.btn_cancel_rdv_edit.clicked.connect(self._cancel_rdv_edit_mode)

        action_row.addWidget(btn_export)
        action_row.addWidget(btn_import)
        action_row.addWidget(self.btn_edit_rdv)
        action_row.addStretch()
        action_row.addWidget(self.btn_add_rdv)
        action_row.addWidget(self.btn_cancel_rdv_edit)
        d_layout.addLayout(action_row)

        layout.addWidget(details_group, 1)

    # ── Tab 3: Activity (Full-Height Timers & Rendez-vous Columns, No Bottom Queue) ──

    def _init_activity_tab(self, parent: QWidget) -> None:
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(6)

        # Left column: All Timers (expands 100% vertical height)
        t_group = QGroupBox("⏳ All Timers")
        t_layout = QVBoxLayout(t_group)
        t_layout.setContentsMargins(6, 6, 6, 6)
        t_layout.setSpacing(4)

        t_hdr = QHBoxLayout()
        t_hdr.setSpacing(4)
        self.lbl_timer_count = QLabel("0 active")
        self.lbl_timer_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        t_hdr.addWidget(self.lbl_timer_count)
        t_hdr.addStretch()

        btn_t_pause = QPushButton("⏸️")
        btn_t_pause.setFixedHeight(22)
        btn_t_pause.setToolTip("Pause / Resume selected timer")
        btn_t_pause.clicked.connect(self._activity_pause_timer)

        btn_t_edit = QPushButton("✏️")
        btn_t_edit.setFixedHeight(22)
        btn_t_edit.setToolTip("Edit selected timer details (or double-click item)")
        btn_t_edit.clicked.connect(self._activity_edit_timer)

        btn_t_del = QPushButton("🗑️")
        btn_t_del.setObjectName("dangerBtn")
        btn_t_del.setFixedHeight(22)
        btn_t_del.setToolTip("Delete selected timer")
        btn_t_del.clicked.connect(self._activity_delete_timer)

        t_hdr.addWidget(btn_t_pause)
        t_hdr.addWidget(btn_t_edit)
        t_hdr.addWidget(btn_t_del)
        t_layout.addLayout(t_hdr)

        self.activity_timer_lb = QListWidget()
        self.activity_timer_lb.setMinimumHeight(140)
        self.activity_timer_lb.itemSelectionChanged.connect(self._on_activity_timer_select)
        self.activity_timer_lb.itemDoubleClicked.connect(lambda _it: self._activity_edit_timer())
        t_layout.addWidget(self.activity_timer_lb, 1)

        t_detail_row = QHBoxLayout()
        t_detail_row.setSpacing(4)
        self.timer_detail = QLabel("Select or double-click a timer to edit.")
        self.timer_detail.setWordWrap(True)
        self.timer_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 4px 6px; border-radius: 4px;"
        )
        t_detail_row.addWidget(self.timer_detail, 1)

        self.btn_activity_timer_link = QPushButton("🔗")
        self.btn_activity_timer_link.setObjectName("successBtn")
        self.btn_activity_timer_link.setFixedHeight(24)
        self.btn_activity_timer_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activity_timer_link.setVisible(False)
        self.btn_activity_timer_link.clicked.connect(self._open_selected_activity_timer_link)
        t_detail_row.addWidget(self.btn_activity_timer_link)
        t_layout.addLayout(t_detail_row)
        layout.addWidget(t_group, 1)

        # Right column: All Rendez-vous (expands 100% vertical height)
        r_group = QGroupBox("📅 All Rendez-vous")
        r_layout = QVBoxLayout(r_group)
        r_layout.setContentsMargins(6, 6, 6, 6)
        r_layout.setSpacing(4)

        r_hdr = QHBoxLayout()
        r_hdr.setSpacing(4)
        self.lbl_rdv_count = QLabel("0 scheduled")
        self.lbl_rdv_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        r_hdr.addWidget(self.lbl_rdv_count)
        r_hdr.addStretch()

        btn_r_edit = QPushButton("✏️")
        btn_r_edit.setFixedHeight(22)
        btn_r_edit.setToolTip("Edit selected RDV details (or double-click item)")
        btn_r_edit.clicked.connect(self._activity_edit_rdv)

        btn_r_del = QPushButton("🗑️")
        btn_r_del.setObjectName("dangerBtn")
        btn_r_del.setFixedHeight(22)
        btn_r_del.setToolTip("Delete selected RDV")
        btn_r_del.clicked.connect(self._activity_delete_rdv)

        r_hdr.addWidget(btn_r_edit)
        r_hdr.addWidget(btn_r_del)
        r_layout.addLayout(r_hdr)

        self.activity_rdv_lb = QListWidget()
        self.activity_rdv_lb.setMinimumHeight(140)
        self.activity_rdv_lb.itemSelectionChanged.connect(self._on_activity_rdv_select)
        self.activity_rdv_lb.itemDoubleClicked.connect(lambda _it: self._activity_edit_rdv())
        r_layout.addWidget(self.activity_rdv_lb, 1)

        r_detail_row = QHBoxLayout()
        r_detail_row.setSpacing(4)
        self.rdv_detail = QLabel("Select or double-click an RDV to edit.")
        self.rdv_detail.setWordWrap(True)
        self.rdv_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 4px 6px; border-radius: 4px;"
        )
        r_detail_row.addWidget(self.rdv_detail, 1)

        self.btn_activity_rdv_link = QPushButton("🔗")
        self.btn_activity_rdv_link.setObjectName("successBtn")
        self.btn_activity_rdv_link.setFixedHeight(24)
        self.btn_activity_rdv_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activity_rdv_link.setVisible(False)
        self.btn_activity_rdv_link.clicked.connect(self._open_selected_activity_rdv_link)
        r_detail_row.addWidget(self.btn_activity_rdv_link)
        r_layout.addLayout(r_detail_row)
        layout.addWidget(r_group, 1)

    # ── Tab 4: Dual Upper & Lower Rich-Text Scratchpads + Tab 5 Go Scratchpad ──

    def _init_scratchpad_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self.scratchpad_splitter = QSplitter(Qt.Orientation.Vertical)
        self.scratchpad_splitter.setChildrenCollapsible(False)

        self.upper_scratchpad_pane = RichScratchpadPane(
            title="📝 Scratchpad 1 (Upper)",
            placeholder="Upper Scratchpad: Pin priority notes, commands, client numbers, or clickable URLs...",
            initial_text=self.scratchpad_state.upper_content,
            initial_html=self.scratchpad_state.upper_html,
            parent=self,
        )
        self.upper_scratchpad_text = self.upper_scratchpad_pane.editor
        self.upper_scratchpad_pane.contentModified.connect(self._on_scratchpad_modified)
        self.upper_scratchpad_pane.scheduleRequested.connect(self._on_scratchpad_schedule_requested)

        self.lower_scratchpad_pane = RichScratchpadPane(
            title="📝 Scratchpad 2 (Lower)",
            placeholder="Lower Scratchpad: Jot down time notes, ticket updates, or clickable URLs...",
            initial_text=self.scratchpad_state.content,
            initial_html=self.scratchpad_state.html,
            parent=self,
        )
        # Backward-compatible attribute aliases for lower scratchpad
        self.scratchpad_text = self.lower_scratchpad_pane.editor
        self.lbl_scratchpad_status = self.lower_scratchpad_pane.lbl_status
        self.btn_scratchpad_bold = self.lower_scratchpad_pane.btn_bold
        self.btn_scratchpad_color = self.lower_scratchpad_pane.btn_color
        self.lower_scratchpad_pane.contentModified.connect(self._on_scratchpad_modified)
        self.lower_scratchpad_pane.scheduleRequested.connect(self._on_scratchpad_schedule_requested)

        self.scratchpad_splitter.addWidget(self.upper_scratchpad_pane)
        self.scratchpad_splitter.addWidget(self.lower_scratchpad_pane)
        self.scratchpad_splitter.setStretchFactor(0, 1)
        self.scratchpad_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.scratchpad_splitter, 1)

    def _init_go_scratchpad(self) -> None:
        """Create and attach the 3rd rich-text Scratchpad inside Tab 5 ('5. Go ⏱️')."""
        self.go_scratchpad_pane = RichScratchpadPane(
            title="📝 Go Scratchpad (Notes & URLs)",
            placeholder="Go Scratchpad: Capture diagnostic snippets, endpoints, or clickable URLs (𝐁 Bold, 🎨 Color)...",
            initial_text=self.scratchpad_state.go_content,
            initial_html=self.scratchpad_state.go_html,
            parent=self.tab_go,
        )
        self.go_scratchpad_text = self.go_scratchpad_pane.editor
        self.go_scratchpad_pane.contentModified.connect(self._on_scratchpad_modified)
        self.go_scratchpad_pane.scheduleRequested.connect(self._on_scratchpad_schedule_requested)
        self.tab_go.attach_scratchpad_widget(self.go_scratchpad_pane)

    # ── Tab 6: Completed / Triggered History (No Bottom Queue + Delete Key) ──

    def _init_history_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(5)

        h_group = QGroupBox("📜 Completed & Triggered Reminders History")
        h_layout = QVBoxLayout(h_group)
        h_layout.setContentsMargins(6, 6, 6, 6)
        h_layout.setSpacing(4)

        h_hdr = QHBoxLayout()
        h_hdr.setSpacing(4)
        self.lbl_history_count = QLabel("0 logged")
        self.lbl_history_count.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")
        h_hdr.addWidget(self.lbl_history_count)
        h_hdr.addStretch()

        self.btn_open_history_link = QPushButton("🔗")
        self.btn_open_history_link.setObjectName("successBtn")
        self.btn_open_history_link.setFixedHeight(22)
        self.btn_open_history_link.setToolTip("Open attached link")
        self.btn_open_history_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_history_link.setVisible(False)
        self.btn_open_history_link.clicked.connect(self._open_selected_history_link)
        h_hdr.addWidget(self.btn_open_history_link)

        btn_copy_h = QPushButton("📋")
        btn_copy_h.setFixedHeight(22)
        btn_copy_h.setToolTip("Copy selected history entry")
        btn_copy_h.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_h.clicked.connect(self._copy_selected_history)
        h_hdr.addWidget(btn_copy_h)

        btn_del_h = QPushButton("🗑️")
        btn_del_h.setObjectName("dangerBtn")
        btn_del_h.setFixedHeight(22)
        btn_del_h.setToolTip("Delete selected entry (Delete key)")
        btn_del_h.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_h.clicked.connect(self._delete_selected_history)
        h_hdr.addWidget(btn_del_h)

        btn_clear_h = QPushButton("🧹")
        btn_clear_h.setObjectName("dangerBtn")
        btn_clear_h.setFixedHeight(22)
        btn_clear_h.setToolTip("Clear all history")
        btn_clear_h.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_h.clicked.connect(self._clear_history)
        h_hdr.addWidget(btn_clear_h)
        h_layout.addLayout(h_hdr)

        self.activity_history_lb = HistoryListWidget()
        self.activity_history_lb.setMinimumHeight(140)
        self.activity_history_lb.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.activity_history_lb.itemSelectionChanged.connect(self._on_activity_history_select)
        self.activity_history_lb.deleteKeyPressed.connect(self._delete_selected_history)
        h_layout.addWidget(self.activity_history_lb, 1)

        self.history_detail = QLabel("Select an entry above to inspect details (press Delete to remove).")
        self.history_detail.setWordWrap(True)
        self.history_detail.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
            f"font-size: 11px; padding: 5px 6px; border-radius: 4px;"
        )
        h_layout.addWidget(self.history_detail)

        layout.addWidget(h_group, 1)
        self._load_history_list()

    # ── Tab 7: Settings (No Top Timer + App Transparency Slider + Compact Emoji Controls) ──

    def _init_settings_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(6)

        s_group = QGroupBox("🔊 Sound, Transparency & System Preferences")
        s_layout = QVBoxLayout(s_group)
        s_layout.setContentsMargins(6, 6, 6, 6)
        s_layout.setSpacing(6)

        # Sound preset + preview
        row_tone = QHBoxLayout()
        row_tone.setSpacing(4)
        row_tone.addWidget(QLabel("Alarm Tone:"))
        self.combo_sound = QComboBox()
        self.combo_sound.setMinimumWidth(0)
        for key, label in SOUND_PRESETS.items():
            self.combo_sound.addItem(f"{key} — {label}", key)
        idx = self.combo_sound.findData(self.app_config.sound_type)
        if idx >= 0:
            self.combo_sound.setCurrentIndex(idx)
        row_tone.addWidget(self.combo_sound, 1)

        self.btn_preview = QPushButton("🔊")
        self.btn_preview.setFixedWidth(36)
        self.btn_preview.setToolTip("Preview alarm tone")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.clicked.connect(self._toggle_preview)
        row_tone.addWidget(self.btn_preview)
        s_layout.addLayout(row_tone)

        # Master Volume slider
        row_vol = QHBoxLayout()
        self.lbl_volume = QLabel(f"Master Volume: {self.app_config.volume}%")
        self.lbl_volume.setFixedWidth(155)
        row_vol.addWidget(self.lbl_volume)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.app_config.volume)
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"Master Volume: {v}%"))
        row_vol.addWidget(self.slider_volume, 1)
        s_layout.addLayout(row_vol)

        # Default App Window Transparency Slider (45% to 100%, default 90%, synced with Top Header Slider)
        row_app_opacity = QHBoxLayout()
        self.lbl_app_opacity = QLabel(f"App Transparency: {self.app_config.app_opacity}%")
        self.lbl_app_opacity.setFixedWidth(155)
        row_app_opacity.addWidget(self.lbl_app_opacity)

        self.slider_app_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_app_opacity.setRange(45, 100)
        self.slider_app_opacity.setValue(self.app_config.app_opacity)
        self.slider_app_opacity.valueChanged.connect(self._on_app_opacity_changed)
        row_app_opacity.addWidget(self.slider_app_opacity, 1)
        s_layout.addLayout(row_app_opacity)

        # Popup & Mini HUD Opacity slider (60% to 100%, default 90%)
        row_opacity = QHBoxLayout()
        self.lbl_opacity = QLabel(f"Popup & HUD Opacity: {self.app_config.overlay_opacity}%")
        self.lbl_opacity.setFixedWidth(155)
        row_opacity.addWidget(self.lbl_opacity)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 100)
        self.slider_opacity.setValue(self.app_config.overlay_opacity)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        row_opacity.addWidget(self.slider_opacity, 1)
        s_layout.addLayout(row_opacity)

        # Custom audio file
        row_file = QHBoxLayout()
        row_file.setSpacing(4)
        row_file.addWidget(QLabel("Audio File:"))
        self.lbl_sound_path = QLabel(self.app_config.custom_sound_path or "No file chosen")
        self.lbl_sound_path.setMinimumWidth(0)
        self.lbl_sound_path.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; padding: 3px 6px; border-radius: 4px;"
        )
        row_file.addWidget(self.lbl_sound_path, 1)

        btn_browse = QPushButton("📂")
        btn_browse.setFixedWidth(36)
        btn_browse.setToolTip("Browse custom audio file (.mp3 / .wav)")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_audio)
        row_file.addWidget(btn_browse)
        s_layout.addLayout(row_file)

        # Checkboxes & Snooze
        row_opts = QHBoxLayout()
        self.chk_escalate = QCheckBox("Gradual volume escalation")
        self.chk_escalate.setChecked(self.app_config.gradual_escalation)
        row_opts.addWidget(self.chk_escalate)

        self.chk_startup = QCheckBox("Launch at Windows boot")
        self.chk_startup.setChecked(is_startup_enabled() or self.app_config.start_on_boot)
        row_opts.addWidget(self.chk_startup)
        row_opts.addStretch()
        s_layout.addLayout(row_opts)

        row_bottom = QHBoxLayout()
        row_bottom.setSpacing(4)
        row_bottom.addWidget(QLabel("Snooze:"))
        self.combo_snooze = QComboBox()
        for opt in SNOOZE_OPTIONS:
            self.combo_snooze.addItem(f"{opt}m", opt)
        s_idx = self.combo_snooze.findData(self.app_config.default_snooze_minutes)
        if s_idx >= 0:
            self.combo_snooze.setCurrentIndex(s_idx)
        row_bottom.addWidget(self.combo_snooze)

        self.lbl_settings_saved = QLabel("")
        self.lbl_settings_saved.setStyleSheet(f"color: {COLORS['accent_success']}; font-weight: bold;")
        row_bottom.addWidget(self.lbl_settings_saved)
        row_bottom.addStretch()

        btn_save = QPushButton("💾")
        btn_save.setObjectName("successBtn")
        btn_save.setFixedWidth(40)
        btn_save.setToolTip("Save settings")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_settings)
        row_bottom.addWidget(btn_save)
        s_layout.addLayout(row_bottom)

        layout.addWidget(s_group)

        # ── Group 2: Discreet & Meeting Mode ──
        meeting_group = QGroupBox("🤫 Discreet & Meeting Mode")
        meeting_layout = QVBoxLayout(meeting_group)
        meeting_layout.setContentsMargins(8, 6, 8, 6)
        meeting_layout.setSpacing(6)

        meeting_row1 = QHBoxLayout()
        self.chk_meeting_auto_mic = QCheckBox("Auto-mute when microphone is in use (Teams, Zoom, Meet, etc.)")
        self.chk_meeting_auto_mic.setChecked(self.app_config.meeting_mode_auto_mic)
        self.chk_meeting_auto_mic.setToolTip("Automatically suppress alarm chimes when any conference app captures microphone audio")
        meeting_row1.addWidget(self.chk_meeting_auto_mic)
        meeting_row1.addStretch()
        meeting_layout.addLayout(meeting_row1)

        meeting_row2 = QHBoxLayout()
        self.chk_meeting_mute_sound = QCheckBox("Mute alarm sound in Meeting Mode (keep silent popups & toasts)")
        self.chk_meeting_mute_sound.setChecked(self.app_config.meeting_mode_mute_sound)
        self.chk_meeting_mute_sound.setToolTip("When checked, bottom-right popups and toasts appear silently without audio chime")
        meeting_row2.addWidget(self.chk_meeting_mute_sound)
        meeting_row2.addStretch()
        meeting_layout.addLayout(meeting_row2)

        meeting_status_row = QHBoxLayout()
        meeting_status_row.setSpacing(8)
        self.lbl_meeting_settings_status = QLabel("⚪ Idle • Audio Chimes Enabled")
        self.lbl_meeting_settings_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        meeting_status_row.addWidget(self.lbl_meeting_settings_status)
        meeting_status_row.addStretch()

        shortcut_hint = QLabel("Shortcut: Ctrl+Shift+M")
        shortcut_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        meeting_status_row.addWidget(shortcut_hint)

        btn_meeting_toggle_settings = QPushButton("Toggle Meeting Mode")
        btn_meeting_toggle_settings.setFixedHeight(24)
        btn_meeting_toggle_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_meeting_toggle_settings.clicked.connect(self._toggle_meeting_mode)
        meeting_status_row.addWidget(btn_meeting_toggle_settings)
        meeting_layout.addLayout(meeting_status_row)

        layout.addWidget(meeting_group)

        # ── Group 3: AutoHotkey v2 Text Expanders (Hotstrings) ──
        ahk_group = QGroupBox("⌨️ AutoHotkey v2 Text Expanders (Hotstrings)")
        ahk_layout = QVBoxLayout(ahk_group)
        ahk_layout.setContentsMargins(6, 6, 6, 6)
        ahk_layout.setSpacing(6)

        ahk_top_row = QHBoxLayout()
        ahk_top_row.setSpacing(6)

        btn_open_ahk = QPushButton("⚡ Set Up & Edit AHK v2 Hotstrings...")
        btn_open_ahk.setObjectName("primaryBtn")
        btn_open_ahk.setFixedHeight(28)
        btn_open_ahk.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_ahk.setToolTip("Open AutoHotkey v2 Hotstrings & Text Expanders Manager")
        btn_open_ahk.clicked.connect(self._open_ahk_manager_dialog)
        ahk_top_row.addWidget(btn_open_ahk)

        self.lbl_ahk_settings_status = QLabel("AHK v2: Checking...")
        self.lbl_ahk_settings_status.setStyleSheet("font-size: 11px;")
        ahk_top_row.addWidget(self.lbl_ahk_settings_status, 1)

        self.btn_ahk_quick_run = QPushButton("▶️ Run")
        self.btn_ahk_quick_run.setFixedHeight(28)
        self.btn_ahk_quick_run.setMinimumWidth(80)
        self.btn_ahk_quick_run.setToolTip("Run or reload AutoHotkey v2 hotstrings script")
        self.btn_ahk_quick_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ahk_quick_run.clicked.connect(self._quick_run_ahk_script)
        ahk_top_row.addWidget(self.btn_ahk_quick_run)

        self.btn_ahk_quick_stop = QPushButton("⏹️ Stop")
        self.btn_ahk_quick_stop.setFixedHeight(28)
        self.btn_ahk_quick_stop.setMinimumWidth(70)
        self.btn_ahk_quick_stop.setObjectName("dangerBtn")
        self.btn_ahk_quick_stop.setToolTip("Stop active AutoHotkey v2 hotstrings script")
        self.btn_ahk_quick_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ahk_quick_stop.clicked.connect(self._quick_stop_ahk_script)
        ahk_top_row.addWidget(self.btn_ahk_quick_stop)

        ahk_layout.addLayout(ahk_top_row)

        ahk_opt_row = QHBoxLayout()
        self.chk_ahk_auto_start = QCheckBox("Auto-run hotstrings script on TimeSpace launch")
        self.chk_ahk_auto_start.setChecked(self.app_config.ahk_auto_start)
        self.chk_ahk_auto_start.toggled.connect(self._on_ahk_auto_start_toggled)
        ahk_opt_row.addWidget(self.chk_ahk_auto_start)
        ahk_opt_row.addStretch()

        lbl_ahk_script_hint = QLabel("Script: data/hotstrings.ahk")
        lbl_ahk_script_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        ahk_opt_row.addWidget(lbl_ahk_script_hint)

        ahk_layout.addLayout(ahk_opt_row)
        layout.addWidget(ahk_group)

        self._update_ahk_settings_status_label()
        layout.addStretch()

    # ── Bottom Active Queue (Visible on Tabs 1, 2, 7; Hidden on 3, 4, 5, 6) ──

    def _build_active_queue(self, parent_layout: QVBoxLayout) -> None:
        self.active_queue_group = QGroupBox("Active Reminders Queue")
        q_layout = QVBoxLayout(self.active_queue_group)
        q_layout.setContentsMargins(6, 5, 6, 5)
        q_layout.setSpacing(4)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(4)
        self.lbl_queue_status = QLabel("All quiet")
        self.lbl_queue_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        hdr_row.addWidget(self.lbl_queue_status)
        hdr_row.addStretch()

        btn_pause_sel = QPushButton("⏸️")
        btn_pause_sel.setFixedHeight(22)
        btn_pause_sel.setToolTip("Pause / Resume selected reminder")
        btn_pause_sel.clicked.connect(self._toggle_selected_pause)
        hdr_row.addWidget(btn_pause_sel)

        btn_edit_sel = QPushButton("✏️")
        btn_edit_sel.setFixedHeight(22)
        btn_edit_sel.setToolTip("Edit selected reminder (or double-click item)")
        btn_edit_sel.clicked.connect(self._edit_selected_queue_item)
        hdr_row.addWidget(btn_edit_sel)

        btn_del_sel = QPushButton("🗑️")
        btn_del_sel.setObjectName("dangerBtn")
        btn_del_sel.setFixedHeight(22)
        btn_del_sel.setToolTip("Delete selected reminder")
        btn_del_sel.clicked.connect(self._delete_selected)
        hdr_row.addWidget(btn_del_sel)
        q_layout.addLayout(hdr_row)

        self.listbox = QListWidget()
        self.listbox.setMinimumHeight(110)
        self.listbox.itemDoubleClicked.connect(lambda _it: self._edit_selected_queue_item())
        q_layout.addWidget(self.listbox, 1)

        parent_layout.addWidget(self.active_queue_group, 3)

    # ── Action Slots, Inline Editing & Backend Wiring ────────────────────────

    def _quick_add_timer(
        self,
        name: str,
        seconds: int,
        category: str = "📌 General",
        url: str = "",
        note: str = "",
    ) -> str:
        item_id = self.scheduler.add_item(
            kind="timer",
            name=name,
            seconds_from_now=seconds,
            original_duration=seconds,
            category=category,
            url=url,
            note=note,
        )
        self._last_started_timer_id = item_id
        self.smart_feedback.setText(f"✅ Started '{name}' ({seconds // 60}m) — click ✏️ to edit")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self._refresh_loop()
        return item_id

    def _on_smart_input_submit(self) -> None:
        query = self.smart_entry.text().strip()
        parsed = NaturalParser.parse(query)
        if not parsed:
            self.smart_feedback.setText('❌ Unrecognized. Try: "Ring in 15 min", "Call Sam in 2 days", "RDV at 4PM"')
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 11px; border: none;")
            return

        if parsed["kind"] == "timer":
            self._last_started_timer_id = self.scheduler.add_item(
                kind="timer",
                name=parsed["name"],
                seconds_from_now=parsed["seconds_from_now"],
                original_duration=parsed["original_duration"],
            )
        else:
            self._last_started_rdv_id = self.scheduler.add_item(
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
        url = self.entry_timer_url.text().strip()
        note = self.entry_timer_note.text().strip()

        if self._editing_timer_id and self.scheduler.get_item(self._editing_timer_id):
            self.scheduler.update_item(
                self._editing_timer_id,
                name=full_name,
                seconds_from_now=total_sec,
                repeat_sec=repeat,
                category=cat,
                url=url,
                note=note,
            )
            self.smart_feedback.setText(f"💾 Updated timer '{full_name}'")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
            self._cancel_timer_edit_mode()
            self._refresh_loop()
            return

        self._last_started_timer_id = self.scheduler.add_item(
            kind="timer",
            name=full_name,
            seconds_from_now=total_sec,
            repeat_sec=repeat,
            original_duration=total_sec,
            category=cat,
            url=url,
            note=note,
        )
        self.smart_feedback.setText(f"✅ Started timer '{full_name}' — click ✏️ to edit")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
        self.entry_timer_name.clear()
        self.entry_timer_ref.clear()
        self.entry_timer_url.clear()
        self.entry_timer_note.clear()
        self._refresh_loop()

    def _begin_edit_timer(self, item: ScheduledItem) -> None:
        """Populate Tab 1 inputs from an active ScheduledItem (timer) and switch ▶️ to 💾."""
        self._editing_timer_id = item.id
        ref, task = self._split_timer_label(item.name)
        self.entry_timer_name.setText(task)
        self.entry_timer_ref.setText(ref)
        self.entry_timer_url.setText(item.url)
        self.entry_timer_note.setText(item.note)
        self.chk_repeat.setChecked(item.repeat_sec > 0)

        now = time.time()
        rem = int(item.remaining_paused if item.is_paused else max(1.0, item.target_time - now))
        m, s = divmod(rem, 60)
        h, m = divmod(m, 60)
        self.spin_h.setValue(min(99, h))
        self.spin_m.setValue(m)
        self.spin_s.setValue(s)

        self.btn_start_timer.setText("💾")
        self.btn_start_timer.setObjectName("successBtn")
        self.btn_start_timer.setToolTip(f"Save changes to '{item.name}'")
        self.btn_start_timer.style().unpolish(self.btn_start_timer)
        self.btn_start_timer.style().polish(self.btn_start_timer)
        self.btn_cancel_timer_edit.setVisible(True)

        self.main_tabs.setCurrentWidget(self.tab_timers)
        self.entry_timer_name.setFocus()
        self.smart_feedback.setText(f"✏️ Editing '{item.name}' — modify fields and click 💾 (or a preset)")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_link']}; font-size: 11px; border: none;")

    def _cancel_timer_edit_mode(self) -> None:
        self._editing_timer_id = None
        self.btn_start_timer.setText("▶️")
        self.btn_start_timer.setObjectName("primaryBtn")
        self.btn_start_timer.setToolTip("Start custom timer")
        self.btn_start_timer.style().unpolish(self.btn_start_timer)
        self.btn_start_timer.style().polish(self.btn_start_timer)
        self.btn_cancel_timer_edit.setVisible(False)
        self.entry_timer_name.clear()
        self.entry_timer_ref.clear()
        self.entry_timer_url.clear()
        self.entry_timer_note.clear()

    def _begin_edit_rdv(self, item: ScheduledItem) -> None:
        """Populate Tab 2 inputs from an active ScheduledItem (rendez-vous) and switch ➕ RDV to 💾 RDV."""
        self._editing_rdv_id = item.id
        clean_name = re.sub(r"^\[\d+m Early\]\s*", "", item.name.strip())
        self.entry_rdv_name.setText(clean_name)
        self.entry_rdv_url.setText(item.url)
        self.entry_rdv_note.setText(item.note)

        event_ts = item.target_time + max(0, item.lead_time_min) * 60
        dt = datetime.datetime.fromtimestamp(event_ts)
        self.mini_calendar._on_day_clicked(dt.date())
        self.time_picker.set_time(dt.hour, dt.minute)

        cat_idx = self.combo_rdv_cat.findText(item.category)
        if cat_idx >= 0:
            self.combo_rdv_cat.setCurrentIndex(cat_idx)

        lead_map = {0: 0, 5: 1, 10: 2, 15: 3}
        self.combo_rdv_lead.setCurrentIndex(lead_map.get(item.lead_time_min, 0))

        rep_idx = self.combo_rdv_repeat.findText((item.repeat_rule or "none").capitalize())
        if rep_idx >= 0:
            self.combo_rdv_repeat.setCurrentIndex(rep_idx)

        self.btn_add_rdv.setText("💾 RDV")
        self.btn_add_rdv.setObjectName("successBtn")
        self.btn_add_rdv.style().unpolish(self.btn_add_rdv)
        self.btn_add_rdv.style().polish(self.btn_add_rdv)
        self.btn_cancel_rdv_edit.setVisible(True)

        self.main_tabs.setCurrentWidget(self.tab_rdv)
        self.entry_rdv_name.setFocus()
        self.smart_feedback.setText(f"✏️ Editing RDV '{clean_name}' — modify details and click 💾 RDV")
        self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_link']}; font-size: 11px; border: none;")

    def _cancel_rdv_edit_mode(self) -> None:
        self._editing_rdv_id = None
        self.btn_add_rdv.setText("➕ RDV")
        self.btn_add_rdv.setObjectName("primaryBtn")
        self.btn_add_rdv.style().unpolish(self.btn_add_rdv)
        self.btn_add_rdv.style().polish(self.btn_add_rdv)
        self.btn_cancel_rdv_edit.setVisible(False)

    def _edit_selected_queue_item(self) -> None:
        row = self.listbox.currentRow()
        if 0 <= row < len(self.scheduler.items):
            it = self.scheduler.items[row]
            if it.kind == "timer":
                self._begin_edit_timer(it)
            else:
                self._begin_edit_rdv(it)

    def _edit_active_or_selected_item(self) -> None:
        """Load the selected queue item, last-started timer, or active timer/RDV into inline edit mode."""
        row = self.listbox.currentRow()
        if 0 <= row < len(self.scheduler.items):
            self._edit_selected_queue_item()
            return
        if self._last_started_timer_id:
            it = self.scheduler.get_item(self._last_started_timer_id)
            if it:
                self._begin_edit_timer(it)
                return
        active = self.scheduler.get_active_timer() or self.scheduler.get_nearest_item()
        if active:
            if active.kind == "timer":
                self._begin_edit_timer(active)
            else:
                self._begin_edit_rdv(active)
        else:
            self.smart_feedback.setText("ℹ️ Start a timer or RDV first, then click ✏️ (or double-click it) to edit.")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")

    def _edit_active_or_selected_rdv(self) -> None:
        if self._last_started_rdv_id:
            it = self.scheduler.get_item(self._last_started_rdv_id)
            if it and it.kind == "rendez-vous":
                self._begin_edit_rdv(it)
                return
        rdvs = [it for it in self.scheduler.items if it.kind == "rendez-vous"]
        if rdvs:
            self._begin_edit_rdv(rdvs[0])
        else:
            self.smart_feedback.setText("ℹ️ No active RDV to edit yet. Add one with ➕ RDV first.")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; border: none;")

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

        if self._editing_rdv_id and self.scheduler.get_item(self._editing_rdv_id):
            self.scheduler.update_item(
                self._editing_rdv_id,
                name=name,
                seconds_from_now=delta,
                repeat_rule=rule,
                category=cat,
                lead_time_min=lead_time,
                url=url,
                note=note,
                anchor_day=d_val.day if rule == "monthly" else 0,
            )
            self._cancel_rdv_edit_mode()
            self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
            self._on_calendar_date_selected(d_val)
            self.smart_feedback.setText(f"💾 Updated RDV '{name}' on {dt.strftime('%b %d at %H:%M')}")
            self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
            self._refresh_loop()
            return

        self._last_started_rdv_id = self.scheduler.add_item(
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
                f"font-size: 10px; font-weight: bold; padding: 3px 5px; border-radius: 4px;"
            )
        else:
            self.lbl_day_agenda.setText(f"{d_val.strftime('%b %d')}: No events")
            self.lbl_day_agenda.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; "
                f"font-size: 10px; padding: 3px 5px; border-radius: 4px;"
            )

    def _toggle_active_timer_pause(self) -> None:
        active = self.scheduler.get_active_timer()
        if active:
            now_paused = self.scheduler.toggle_pause(active.id)
            self.btn_ring_play_pause.setText("▶️" if now_paused else "⏸️")
        else:
            nearest = self.scheduler.get_nearest_item()
            if nearest:
                self.scheduler.toggle_pause(nearest.id)
        self._refresh_loop()

    def _stop_active_timer(self) -> None:
        active = self.scheduler.get_active_timer()
        if active:
            self.scheduler.remove_item(active.id)
            self.btn_ring_play_pause.setText("⏸️")
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

    # ── Multi-Scratchpad Actions & Persistence ───────────────────────────────

    def _toggle_scratchpad_bold(self) -> None:
        self.lower_scratchpad_pane.toggle_bold()

    def _show_scratchpad_color_menu(self) -> None:
        self.lower_scratchpad_pane.show_color_menu()

    def _apply_scratchpad_color(self, hex_color: str) -> None:
        self.lower_scratchpad_pane.apply_color(hex_color)

    def _insert_scratchpad_timestamp(self) -> None:
        self.lower_scratchpad_pane.insert_timestamp()

    def _copy_scratchpad(self) -> None:
        self.lower_scratchpad_pane.copy_all()

    def _clear_scratchpad(self) -> None:
        self.lower_scratchpad_pane.clear_notes()

    def _on_scratchpad_modified(self) -> None:
        self._scratchpad_save_timer.start()

    def _save_scratchpad_now(self) -> None:
        now_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        upper_plain = self.upper_scratchpad_text.toPlainText()
        lower_plain = self.scratchpad_text.toPlainText()
        go_plain = self.go_scratchpad_text.toPlainText()

        self.scratchpad_state.upper_content = upper_plain
        self.scratchpad_state.upper_html = self.upper_scratchpad_text.toHtml() if upper_plain.strip() else ""
        self.scratchpad_state.content = lower_plain
        self.scratchpad_state.html = self.scratchpad_text.toHtml() if lower_plain.strip() else ""
        self.scratchpad_state.go_content = go_plain
        self.scratchpad_state.go_html = self.go_scratchpad_text.toHtml() if go_plain.strip() else ""
        self.scratchpad_state.updated_at = now_stamp

        Storage.save_scratchpad(self.scratchpad_state)
        for pane in (self.upper_scratchpad_pane, self.lower_scratchpad_pane, self.go_scratchpad_pane):
            pane.lbl_status.setText(f"Saved {now_stamp}")
            pane.lbl_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")

    def _append_to_scratchpad(self, text: str) -> None:
        """Append Go diagnostic output to the Go Scratchpad (Tab 5) and Lower Scratchpad (Tab 4)."""
        cleaned = text.strip()
        if not cleaned:
            return
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for editor in (self.go_scratchpad_text, self.scratchpad_text):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if editor.toPlainText().strip():
                cursor.insertText("\n\n")

            header_fmt = QTextCharFormat()
            header_fmt.setForeground(QColor(COLORS["accent_link"]))
            header_fmt.setFontWeight(QFont.Weight.Bold)
            cursor.insertText(f"[{stamp}] — Go Diagnostic Output:\n", header_fmt)

            body_fmt = QTextCharFormat()
            body_fmt.setForeground(QColor(COLORS["text"]))
            body_fmt.setFontWeight(QFont.Weight.Normal)
            cursor.insertText(f"{cleaned}\n", body_fmt)

            editor.setTextCursor(cursor)
            sb = editor.verticalScrollBar()
            sb.setValue(sb.maximum())
        self._save_scratchpad_now()

    def _on_scratchpad_schedule_requested(self, task_text: str, extracted_url: str, mode_minutes: int) -> None:
        """Schedule highlighted Scratchpad text as a Timer/RDV or pre-fill Tab 1 / Tab 2 forms."""
        clean_title = task_text.strip()
        if extracted_url and extracted_url in clean_title:
            stripped = clean_title.replace(extracted_url, "").strip(" -—:|")
            if stripped:
                clean_title = stripped

        if mode_minutes == 0:
            parsed = NaturalParser.parse(task_text)
            if parsed:
                if parsed["kind"] == "timer":
                    self._last_started_timer_id = self.scheduler.add_item(
                        kind="timer",
                        name=parsed["name"],
                        seconds_from_now=parsed["seconds_from_now"],
                        original_duration=parsed["original_duration"],
                        url=extracted_url,
                    )
                else:
                    self._last_started_rdv_id = self.scheduler.add_item(
                        kind="rendez-vous",
                        name=parsed["name"],
                        seconds_from_now=parsed["seconds_from_now"],
                        url=extracted_url,
                    )
                    self.mini_calendar.set_event_dates(self.scheduler.get_all_event_dates())
                self.smart_feedback.setText(f"⏰ Scheduled {parsed['display_str']} from Scratchpad")
                self.smart_feedback.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; border: none;")
                self._refresh_loop()
            return

        if mode_minutes > 0:
            self._quick_add_timer(
                clean_title or f"{mode_minutes}m Note Reminder",
                mode_minutes * 60,
                category="📌 General",
                url=extracted_url,
            )
            return

        if mode_minutes == -1:
            self._cancel_timer_edit_mode()
            self.entry_timer_name.setText(clean_title)
            if extracted_url:
                self.entry_timer_url.setText(extracted_url)
            self.main_tabs.setCurrentWidget(self.tab_timers)
            self.entry_timer_name.setFocus()
            return

        if mode_minutes == -2:
            self._cancel_rdv_edit_mode()
            self.entry_rdv_name.setText(clean_title)
            if extracted_url:
                self.entry_rdv_url.setText(extracted_url)
            self.main_tabs.setCurrentWidget(self.tab_rdv)
            self.entry_rdv_name.setFocus()

    def _on_custom_go_targets_changed(self, targets: list) -> None:
        """Persist updated custom target bookmarks from 5. Go into AppConfig."""
        self.app_config.custom_go_targets = list(targets or [])
        Storage.save_config(self.app_config)

    def _on_go_diagnostic_completed(self, payload: dict) -> None:
        action = str(payload.get("action", "diag"))
        target = str(payload.get("target", ""))
        success = bool(payload.get("success", False))
        status_label = "Diag PASS" if success else "Diag FAIL"
        out_summary = str(payload.get("output", "") or "").splitlines()
        first_line = out_summary[-1] if out_summary else ""
        Storage.add_history_entry(
            HistoryEntry(
                name=f"[Go:{action}] {target}",
                kind="diagnostic",
                category="💼 Work",
                completed_at=datetime.datetime.now().strftime("%b %d, %H:%M:%S"),
                status=status_label,
                note=first_line[:140],
            )
        )
        self._load_history_list()

    # ── Activity & History Helpers ───────────────────────────────────────────

    def _fmt_remain(self, item: ScheduledItem, now: float) -> str:
        rem = int(item.remaining_paused if item.is_paused else max(0.0, item.target_time - now))
        prefix = "⏸ " if item.is_paused else ""
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
            parts = [f"📌 {it.name}", f"⏱ {self._fmt_remain(it, now)}", f"🔔 {self._fmt_target(it)} (🔁 {rep})"]
            if it.note:
                parts.append(f"📝 {it.note}")
            if it.url:
                parts.append(f"🔗 {it.url}")
            self.timer_detail.setText(" | ".join(parts))
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
            self.rdv_detail.setText(" | ".join(parts))
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

    def _activity_edit_timer(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            self._begin_edit_timer(self._activity_timer_items[row])

    def _activity_edit_rdv(self) -> None:
        row = self.activity_rdv_lb.currentRow()
        if 0 <= row < len(self._activity_rdv_items):
            self._begin_edit_rdv(self._activity_rdv_items[row])

    def _activity_delete_timer(self) -> None:
        row = self.activity_timer_lb.currentRow()
        if 0 <= row < len(self._activity_timer_items):
            self.scheduler.remove_item(self._activity_timer_items[row].id)
            self.timer_detail.setText("Select or double-click a timer to edit.")
            self.btn_activity_timer_link.setVisible(False)
            self._refresh_loop()

    def _activity_delete_rdv(self) -> None:
        row = self.activity_rdv_lb.currentRow()
        if 0 <= row < len(self._activity_rdv_items):
            self.scheduler.remove_item(self._activity_rdv_items[row].id)
            self.rdv_detail.setText("Select or double-click an RDV to edit.")
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
        self.lbl_history_count.setText(f"{cnt} entry(s)" if cnt else "0 logged")
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
            self.history_detail.setText(" | ".join(parts))
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
            self.history_detail.setText(f"✅ Copied: {line}")

    def _delete_selected_history(self) -> None:
        """Delete selected individual item(s) from the History list when Delete key or 🗑️ is pressed."""
        selected_indexes = [idx.row() for idx in self.activity_history_lb.selectedIndexes()]
        if not selected_indexes and self.activity_history_lb.currentRow() >= 0:
            selected_indexes = [self.activity_history_lb.currentRow()]
        if not selected_indexes:
            return
        removed = Storage.delete_history_indices(selected_indexes)
        if removed > 0:
            self._load_history_list()
            self.history_detail.setText(f"🗑️ Removed {removed} history entry(s).")

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
            self.history_detail.setText("Select an entry above to inspect details (press Delete to remove).")

    # ── Settings, Transparency & Audio Handlers ──────────────────────────────

    def _toggle_preview(self) -> None:
        if self.is_previewing:
            self.sound_player.stop_preview()
            self.btn_preview.setText("🔊")
            self.is_previewing = False
        else:
            snd_type = self.combo_sound.currentData() or "gentle"
            custom_p = self.lbl_sound_path.text()
            vol = self.slider_volume.value()
            self.sound_player.start_preview(snd_type, "" if custom_p == "No file chosen" else custom_p, volume=vol)
            self.btn_preview.setText("⏹️")
            self.is_previewing = True
            QTimer.singleShot(3500, self._reset_preview_btn)

    def _reset_preview_btn(self) -> None:
        self.btn_preview.setText("🔊")
        self.is_previewing = False

    def _browse_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav);;All Files (*.*)")
        if path:
            self.lbl_sound_path.setText(path)
            idx = self.combo_sound.findData("custom")
            if idx >= 0:
                self.combo_sound.setCurrentIndex(idx)

    def _on_app_opacity_changed(self, value: int) -> None:
        """Sync the Top Header opacity slider and Settings App Transparency slider (45%..100%) and apply to window."""
        clamped = max(45, min(100, int(value)))
        self.app_config.app_opacity = clamped

        if hasattr(self, "lbl_header_opacity"):
            self.lbl_header_opacity.setText(f"🔆 {clamped}%")
        if hasattr(self, "slider_header_opacity") and self.slider_header_opacity.value() != clamped:
            self.slider_header_opacity.blockSignals(True)
            self.slider_header_opacity.setValue(clamped)
            self.slider_header_opacity.blockSignals(False)

        if hasattr(self, "lbl_app_opacity"):
            self.lbl_app_opacity.setText(f"App Transparency: {clamped}%")
        if hasattr(self, "slider_app_opacity") and self.slider_app_opacity.value() != clamped:
            self.slider_app_opacity.blockSignals(True)
            self.slider_app_opacity.setValue(clamped)
            self.slider_app_opacity.blockSignals(False)

        win = self.window()
        if win is not None:
            win.setWindowOpacity(clamped / 100.0)

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
        self.app_config.app_opacity = max(45, min(100, self.slider_app_opacity.value()))
        self.app_config.overlay_opacity = max(60, min(100, self.slider_opacity.value()))
        self.app_config.default_snooze_minutes = int(self.combo_snooze.currentData() or 5)
        self.app_config.gradual_escalation = self.chk_escalate.isChecked()
        self.app_config.start_on_boot = self.chk_startup.isChecked()
        if hasattr(self, "chk_meeting_auto_mic"):
            self.app_config.meeting_mode_auto_mic = self.chk_meeting_auto_mic.isChecked()
        if hasattr(self, "chk_meeting_mute_sound"):
            self.app_config.meeting_mode_mute_sound = self.chk_meeting_mute_sound.isChecked()
        if hasattr(self, "chk_ahk_auto_start"):
            self.app_config.ahk_auto_start = self.chk_ahk_auto_start.isChecked()

        Storage.save_config(self.app_config)
        self.sound_player.update_config(self.app_config)
        self._on_app_opacity_changed(self.app_config.app_opacity)
        self._on_opacity_slider_changed(self.app_config.overlay_opacity)
        set_startup_enabled(self.app_config.start_on_boot)

        self.lbl_settings_saved.setText("✅ Saved!")
        QTimer.singleShot(3000, lambda: self.lbl_settings_saved.setText(""))

    # ── AutoHotkey v2 Text Expanders Controller ──────────────────────────────

    def _update_ahk_settings_status_label(self) -> None:
        if not hasattr(self, "lbl_ahk_settings_status"):
            return
        exe = find_ahk_v2_exe(self.app_config.ahk_v2_exe_path)
        if not exe:
            self.lbl_ahk_settings_status.setText("⚠️ AHK v2 Not Found")
            self.lbl_ahk_settings_status.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 11px;")
        elif self.ahk_manager.is_running():
            pid = self.ahk_manager.get_pid()
            self.lbl_ahk_settings_status.setText(f"🟢 Running (PID: {pid})")
            self.lbl_ahk_settings_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_ahk_settings_status.setText(f"⚪ Ready ({os.path.basename(exe)}) • Stopped")
            self.lbl_ahk_settings_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

    def _on_ahk_status_changed(self, running: bool, pid: int) -> None:
        self._update_ahk_settings_status_label()

    def _on_ahk_error(self, err: str) -> None:
        self._update_ahk_settings_status_label()

    def _on_ahk_auto_start_toggled(self, checked: bool) -> None:
        self.app_config.ahk_auto_start = checked
        Storage.save_config(self.app_config)

    def _auto_start_ahk_script(self) -> None:
        script_file = self.app_config.ahk_script_path or DEFAULT_AHK_SCRIPT_FILE
        if not os.path.exists(script_file):
            items = Storage.load_hotstrings()
            code = generate_ahk_v2_script(items)
            Storage.save_ahk_script_text(code, script_file)
        self.ahk_manager.start_script(script_file, self.app_config.ahk_v2_exe_path)

    def _quick_run_ahk_script(self) -> None:
        script_file = self.app_config.ahk_script_path or DEFAULT_AHK_SCRIPT_FILE
        if not os.path.exists(script_file):
            items = Storage.load_hotstrings()
            code = generate_ahk_v2_script(items)
            Storage.save_ahk_script_text(code, script_file)
        self.ahk_manager.start_script(script_file, self.app_config.ahk_v2_exe_path)

    def _quick_stop_ahk_script(self) -> None:
        self.ahk_manager.stop_script()

    def _open_ahk_manager_dialog(self) -> None:
        if self.ahk_dialog is None or not self.ahk_dialog.isVisible():
            self.ahk_dialog = AHKHotstringsDialog(self, self.app_config, self.ahk_manager)
            self.ahk_dialog.show()
            self.ahk_dialog.raise_()
            self.ahk_dialog.activateWindow()
        else:
            self.ahk_dialog.raise_()
            self.ahk_dialog.activateWindow()

    # ── Mini HUD Controller ──────────────────────────────────────────────────

    def _toggle_hud(self) -> None:
        if self.hud and self.hud.isVisible():
            self._save_hud_pos()
            self.hud.hide()
            self.hud_enabled = False
            self.btn_hud_toggle.setText("📌 HUD")
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
        self.btn_hud_toggle.setText("📌 HUD")

    def _save_hud_pos(self) -> None:
        if self.hud:
            pos = self.hud.pos()
            self.app_config.hud_x = pos.x()
            self.app_config.hud_y = pos.y()
            self.app_config.hud_enabled = self.hud_enabled
            Storage.save_config(self.app_config)

    # ── Discreet & Meeting Mode Controller ───────────────────────────────────

    def is_meeting_mode_active(self) -> bool:
        """Return True if meeting mode / audio mute is currently active."""
        now = time.time()
        # 1. Manual meeting mode override
        if self.app_config.meeting_mode_enabled:
            if self.app_config.meeting_mode_until > 0.0:
                if now < self.app_config.meeting_mode_until:
                    return True
                else:
                    # Timed mute expired
                    self.app_config.meeting_mode_enabled = False
                    self.app_config.meeting_mode_until = 0.0
                    Storage.save_config(self.app_config)
            else:
                return True

        # 2. Automatic microphone capture detection
        if self.app_config.meeting_mode_auto_mic and getattr(self, "_mic_active", False):
            return True

        return False

    def _toggle_meeting_mode(self) -> None:
        """Toggle manual meeting mode ON or OFF."""
        if self.is_meeting_mode_active():
            # Turn OFF (clear manual mute and timed mute)
            self.app_config.meeting_mode_enabled = False
            self.app_config.meeting_mode_until = 0.0
        else:
            # Turn ON (manual indefinite mute)
            self.app_config.meeting_mode_enabled = True
            self.app_config.meeting_mode_until = 0.0

        Storage.save_config(self.app_config)
        self._update_meeting_mode_ui()

    def _show_meeting_mode_menu(self, pos: QPoint) -> None:
        """Context menu offering quick timed mute presets."""
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {COLORS['surface']}; color: {COLORS['text']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px; }}"
            f"QMenu::item {{ padding: 5px 20px 5px 10px; border-radius: 3px; }}"
            f"QMenu::item:selected {{ background-color: {COLORS['accent']}; color: #ffffff; }}"
        )

        def set_mute_duration(minutes: int):
            self.app_config.meeting_mode_enabled = True
            self.app_config.meeting_mode_until = time.time() + (minutes * 60)
            Storage.save_config(self.app_config)
            self._update_meeting_mode_ui()

        def set_mute_until_end_of_day():
            now = datetime.datetime.now()
            end_hour = 17 if now.hour < 17 else (18 if now.hour < 18 else 23)
            target = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            self.app_config.meeting_mode_enabled = True
            self.app_config.meeting_mode_until = target.timestamp()
            Storage.save_config(self.app_config)
            self._update_meeting_mode_ui()

        def set_mute_indefinite():
            self.app_config.meeting_mode_enabled = True
            self.app_config.meeting_mode_until = 0.0
            Storage.save_config(self.app_config)
            self._update_meeting_mode_ui()

        def turn_off():
            self.app_config.meeting_mode_enabled = False
            self.app_config.meeting_mode_until = 0.0
            Storage.save_config(self.app_config)
            self._update_meeting_mode_ui()

        a_30m = menu.addAction("⚡ Mute for 30 Minutes")
        a_30m.triggered.connect(lambda: set_mute_duration(30))

        a_1h = menu.addAction("⚡ Mute for 1 Hour")
        a_1h.triggered.connect(lambda: set_mute_duration(60))

        a_2h = menu.addAction("⚡ Mute for 2 Hours")
        a_2h.triggered.connect(lambda: set_mute_duration(120))

        a_eod = menu.addAction("📅 Mute Until End of Day (17:00)")
        a_eod.triggered.connect(set_mute_until_end_of_day)

        a_indef = menu.addAction("♾️ Mute Indefinitely")
        a_indef.triggered.connect(set_mute_indefinite)

        menu.addSeparator()

        a_off = menu.addAction("🔔 Turn Off Meeting Mode (Audio ON)")
        a_off.triggered.connect(turn_off)

        menu.exec(self.btn_meeting_mode.mapToGlobal(pos))

    def _update_meeting_mode_ui(self) -> None:
        """Update Header button and Settings status label reflecting current meeting mode state."""
        if not hasattr(self, "btn_meeting_mode"):
            return
        active = self.is_meeting_mode_active()
        now = time.time()

        if active:
            if self.app_config.meeting_mode_enabled and self.app_config.meeting_mode_until > 0:
                rem_sec = max(0, int(self.app_config.meeting_mode_until - now))
                m = rem_sec // 60
                s = rem_sec % 60
                self.btn_meeting_mode.setText(f"🤫 {m:02d}:{s:02d}")
                self.btn_meeting_mode.setToolTip(
                    f"Meeting Mode Active (Muted for {m}m {s}s)\nLeft-click to turn OFF | Right-click for presets | Ctrl+Shift+M"
                )
            elif self.app_config.meeting_mode_enabled:
                self.btn_meeting_mode.setText("🤫 Meeting")
                self.btn_meeting_mode.setToolTip(
                    "Meeting Mode Active (Manual Mute)\nLeft-click to turn OFF | Right-click for presets | Ctrl+Shift+M"
                )
            elif getattr(self, "_mic_active", False):
                self.btn_meeting_mode.setText("🤫 Call (Mic)")
                self.btn_meeting_mode.setToolTip(
                    "Meeting Mode Active (Microphone in use)\nLeft-click to override | Right-click for presets | Ctrl+Shift+M"
                )
            else:
                self.btn_meeting_mode.setText("🤫 Meeting")
                self.btn_meeting_mode.setToolTip("Meeting Mode Active (Audio Muted)")

            self.btn_meeting_mode.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['surface_light']}; color: {COLORS['glow_cyan']}; "
                f"border: 1px solid {COLORS['glow_cyan']}; border-radius: 4px; font-weight: bold; padding: 2px 8px; }}"
            )
        else:
            self.btn_meeting_mode.setText("🔔 Normal")
            self.btn_meeting_mode.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['surface']}; color: {COLORS['text_muted']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 8px; }}"
            )
            self.btn_meeting_mode.setToolTip(
                "Meeting Mode: Idle (Audio enabled)\nLeft-click to mute | Right-click for timed presets | Ctrl+Shift+M"
            )

        if hasattr(self, "lbl_meeting_settings_status"):
            if active:
                if getattr(self, "_mic_active", False):
                    apps = get_active_microphone_apps()
                    app_str = f" ({', '.join(apps)})" if apps else ""
                    self.lbl_meeting_settings_status.setText(f"🟢 Active • Microphone in use{app_str} • Audio Muted")
                    self.lbl_meeting_settings_status.setStyleSheet(
                        f"color: {COLORS['accent_success']}; font-weight: bold; font-size: 11px;"
                    )
                else:
                    self.lbl_meeting_settings_status.setText("🤫 Active • Manual Meeting Mode • Audio Muted")
                    self.lbl_meeting_settings_status.setStyleSheet(
                        f"color: {COLORS['glow_cyan']}; font-weight: bold; font-size: 11px;"
                    )
            else:
                self.lbl_meeting_settings_status.setText("⚪ Idle • Audio Chimes Enabled")
                self.lbl_meeting_settings_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

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
                status_prefix = "⏸ "
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
            tip_lines = [f"{it.name} (double-click or click ✏️ to edit)"]
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
        self.lbl_queue_status.setText(f"{total_active} active" if total_active else "All quiet")

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
            self.btn_ring_play_pause.setText("▶️" if active_timer.is_paused else "⏸️")
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
            self.btn_ring_play_pause.setText("⏸️")
        else:
            self.ring.set_idle()
            self.btn_ring_play_pause.setText("⏸️")

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

        # Check Meeting Mode & microphone capture state
        if self.app_config.meeting_mode_auto_mic:
            self._mic_active = is_microphone_in_use()
        else:
            self._mic_active = False
        self._update_meeting_mode_ui()

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
            meeting_active = self.is_meeting_mode_active()
            AlarmDialog(
                master=self,
                title_text="Missed While Closed",
                reminder_name=f"{names}{more}",
                category="⚠️ Missed",
                url=single.url if single else "",
                note=single.note if single else "",
                config=self.app_config,
                meeting_mode=meeting_active,
            )
            self.scheduler.missed_items.clear()

    def _handle_wake_missed_ui(self, items: List[ScheduledItem]) -> None:
        names = ", ".join(f"'{it.name}'" for it in items[:3])
        single = items[0] if len(items) == 1 else None
        meeting_active = self.is_meeting_mode_active()
        AlarmDialog(
            master=self,
            title_text="Missed During PC Sleep",
            reminder_name=names,
            category="⚠️ Wake Drift",
            url=single.url if single else "",
            note=single.note if single else "",
            config=self.app_config,
            meeting_mode=meeting_active,
        )

    def _popup_alarm(self, item: ScheduledItem) -> None:
        meeting_active = self.is_meeting_mode_active()
        mute_sound = meeting_active and self.app_config.meeting_mode_mute_sound
        if not mute_sound:
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
            meeting_mode=meeting_active,
        )


class MainApp(QMainWindow):
    """Standalone PySide6 application shell wrapping TimerRendezVousWidget with System Tray & Global Hotkey."""

    def __init__(self, start_minimized: bool = False):
        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} ⏰")
        self.resize(UI_DIMENSIONS["window_width"], UI_DIMENSIONS["window_height"])
        self.setMinimumSize(
            UI_DIMENSIONS.get("min_window_width", 480),
            UI_DIMENSIONS.get("min_window_height", 540),
        )
        self.setStyleSheet(DARK_QSS)

        self.module_widget = TimerRendezVousWidget(self)
        self.setCentralWidget(self.module_widget)

        # Apply persisted window opacity (min=45%, max=100%, default=90%)
        self.setWindowOpacity(max(0.45, min(1.0, self.module_widget.app_config.app_opacity / 100.0)))

        # Wire thread-safe tray signals
        self.module_widget.bridge.toggleVisibilityRequested.connect(self.toggle_visibility)
        self.module_widget.bridge.quitRequested.connect(self.quit_app)

        self.tray = TrayManager(
            on_toggle=lambda: self.module_widget.bridge.toggleVisibilityRequested.emit(),
            on_exit=lambda: self.module_widget.bridge.quitRequested.emit(),
            on_toggle_pause=lambda: self.module_widget.bridge.togglePauseRequested.emit(),
            on_toggle_hud=lambda: self.module_widget.bridge.toggleHudRequested.emit(),
            on_toggle_meeting_mode=lambda: self.module_widget.bridge.toggleMeetingModeRequested.emit(),
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
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _update_tray_tooltip(self) -> None:
        nearest = self.module_widget.scheduler.get_nearest_item()
        meeting_tag = " [🤫 Meeting]" if self.module_widget.is_meeting_mode_active() else ""
        if nearest:
            rem = max(0, int(nearest.target_time - time.time()))
            m, s = divmod(rem, 60)
            h, m = divmod(m, 60)
            tooltip = f"Next: {nearest.name} ({h:02d}:{m:02d}:{s:02d}){meeting_tag}"
        else:
            tooltip = f"{APP_TITLE}: All quiet{meeting_tag}"
        self.tray.update_tooltip(tooltip)

    def _setup_hotkey(self) -> None:
        self._hotkey_listener = GlobalHotkeyListener(
            HOTKEY,
            lambda: self.module_widget.bridge.toggleVisibilityRequested.emit(),
        )
        self._hotkey_listener.start()
        shortcut = QShortcut(QKeySequence("Ctrl+F8"), self)
        shortcut.activated.connect(self.toggle_visibility)

        self._meeting_hotkey_listener = GlobalHotkeyListener(
            MEETING_HOTKEY,
            lambda: self.module_widget.bridge.toggleMeetingModeRequested.emit(),
        )
        self._meeting_hotkey_listener.start()
        meeting_shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        meeting_shortcut.activated.connect(self.module_widget._toggle_meeting_mode)

    def closeEvent(self, event) -> None:
        """Minimize to system tray when window [X] is clicked."""
        event.ignore()
        self.hide_to_tray()

    def hide_to_tray(self) -> None:
        self.module_widget._save_scratchpad_now()
        self.hide()

    def toggle_visibility(self) -> None:
        """Minimize OR restore the GUI window when Ctrl+F8 (or tray toggle) is pressed."""
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()
        else:
            self.module_widget._save_scratchpad_now()
            self.showMinimized()

    def quit_app(self) -> None:
        self.module_widget._save_scratchpad_now()
        self.module_widget._save_hud_pos()
        Storage.save_config(self.module_widget.app_config)
        if hasattr(self, "_hotkey_listener") and self._hotkey_listener:
            self._hotkey_listener.stop()
        if hasattr(self, "_meeting_hotkey_listener") and self._meeting_hotkey_listener:
            self._meeting_hotkey_listener.stop()
        if self.module_widget.hud:
            self.module_widget.hud.close()
        if hasattr(self.module_widget, "ahk_manager") and self.module_widget.ahk_manager.is_running():
            self.module_widget.ahk_manager.stop_script()
        self.tray.stop()
        self._qt_app.quit()

    def mainloop(self) -> None:
        """Compatibility launcher method for run.py."""
        sys.exit(self._qt_app.exec())


TimeSpaceWidget = TimerRendezVousWidget
