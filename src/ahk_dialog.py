"""AutoHotkey v2 Hotstrings & Text Expanders management dialog."""
import os
import sys
from typing import List, Optional, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QPlainTextEdit,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QApplication,
)

from src.config import COLORS, DARK_QSS, AHKHotstringItem, AppConfig
from src.storage import Storage, DEFAULT_AHK_SCRIPT_FILE
from src.ahk_manager import (
    find_ahk_v2_exe,
    clean_hotstring_trigger,
    normalize_hotstring_options,
    generate_ahk_v2_script,
    AHKProcessManager,
)


class AHKItemEditDialog(QDialog):
    """Sub-dialog to add or edit an individual AutoHotkey v2 hotstring."""

    def __init__(self, parent: Optional[QWidget] = None, item: Optional[AHKHotstringItem] = None) -> None:
        super().__init__(parent)
        self.item = item
        self.result_item: Optional[AHKHotstringItem] = None

        self.setWindowTitle("Edit Hotstring" if item else "Add New Hotstring")
        self.setMinimumSize(480, 420)
        self.resize(520, 460)
        self.setStyleSheet(DARK_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Trigger field
        row_trig = QHBoxLayout()
        row_trig.setSpacing(8)
        lbl_trig = QLabel("Trigger Abbreviation:")
        lbl_trig.setFixedWidth(140)
        lbl_trig.setStyleSheet("font-weight: bold;")
        self.entry_trigger = QLineEdit()
        self.entry_trigger.setPlaceholderText("e.g. btw, dts, @m, sig (colons stripped automatically)")
        if item:
            self.entry_trigger.setText(clean_hotstring_trigger(item.trigger))
        row_trig.addWidget(lbl_trig)
        row_trig.addWidget(self.entry_trigger, 1)
        layout.addLayout(row_trig)

        # Replacement text or code
        lbl_rep = QLabel("Replacement Text or AHK v2 Code:")
        lbl_rep.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_rep)

        self.edit_replacement = QPlainTextEdit()
        self.edit_replacement.setFont(QFont("Consolas", 10))
        self.edit_replacement.setPlaceholderText(
            "Enter text expansion, multi-line snippet, or AHK v2 function like:\n"
            'SendText(FormatTime(, "yyyy-MM-dd HH:mm:ss"))'
        )
        if item:
            self.edit_replacement.setPlainText(item.replacement)
        layout.addWidget(self.edit_replacement, 1)

        # Type & Execution
        row_type = QHBoxLayout()
        row_type.setSpacing(8)
        lbl_type = QLabel("Expansion Type:")
        lbl_type.setFixedWidth(140)
        lbl_type.setStyleSheet("font-weight: bold;")
        self.combo_type = QComboBox()
        self.combo_type.addItem("Plain Text Expansion", "text")
        self.combo_type.addItem("Raw Text Mode (T - literal characters)", "raw")
        self.combo_type.addItem("AHK v2 Function / Expression (X)", "expr")

        if item:
            opts = item.options.upper()
            if item.is_expression or "X" in opts:
                self.combo_type.setCurrentIndex(2)
            elif "T" in opts:
                self.combo_type.setCurrentIndex(1)
            else:
                self.combo_type.setCurrentIndex(0)
        row_type.addWidget(lbl_type)
        row_type.addWidget(self.combo_type, 1)
        layout.addLayout(row_type)

        # Options checkboxes grid
        opts_frame = QFrame()
        opts_frame.setStyleSheet(
            f"background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 5px; padding: 6px;"
        )
        opts_layout = QGridLayout(opts_frame)
        opts_layout.setContentsMargins(6, 6, 6, 6)
        opts_layout.setSpacing(8)

        self.chk_instant = QCheckBox("[*] Instant trigger (no space/enter needed)")
        self.chk_instant.setToolTip("Expands immediately when the last letter is typed")

        self.chk_inword = QCheckBox("[?] Trigger inside words")
        self.chk_inword.setToolTip("Triggers even inside other words (great for email addresses or prefixes)")

        self.chk_case = QCheckBox("[c] Case-sensitive")
        self.chk_case.setToolTip("Only triggers if typed in the exact casing")

        self.chk_omit_end = QCheckBox("[O] Omit ending character")
        self.chk_omit_end.setToolTip("Does not produce the space or punctuation that triggered the hotstring")

        if item:
            o = item.options
            self.chk_instant.setChecked("*" in o)
            self.chk_inword.setChecked("?" in o)
            self.chk_case.setChecked("c" in o or "C" in o)
            self.chk_omit_end.setChecked("O" in o or "o" in o)

        opts_layout.addWidget(self.chk_instant, 0, 0)
        opts_layout.addWidget(self.chk_inword, 0, 1)
        opts_layout.addWidget(self.chk_case, 1, 0)
        opts_layout.addWidget(self.chk_omit_end, 1, 1)
        layout.addWidget(opts_frame)

        # Description / Label
        row_desc = QHBoxLayout()
        row_desc.setSpacing(8)
        lbl_desc = QLabel("Description / Tag:")
        lbl_desc.setFixedWidth(140)
        self.entry_desc = QLineEdit()
        self.entry_desc.setPlaceholderText("Optional memo or usage context (e.g. Work Signature)")
        if item:
            self.entry_desc.setText(item.description)
        row_desc.addWidget(lbl_desc)
        row_desc.addWidget(self.entry_desc, 1)
        layout.addLayout(row_desc)

        # Enabled checkbox
        self.chk_enabled = QCheckBox("Enable this hotstring immediately")
        self.chk_enabled.setChecked(item.enabled if item else True)
        layout.addWidget(self.chk_enabled)

        # Buttons
        row_btn = QHBoxLayout()
        row_btn.addStretch()

        btn_cancel = QPushButton("✖ Cancel")
        btn_cancel.setObjectName("dangerBtn")
        btn_cancel.clicked.connect(self.reject)
        row_btn.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Save Hotstring")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        row_btn.addWidget(btn_save)

        layout.addLayout(row_btn)

    def _on_save(self) -> None:
        trig = clean_hotstring_trigger(self.entry_trigger.text())
        if not trig:
            QMessageBox.warning(self, "Invalid Trigger", "Please provide a trigger abbreviation.")
            return

        rep = self.edit_replacement.toPlainText().strip()
        if not rep:
            QMessageBox.warning(self, "Invalid Replacement", "Please provide replacement text or code.")
            return

        # Build options string
        opts_set = []
        if self.chk_instant.isChecked():
            opts_set.append("*")
        if self.chk_inword.isChecked():
            opts_set.append("?")
        if self.chk_case.isChecked():
            opts_set.append("c")
        if self.chk_omit_end.isChecked():
            opts_set.append("O")

        type_mode = self.combo_type.currentData()
        is_expr = (type_mode == "expr")
        if type_mode == "raw":
            opts_set.append("T")
        elif type_mode == "expr":
            opts_set.append("X")

        final_opts = "".join(opts_set)

        self.result_item = AHKHotstringItem(
            trigger=trig,
            replacement=self.edit_replacement.toPlainText(),
            options=final_opts,
            is_expression=is_expr,
            enabled=self.chk_enabled.isChecked(),
            description=self.entry_desc.text().strip(),
        )
        self.accept()


class AHKHotstringsDialog(QDialog):
    """
    Comprehensive AutoHotkey v2 Hotstrings & Text Expanders Manager Window.
    Supports structured table editing, code generation, script inspection, and process management.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        config: Optional[AppConfig] = None,
        process_manager: Optional[AHKProcessManager] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config or Storage.load_config()
        self.process_manager = process_manager or AHKProcessManager(self)
        self.items: List[AHKHotstringItem] = Storage.load_hotstrings()

        self.setWindowTitle("⌨️ AutoHotkey v2 Hotstrings Text Expanders")
        self.setMinimumSize(780, 600)
        self.resize(860, 680)
        self.setStyleSheet(DARK_QSS)

        # Wire process signals
        self.process_manager.statusChanged.connect(self._on_process_status_changed)
        self.process_manager.errorOccurred.connect(self._on_process_error)
        self.process_manager.outputReceived.connect(self._on_process_output)

        self._init_ui()
        self._refresh_table()
        self._sync_code_preview()
        self._update_status_bar()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Header & Status Row ──
        hdr_frame = QFrame()
        hdr_frame.setObjectName("ahkHeaderFrame")
        hdr_frame.setStyleSheet(
            f"QFrame#ahkHeaderFrame {{"
            f"  background-color: {COLORS['surface']};"
            f"  border: 1px solid {COLORS['border']};"
            f"  border-radius: 6px;"
            f"  padding: 6px 8px;"
            f"}}"
            f"QFrame#ahkHeaderFrame QPushButton {{"
            f"  padding: 4px 12px;"
            f"  font-size: 11px;"
            f"  font-weight: 600;"
            f"}}"
        )
        hdr_layout = QVBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(6, 6, 6, 6)
        hdr_layout.setSpacing(8)

        # Row 1: Title + AHK v2 Executable Status + Auto-Start
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        lbl_title = QLabel("⌨️ AutoHotkey v2 Hotstrings Manager")
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLORS['text']};")
        top_row.addWidget(lbl_title)
        top_row.addStretch()

        self.lbl_exe_status = QLabel("Checking AHK v2...")
        self.lbl_exe_status.setStyleSheet("font-size: 11px;")
        top_row.addWidget(self.lbl_exe_status)

        self.chk_auto_start = QCheckBox("Auto-start with TimeSpace")
        self.chk_auto_start.setChecked(self.config.ahk_auto_start)
        self.chk_auto_start.toggled.connect(self._on_auto_start_toggled)
        top_row.addWidget(self.chk_auto_start)

        hdr_layout.addLayout(top_row)

        # Row 2: Action Controls Bar (All 4 buttons aligned + status pill)
        ctl_row = QHBoxLayout()
        ctl_row.setSpacing(8)

        self.lbl_proc_status = QLabel("⚪ Stopped")
        self.lbl_proc_status.setFixedHeight(32)
        self.lbl_proc_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_proc_status.setStyleSheet(
            f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        ctl_row.addWidget(self.lbl_proc_status)

        self.btn_run_script = QPushButton("▶️ Run / Reload")
        self.btn_run_script.setObjectName("primaryBtn")
        self.btn_run_script.setFixedHeight(32)
        self.btn_run_script.setMinimumWidth(125)
        self.btn_run_script.setToolTip("Start or reload AutoHotkey v2 script with all active hotstrings")
        self.btn_run_script.clicked.connect(self._run_or_reload_script)
        ctl_row.addWidget(self.btn_run_script)

        self.btn_stop_script = QPushButton("⏹️ Stop")
        self.btn_stop_script.setObjectName("dangerBtn")
        self.btn_stop_script.setFixedHeight(32)
        self.btn_stop_script.setMinimumWidth(80)
        self.btn_stop_script.setToolTip("Stop active AutoHotkey v2 script process")
        self.btn_stop_script.clicked.connect(self._stop_script)
        ctl_row.addWidget(self.btn_stop_script)

        btn_open_folder = QPushButton("📂 Open Script Folder")
        btn_open_folder.setFixedHeight(32)
        btn_open_folder.setMinimumWidth(160)
        btn_open_folder.setToolTip("Open folder containing hotstrings.ahk in Windows Explorer")
        btn_open_folder.clicked.connect(self._open_script_folder)
        ctl_row.addWidget(btn_open_folder)

        btn_browse_exe = QPushButton("⚙️ AHK Path")
        btn_browse_exe.setFixedHeight(32)
        btn_browse_exe.setMinimumWidth(105)
        btn_browse_exe.setToolTip("Configure custom AutoHotkey v2 executable location")
        btn_browse_exe.clicked.connect(self._browse_ahk_exe)
        ctl_row.addWidget(btn_browse_exe)

        ctl_row.addStretch()
        hdr_layout.addLayout(ctl_row)
        layout.addWidget(hdr_frame)

        # ── Tabbed View (Visual Table vs Script Editor) ──
        self.tabs = QTabWidget()

        # Tab 1: Visual Table
        tab_table = QWidget()
        lay_table = QVBoxLayout(tab_table)
        lay_table.setContentsMargins(6, 8, 6, 6)
        lay_table.setSpacing(6)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        lbl_search = QLabel("🔍")
        filter_row.addWidget(lbl_search)
        self.entry_filter = QLineEdit()
        self.entry_filter.setPlaceholderText("Filter hotstrings by trigger, expansion text, or description...")
        self.entry_filter.textChanged.connect(self._filter_table)
        filter_row.addWidget(self.entry_filter, 1)

        # Preset Templates dropdown
        self.combo_templates = QComboBox()
        self.combo_templates.addItem("⚡ Add Preset Template...", None)
        self.combo_templates.addItem("📅 Current Date (:X:ds -> YYYY-MM-DD)", "date")
        self.combo_templates.addItem("🕒 Current Timestamp (:X:dts -> YYYY-MM-DD HH:mm:ss)", "timestamp")
        self.combo_templates.addItem("📧 Professional Email Signature", "sig")
        self.combo_templates.addItem("🌐 Localhost IP / URL (:lh)", "local")
        self.combo_templates.addItem("💼 IT Ticket Greeting (:thx)", "ticket")
        self.combo_templates.addItem("🔤 Lorem Ipsum snippet", "lorem")
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        filter_row.addWidget(self.combo_templates)

        lay_table.addLayout(filter_row)

        # Table Widget
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Active", "Trigger", "Replacement Preview", "Options", "Type", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_selected_item())
        lay_table.addWidget(self.table, 1)

        # Table action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_add = QPushButton("➕ Add Hotstring")
        btn_add.setObjectName("primaryBtn")
        btn_add.clicked.connect(self._add_new_item)
        btn_row.addWidget(btn_add)

        btn_edit = QPushButton("✏️ Edit")
        btn_edit.clicked.connect(self._edit_selected_item)
        btn_row.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ Delete")
        btn_del.setObjectName("dangerBtn")
        btn_del.clicked.connect(self._delete_selected_item)
        btn_row.addWidget(btn_del)

        btn_dup = QPushButton("📋 Duplicate")
        btn_dup.clicked.connect(self._duplicate_selected_item)
        btn_row.addWidget(btn_dup)

        btn_row.addStretch()

        btn_up = QPushButton("▲ Move Up")
        btn_up.clicked.connect(lambda: self._move_item(-1))
        btn_row.addWidget(btn_up)

        btn_down = QPushButton("▼ Move Down")
        btn_down.clicked.connect(lambda: self._move_item(1))
        btn_row.addWidget(btn_down)

        lay_table.addLayout(btn_row)
        self.tabs.addTab(tab_table, "📋 Visual Hotstrings Table")

        # Tab 2: AHK v2 Code Editor
        tab_code = QWidget()
        lay_code = QVBoxLayout(tab_code)
        lay_code.setContentsMargins(6, 8, 6, 6)
        lay_code.setSpacing(6)

        lbl_code_info = QLabel("Strict AutoHotkey v2 Code Preview (`data/hotstrings.ahk`):")
        lbl_code_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        lay_code.addWidget(lbl_code_info)

        self.edit_code = QPlainTextEdit()
        self.edit_code.setFont(QFont("Consolas", 10))
        self.edit_code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        lay_code.addWidget(self.edit_code, 1)

        code_btn_row = QHBoxLayout()
        code_btn_row.setSpacing(6)

        btn_regen = QPushButton("🔄 Regenerate from Table")
        btn_regen.setToolTip("Rebuild AHK v2 script from visual table items")
        btn_regen.clicked.connect(self._sync_code_preview)
        code_btn_row.addWidget(btn_regen)

        btn_save_code = QPushButton("💾 Save Script File")
        btn_save_code.setObjectName("successBtn")
        btn_save_code.setToolTip("Save current editor text directly to data/hotstrings.ahk")
        btn_save_code.clicked.connect(self._save_script_from_code)
        code_btn_row.addWidget(btn_save_code)

        btn_copy_code = QPushButton("📋 Copy Script")
        btn_copy_code.clicked.connect(self._copy_code_to_clipboard)
        code_btn_row.addWidget(btn_copy_code)

        code_btn_row.addStretch()
        lay_code.addLayout(code_btn_row)

        self.tabs.addTab(tab_code, "📝 AHK v2 Script Editor")
        layout.addWidget(self.tabs, 1)

        # ── Bottom Bar / Cheatsheet ──
        footer_row = QHBoxLayout()
        lbl_tip = QLabel(
            "💡 Options: [*] Instant expansion • [?] Trigger inside words • [c] Case-sensitive • [T] Raw text • [X] AHK v2 function"
        )
        lbl_tip.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        footer_row.addWidget(lbl_tip, 1)

        btn_apply = QPushButton("💾 Save & Apply")
        btn_apply.setObjectName("successBtn")
        btn_apply.clicked.connect(self._save_and_apply)
        footer_row.addWidget(btn_apply)

        btn_close = QPushButton("✖ Close")
        btn_close.clicked.connect(self.close)
        footer_row.addWidget(btn_close)

        layout.addLayout(footer_row)

    # ── Table Population & Filtering ──

    def _refresh_table(self) -> None:
        filter_text = self.entry_filter.text().strip().lower()
        self.table.setRowCount(0)

        for row_idx, item in enumerate(self.items):
            trig = clean_hotstring_trigger(item.trigger)
            rep = item.replacement.replace("\n", " ↵ ")
            desc = item.description
            opts = item.options

            # Filter check
            if filter_text:
                if (
                    filter_text not in trig.lower()
                    and filter_text not in rep.lower()
                    and filter_text not in desc.lower()
                ):
                    continue

            r = self.table.rowCount()
            self.table.insertRow(r)

            # Checkbox: Active
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(4, 2, 4, 2)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setChecked(item.enabled)
            chk.toggled.connect(lambda checked, idx=row_idx: self._toggle_item_enabled(idx, checked))
            chk_layout.addWidget(chk)
            self.table.setCellWidget(r, 0, chk_widget)

            # Trigger
            item_trig = QTableWidgetItem(f":{opts}:{trig}")
            item_trig.setForeground(QColor(COLORS["accent_link"]))
            item_trig.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table.setItem(r, 1, item_trig)

            # Replacement Preview
            item_rep = QTableWidgetItem(rep[:80] + ("..." if len(rep) > 80 else ""))
            self.table.setItem(r, 2, item_rep)

            # Options Badges
            opts_desc = []
            if "*" in opts:
                opts_desc.append("Instant (*)")
            if "?" in opts:
                opts_desc.append("In-Word (?)")
            if "c" in opts or "C" in opts:
                opts_desc.append("Case (c)")
            if "T" in opts:
                opts_desc.append("Raw (T)")
            if "X" in opts or item.is_expression:
                opts_desc.append("Exec (X)")
            item_opts = QTableWidgetItem(", ".join(opts_desc) or "Standard")
            self.table.setItem(r, 3, item_opts)

            # Type
            type_label = "v2 Function" if (item.is_expression or "X" in opts) else ("Raw Text" if "T" in opts else "Text")
            item_type = QTableWidgetItem(type_label)
            self.table.setItem(r, 4, item_type)

            # Description
            item_desc = QTableWidgetItem(desc)
            item_desc.setForeground(QColor(COLORS["text_muted"]))
            self.table.setItem(r, 5, item_desc)

            # Store original item index in UserRole
            item_trig.setData(Qt.ItemDataRole.UserRole, row_idx)

    def _filter_table(self) -> None:
        self._refresh_table()

    def _toggle_item_enabled(self, item_index: int, checked: bool) -> None:
        if 0 <= item_index < len(self.items):
            self.items[item_index].enabled = checked
            self._save_items_silently()
            self._sync_code_preview()

    # ── Item CRUD Operations ──

    def _add_new_item(self) -> None:
        dlg = AHKItemEditDialog(self)
        if dlg.exec() and dlg.result_item:
            self.items.append(dlg.result_item)
            self._save_items_silently()
            self._refresh_table()
            self._sync_code_preview()

    def _get_selected_item_index(self) -> Optional[int]:
        sel = self.table.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        item_trig = self.table.item(row, 1)
        if item_trig:
            return item_trig.data(Qt.ItemDataRole.UserRole)
        return None

    def _edit_selected_item(self) -> None:
        idx = self._get_selected_item_index()
        if idx is None or idx >= len(self.items):
            QMessageBox.information(self, "No Selection", "Please select a hotstring to edit.")
            return

        dlg = AHKItemEditDialog(self, self.items[idx])
        if dlg.exec() and dlg.result_item:
            self.items[idx] = dlg.result_item
            self._save_items_silently()
            self._refresh_table()
            self._sync_code_preview()

    def _delete_selected_item(self) -> None:
        idx = self._get_selected_item_index()
        if idx is None or idx >= len(self.items):
            QMessageBox.information(self, "No Selection", "Please select a hotstring to delete.")
            return

        trig = self.items[idx].trigger
        confirm = QMessageBox.question(
            self,
            "Delete Hotstring",
            f"Are you sure you want to delete hotstring ':{trig}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.items.pop(idx)
            self._save_items_silently()
            self._refresh_table()
            self._sync_code_preview()

    def _duplicate_selected_item(self) -> None:
        idx = self._get_selected_item_index()
        if idx is None or idx >= len(self.items):
            return

        orig = self.items[idx]
        dup = AHKHotstringItem(
            trigger=f"{orig.trigger}_copy",
            replacement=orig.replacement,
            options=orig.options,
            is_expression=orig.is_expression,
            enabled=orig.enabled,
            description=f"{orig.description} (Copy)" if orig.description else "Copy",
        )
        self.items.insert(idx + 1, dup)
        self._save_items_silently()
        self._refresh_table()
        self._sync_code_preview()

    def _move_item(self, delta: int) -> None:
        idx = self._get_selected_item_index()
        if idx is None:
            return
        new_idx = idx + delta
        if 0 <= new_idx < len(self.items):
            item = self.items.pop(idx)
            self.items.insert(new_idx, item)
            self._save_items_silently()
            self._refresh_table()
            self._sync_code_preview()
            # Restore selection
            for r in range(self.table.rowCount()):
                it = self.table.item(r, 1)
                if it and it.data(Qt.ItemDataRole.UserRole) == new_idx:
                    self.table.selectRow(r)
                    break

    def _on_template_selected(self, index: int) -> None:
        key = self.combo_templates.currentData()
        self.combo_templates.setCurrentIndex(0)
        if not key:
            return

        new_item: Optional[AHKHotstringItem] = None
        if key == "date":
            new_item = AHKHotstringItem(
                trigger="ds",
                replacement='SendText(FormatTime(, "yyyy-MM-dd"))',
                options="X",
                is_expression=True,
                enabled=True,
                description="Current Date (YYYY-MM-DD)",
            )
        elif key == "timestamp":
            new_item = AHKHotstringItem(
                trigger="dts",
                replacement='SendText(FormatTime(, "yyyy-MM-dd HH:mm:ss"))',
                options="X",
                is_expression=True,
                enabled=True,
                description="Current Timestamp (YYYY-MM-DD HH:mm:ss)",
            )
        elif key == "sig":
            new_item = AHKHotstringItem(
                trigger="sig",
                replacement="Best regards,\nIT Support Specialist\nTimeSpace Workspace",
                options="T",
                is_expression=False,
                enabled=True,
                description="Email / Ticket Signature",
            )
        elif key == "local":
            new_item = AHKHotstringItem(
                trigger="lh",
                replacement="http://127.0.0.1:",
                options="*",
                is_expression=False,
                enabled=True,
                description="Localhost URL prefix",
            )
        elif key == "ticket":
            new_item = AHKHotstringItem(
                trigger="thx",
                replacement="Thank you for contacting IT Support! We have received your request and are reviewing it.",
                options="T",
                is_expression=False,
                enabled=True,
                description="Ticket Reception Reply",
            )
        elif key == "lorem":
            new_item = AHKHotstringItem(
                trigger="lorem",
                replacement="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                options="T",
                is_expression=False,
                enabled=True,
                description="Lorem Ipsum Placeholder",
            )

        if new_item:
            self.items.append(new_item)
            self._save_items_silently()
            self._refresh_table()
            self._sync_code_preview()

    # ── Code & Script Sync ──

    def _sync_code_preview(self) -> None:
        code = generate_ahk_v2_script(self.items)
        self.edit_code.setPlainText(code)

    def _save_script_from_code(self) -> None:
        code = self.edit_code.toPlainText()
        Storage.save_ahk_script_text(code, self.config.ahk_script_path or None)
        QMessageBox.information(self, "Script Saved", "AutoHotkey v2 script successfully saved to disk.")

    def _copy_code_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.edit_code.toPlainText())
        QMessageBox.information(self, "Copied", "AutoHotkey v2 script copied to system clipboard.")

    def _save_items_silently(self) -> None:
        Storage.save_hotstrings(self.items)
        code = generate_ahk_v2_script(self.items)
        Storage.save_ahk_script_text(code, self.config.ahk_script_path or None)

    def _save_and_apply(self) -> None:
        self._save_items_silently()
        if self.process_manager.is_running():
            self._run_or_reload_script()
        QMessageBox.information(self, "Saved", "All hotstrings saved and script generated successfully!")

    # ── Process Execution & Lifecycle ──

    def _update_status_bar(self) -> None:
        exe = find_ahk_v2_exe(self.config.ahk_v2_exe_path)
        if exe:
            self.lbl_exe_status.setText(f"🟢 AHK v2 Ready: {os.path.basename(exe)}")
            self.lbl_exe_status.setStyleSheet(f"color: {COLORS['accent_success']}; font-weight: bold;")
            self.lbl_exe_status.setToolTip(exe)
        else:
            self.lbl_exe_status.setText("⚠️ AHK v2 Not Found")
            self.lbl_exe_status.setStyleSheet(f"color: {COLORS['accent_danger']}; font-weight: bold;")
            self.lbl_exe_status.setToolTip("AutoHotkey v2 was not detected in standard locations.")

        if self.process_manager.is_running():
            pid = self.process_manager.get_pid()
            self.lbl_proc_status.setText(f"🟢 Running (PID: {pid})")
            self.lbl_proc_status.setStyleSheet(
                f"background-color: {COLORS['accent_success']}; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
        else:
            self.lbl_proc_status.setText("⚪ Stopped")
            self.lbl_proc_status.setStyleSheet(
                f"background-color: {COLORS['surface_light']}; color: {COLORS['text_muted']}; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )

    def _browse_ahk_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select AutoHotkey v2 Executable",
            r"C:\Program Files\AutoHotkey\v2",
            "AutoHotkey Executable (AutoHotkey*.exe);;All Executables (*.exe)",
        )
        if path:
            self.config.ahk_v2_exe_path = path
            Storage.save_config(self.config)
            self._update_status_bar()

    def _run_or_reload_script(self) -> None:
        # First ensure script is written to disk
        self._save_items_silently()
        script_file = self.config.ahk_script_path or DEFAULT_AHK_SCRIPT_FILE

        ok = self.process_manager.start_script(script_file, self.config.ahk_v2_exe_path)
        if ok:
            self._update_status_bar()

    def _stop_script(self) -> None:
        self.process_manager.stop_script()
        self._update_status_bar()

    def _open_script_folder(self) -> None:
        script_file = self.config.ahk_script_path or DEFAULT_AHK_SCRIPT_FILE
        folder = os.path.dirname(os.path.abspath(script_file))
        if os.path.exists(folder):
            QDesktopServices.openUrl(f"file:///{folder.replace(os.sep, '/')}")

    def _on_auto_start_toggled(self, checked: bool) -> None:
        self.config.ahk_auto_start = checked
        Storage.save_config(self.config)

    def _on_process_status_changed(self, running: bool, pid: int) -> None:
        self._update_status_bar()

    def _on_process_error(self, err: str) -> None:
        self._update_status_bar()
        QMessageBox.warning(self, "AutoHotkey Process Error", err)

    def _on_process_output(self, out: str) -> None:
        pass

