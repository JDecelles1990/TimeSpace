"""PySide6 '5. Go ⏱️' Cross-Platform Diagnostic & Troubleshooting Module using non-blocking QProcess."""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QPlainTextEdit,
    QProgressBar,
)

from src.config import COLORS, GO_DIAG_ACTIONS, GO_TARGET_PRESETS


class GoConsoleHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the live Go diagnostic console (PASS/OPEN, FAIL/ERROR, WARN/CLOSED, headers)."""

    def __init__(self, document):
        super().__init__(document)
        self._rules: List[Tuple[re.Pattern, QTextCharFormat]] = []

        fmt_header = QTextCharFormat()
        fmt_header.setForeground(QColor(COLORS["accent_link"]))
        fmt_header.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"═══.*═══|^(?:▶|🚀|🔨)\s*\[[^\]]+\]"), fmt_header))

        fmt_pass = QTextCharFormat()
        fmt_pass.setForeground(QColor(COLORS["accent_success"]))
        fmt_pass.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"\[PASS\]|\bOPEN\b|✔|\b200\s+OK\b"), fmt_pass))

        fmt_fail = QTextCharFormat()
        fmt_fail.setForeground(QColor(COLORS["accent_danger"]))
        fmt_fail.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"\[FAIL\]|\[ERROR\]|\[STDERR\]|\bUNREACHABLE\b|✖"), fmt_fail))

        fmt_warn = QTextCharFormat()
        fmt_warn.setForeground(QColor(COLORS["accent_warning"]))
        fmt_warn.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"\bCLOSED/FILTERED\b|\[WARN\]|\[STOPPED\]|\bELEVATED\b"), fmt_warn))

    def highlightBlock(self, text: str) -> None:
        if not text:
            return
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                if end > start:
                    self.setFormat(start, end - start, fmt)


class GoTroubleshootingTab(QWidget):
    """Cross-platform diagnostic and remediation tab powered by asynchronous QProcess execution."""

    diagnostic_completed = Signal(dict)
    sendToScratchpad = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._repo_root: Path = Path(__file__).resolve().parent.parent
        self._go_engine_dir: Path = self._repo_root / "go_engine"
        self._bin_dir: Path = self._repo_root / "bin"

        self._process: Optional[QProcess] = None
        self._stdout_buffer: str = ""
        self._pending_json_payload: Optional[Dict[str, Any]] = None
        self._current_action: str = ""
        self._current_target: str = ""
        self._action_buttons: List[QPushButton] = []

        self._build_ui()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Top Configuration Group (Mode + Build + Target/Presets + 2x4 Action Grid + Elevated CLI Launcher)
        cfg_group = QGroupBox("⚡ Go Diagnostic & Remediation Engine")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setContentsMargins(8, 6, 8, 6)
        cfg_layout.setSpacing(5)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.addWidget(QLabel("Engine Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Compiled Binary Mode (Zero-Dependency)", "binary")
        self.combo_mode.addItem("Go Script Mode (go run)", "go_run")
        mode_row.addWidget(self.combo_mode, 1)

        self.lbl_engine_status = QLabel(self._detect_engine_badge())
        self.lbl_engine_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        mode_row.addWidget(self.lbl_engine_status)

        self.btn_build_bins = QPushButton("🔨 Build Binaries")
        self.btn_build_bins.setFixedHeight(24)
        self.btn_build_bins.setToolTip("Cross-compile Go binaries into /bin via go_engine/build_all.ps1")
        self.btn_build_bins.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_build_bins.clicked.connect(self.build_go_binaries)
        mode_row.addWidget(self.btn_build_bins)
        cfg_layout.addLayout(mode_row)

        target_row = QHBoxLayout()
        target_row.setSpacing(6)
        target_row.addWidget(QLabel("Target:"))
        self.entry_target = QLineEdit("1.1.1.1")
        self.entry_target.setPlaceholderText("IP, hostname, or URL (e.g., 1.1.1.1, github.com)")
        target_row.addWidget(self.entry_target, 2)

        self.combo_presets = QComboBox()
        self.combo_presets.setToolTip("Quick-select common diagnostic targets")
        for label, host_val in GO_TARGET_PRESETS:
            self.combo_presets.addItem(label, host_val)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        target_row.addWidget(self.combo_presets, 2)

        target_row.addWidget(QLabel("Args:"))
        self.entry_extra_args = QLineEdit()
        self.entry_extra_args.setPlaceholderText("Optional CLI flags")
        target_row.addWidget(self.entry_extra_args, 1)
        cfg_layout.addLayout(target_row)

        # 8 Action Buttons Grid (2 rows x 4 columns)
        grid = QGridLayout()
        grid.setSpacing(5)
        for idx, (label, action_slug) in enumerate(GO_DIAG_ACTIONS):
            btn = QPushButton(label)
            btn.setMinimumHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, a=action_slug: self.run_diagnostic(a))
            row, col = divmod(idx, 4)
            grid.addWidget(btn, row, col)
            self._action_buttons.append(btn)
        cfg_layout.addLayout(grid)

        # External Interactive Go CLI Launcher Bar (Elevation Checkbox + External Terminal Button)
        cli_launcher_layout = QHBoxLayout()
        cli_launcher_layout.setSpacing(8)

        self.elevate_checkbox = QCheckBox("⚡ Run as Admin / sudo (Elevated Fixes)")
        self.elevate_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.elevate_checkbox.setStyleSheet(
            f"QCheckBox {{ font-weight: bold; color: {COLORS['accent_warning']}; padding: 2px 4px; }}"
        )

        self.launch_cli_btn = QPushButton("🚀 Launch Interactive Go CLI (External Terminal)")
        self.launch_cli_btn.setObjectName("primaryBtn")
        self.launch_cli_btn.setMinimumHeight(29)
        self.launch_cli_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.launch_cli_btn.clicked.connect(self.launch_interactive_go_cli)

        cli_launcher_layout.addWidget(self.elevate_checkbox)
        cli_launcher_layout.addWidget(self.launch_cli_btn, 1)
        cfg_layout.addLayout(cli_launcher_layout)

        layout.addWidget(cfg_group)

        # Process Controls, Copy / Send to Scratchpad & Indeterminate Progress Bar Row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(5)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {COLORS['surface_light']}; border: 1px solid {COLORS['border']}; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: {COLORS['accent']}; border-radius: 3px; }}"
        )
        ctrl_row.addWidget(self.progress_bar, 1)

        self.lbl_run_state = QLabel("Idle")
        self.lbl_run_state.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        ctrl_row.addWidget(self.lbl_run_state)

        self.btn_copy_out = QPushButton("📋 Copy")
        self.btn_copy_out.setFixedHeight(23)
        self.btn_copy_out.setToolTip("Copy console output to clipboard")
        self.btn_copy_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_out.clicked.connect(self.copy_console_output)
        ctrl_row.addWidget(self.btn_copy_out)

        self.btn_send_sp = QPushButton("📝 +Scratchpad")
        self.btn_send_sp.setFixedHeight(23)
        self.btn_send_sp.setToolTip("Append console output to 4. Scratchpad")
        self.btn_send_sp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_sp.clicked.connect(self.send_console_to_scratchpad)
        ctrl_row.addWidget(self.btn_send_sp)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setFixedHeight(23)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_process)
        ctrl_row.addWidget(self.btn_stop)

        self.btn_clear = QPushButton("🧹 Clear")
        self.btn_clear.setFixedHeight(23)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_console)
        ctrl_row.addWidget(self.btn_clear)

        layout.addLayout(ctrl_row)

        # Read-Only Monospace Color-Highlighted Live Output Console
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        mono_family = "Consolas" if sys.platform == "win32" else "Monospace"
        self.console.setFont(QFont(mono_family, 10))
        self.console.setPlaceholderText(
            "Select any diagnostic or remediation action above to stream color-coded real-time output...\n"
            "• Quick Target Presets let you switch between Cloudflare, Google, GitHub, Microsoft, or Localhost.\n"
            "• Use '📋 Copy' or '📝 +Scratchpad' to capture results directly into your Time Notes Scratchpad.\n"
            "• Click '🚀 Launch Interactive Go CLI' (with optional '⚡ Run as Admin / sudo') for an external REPL."
        )
        self.console.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {COLORS['bg_dark']}; color: {COLORS['text']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 5px; padding: 6px; }}"
        )
        self._console_highlighter = GoConsoleHighlighter(self.console.document())
        layout.addWidget(self.console, 1)

    # ── Preset, Copy, Scratchpad & Build Helpers ─────────────────────────────

    def _on_preset_selected(self, index: int) -> None:
        host_val = self.combo_presets.itemData(index)
        if host_val:
            self.entry_target.setText(str(host_val))

    def copy_console_output(self) -> None:
        text = self.console.toPlainText().strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        self.lbl_run_state.setText("✅ Copied output")
        self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; font-weight: bold;")

    def send_console_to_scratchpad(self) -> None:
        text = self.console.toPlainText().strip()
        if not text:
            return
        self.sendToScratchpad.emit(text)
        self.lbl_run_state.setText("📝 Sent to Scratchpad")
        self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent_link']}; font-size: 11px; font-weight: bold;")

    def build_go_binaries(self) -> None:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._append_line("[WARN] A process is already running. Stop it or wait before building.")
            return

        build_script = self._go_engine_dir / "build_all.ps1"
        if not build_script.exists():
            self._append_line(f"[ERROR] Build script not found at {build_script}")
            return

        if not shutil.which("go"):
            self._append_line(
                "[WARN] Go compiler ('go') was not found on PATH. Install Go 1.22+ from https://go.dev/dl/ and click '🔨 Build Binaries' again."
            )
            self.lbl_run_state.setText("Go compiler missing")
            self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent_warning']}; font-size: 11px; font-weight: bold;")
            return

        shell_exe = shutil.which("pwsh") or shutil.which("powershell")
        if not shell_exe:
            self._append_line("[ERROR] PowerShell ('pwsh' / 'powershell') not found on PATH to run build_all.ps1.")
            return

        self._stdout_buffer = ""
        self._pending_json_payload = None
        self._current_action = "build-binaries"
        self._current_target = "all-platforms"
        self._append_line(f"🔨 [Build Engine] Running {build_script.name} (CGO_ENABLED=0)...")

        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(self._go_engine_dir))
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self._process.readyReadStandardError.connect(self._on_stderr_ready)
        self._process.finished.connect(self._on_process_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        self._set_running_ui_state(True, "Building Go binaries...")
        args = ["-NoProfile", "-File", str(build_script)]
        if sys.platform == "win32":
            args = ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(build_script)]
        self._process.start(shell_exe, args)

    # ── Binary & Toolchain Resolution (pathlib.Path only) ────────────────────

    def _resolve_binary_path(self) -> Path:
        if sys.platform == "win32":
            return self._bin_dir / "diag_windows.exe"
        if sys.platform == "darwin":
            return self._bin_dir / "diag_mac_arm64"
        return self._bin_dir / "diag_linux"

    def _detect_engine_badge(self) -> str:
        bin_path = self._resolve_binary_path()
        if bin_path.exists():
            return f"Binary ready ({bin_path.name})"
        if shutil.which("go"):
            return "Go CLI detected on PATH"
        return "Fallback ready"

    # ── External Interactive Go CLI Launcher (Admin / sudo + REPL) ───────────

    def launch_interactive_go_cli(self) -> None:
        target = self.entry_target.text().strip() or "1.1.1.1"
        elevate = self.elevate_checkbox.isChecked()
        binary_path = self._resolve_binary_path()

        if binary_path.exists():
            cli_cmd = f'"{binary_path}" --interactive --target={target}'
            work_dir = str(binary_path.parent)
        elif shutil.which("go") and self._go_engine_dir.exists():
            cli_cmd = f"go run . --interactive --target={target}"
            work_dir = str(self._go_engine_dir)
        else:
            script_path = Path(__file__).resolve()
            cli_cmd = f'"{sys.executable}" "{script_path}" --fallback-cli --interactive --target={target}'
            work_dir = str(self._repo_root)

        mode_str = "ELEVATED (Admin/sudo)" if elevate else "STANDARD USER"
        self._append_line(f"🚀 [EXEC] Spawning external Go CLI [{mode_str}] for target: {target}")
        started = False

        if sys.platform.startswith("win"):
            shell_path = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
            ps_invoke = cli_cmd if cli_cmd.startswith("go ") else f"& {cli_cmd}"
            safe_work_dir = work_dir.replace("'", "''")
            ps_script = f"Set-Location -LiteralPath '{safe_work_dir}'; {ps_invoke}"
            encoded_cmd = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
            operation = "runas" if elevate else "open"
            params = f"-NoExit -EncodedCommand {encoded_cmd}"
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, operation, shell_path, params, work_dir, 1)
                started = int(ret) > 32
            except Exception:
                started = False

        elif sys.platform.startswith("linux"):
            inner_cmd = f"sudo {cli_cmd}" if elevate else cli_cmd
            linux_terminals = [
                ("x-terminal-emulator", ["-e", f"bash -c '{inner_cmd}; exec bash'"]),
                ("gnome-terminal", ["--", "bash", "-c", f"{inner_cmd}; exec bash"]),
                ("konsole", ["--hold", "-e", "bash", "-c", inner_cmd]),
                ("xfce4-terminal", ["--hold", "-e", f"bash -c '{inner_cmd}'"]),
                ("xterm", ["-hold", "-e", inner_cmd]),
            ]
            for term_bin, term_args in linux_terminals:
                if shutil.which(term_bin):
                    started, _ = QProcess.startDetached(term_bin, term_args, work_dir)
                    if started:
                        break

        elif sys.platform == "darwin":
            mac_cmd = f"sudo {cli_cmd}" if elevate else cli_cmd
            apple_script = (
                f'tell application "Terminal"\n'
                f"    activate\n"
                f'    do script "cd \'{work_dir}\' && {mac_cmd}"\n'
                f"end tell"
            )
            started, _ = QProcess.startDetached("osascript", ["-e", apple_script])

        if started:
            self._append_line(f"═══ [PASS] External Go CLI session ({mode_str}) launched. ═══\n")
            self.lbl_run_state.setText(f"CLI Launched ({mode_str})")
            self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 11px; font-weight: bold;")
        else:
            self._append_line("[ERROR] Failed to spawn external terminal emulator (or UAC canceled).")
            self.lbl_run_state.setText("Terminal launch canceled")
            self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent_danger']}; font-size: 11px; font-weight: bold;")

    # ── Asynchronous QProcess Execution ──────────────────────────────────────

    def run_diagnostic(self, action: str) -> None:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._append_line("[WARN] A diagnostic process is already running. Stop it or wait for completion.")
            return

        target = self.entry_target.text().strip() or "1.1.1.1"
        extra_raw = self.entry_extra_args.text().strip()
        extra_args = [tok for tok in extra_raw.split(" ") if tok] if extra_raw else []

        self._current_action = action
        self._current_target = target
        self._stdout_buffer = ""
        self._pending_json_payload = None

        mode = self.combo_mode.currentData() or "binary"
        bin_path = self._resolve_binary_path()
        go_exe = shutil.which("go")

        program: str = ""
        args: List[str] = []
        working_dir: Path = self._repo_root

        if mode == "binary" and bin_path.exists():
            program = str(bin_path)
            args = [f"--action={action}", f"--target={target}", *extra_args]
            self._append_line(f"▶ [Binary Mode] {bin_path.name} --action={action} --target={target}")
        elif mode == "go_run" and go_exe:
            program = go_exe
            args = ["run", ".", f"--action={action}", f"--target={target}", *extra_args]
            working_dir = self._go_engine_dir
            self._append_line(f"▶ [Go Script Mode] go run . --action={action} --target={target}")
        elif bin_path.exists():
            program = str(bin_path)
            args = [f"--action={action}", f"--target={target}", *extra_args]
            self._append_line(
                f"ℹ️ 'go' toolchain not found on PATH; using compiled binary {bin_path.name}..."
            )
        elif go_exe:
            program = go_exe
            args = ["run", ".", f"--action={action}", f"--target={target}", *extra_args]
            working_dir = self._go_engine_dir
            self._append_line(
                f"ℹ️ Compiled binary '{bin_path.name}' not found in /bin; falling back to 'go run .' in go_engine/..."
            )
        else:
            # Graceful non-blocking QProcess fallback when neither compiled binary nor Go compiler is installed yet
            self._append_line(
                f"ℹ️ '{bin_path.name}' not built yet & 'go' not on PATH (compile anytime via '🔨 Build Binaries')."
            )
            self._append_line(
                f"▶ [Async Fallback Engine] Running --action={action} --target={target}..."
            )
            program = sys.executable
            args = [
                str(Path(__file__).resolve()),
                "--fallback-cli",
                f"--action={action}",
                f"--target={target}",
                *extra_args,
            ]

        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(working_dir))
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self._process.readyReadStandardError.connect(self._on_stderr_ready)
        self._process.finished.connect(self._on_process_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        self._set_running_ui_state(True, f"Running {action} on {target}...")
        self._process.start(program, args)

    def stop_process(self) -> None:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._append_line("⏹ [STOPPED] Diagnostic process terminated by user.")
            self._set_running_ui_state(False, "Stopped")

    def clear_console(self) -> None:
        self.console.clear()
        self.lbl_run_state.setText("Idle")
        self.lbl_run_state.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

    # ── Stream & JSON Signal Handlers ────────────────────────────────────────

    def _on_stdout_ready(self) -> None:
        if not self._process:
            return
        raw_bytes = self._process.readAllStandardOutput().data()
        text = raw_bytes.decode("utf-8", errors="replace")
        self._stdout_buffer += text
        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            self._process_output_line(line.rstrip("\r"))

    def _on_stderr_ready(self) -> None:
        if not self._process:
            return
        raw_bytes = self._process.readAllStandardError().data()
        text = raw_bytes.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip():
                self._append_line(f"[STDERR] {line.strip()}")

    def _process_output_line(self, line: str) -> None:
        stripped = line.strip()
        if not stripped:
            return
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
                if isinstance(payload, dict) and "action" in payload and "success" in payload:
                    ok = bool(payload.get("success"))
                    tag = "[PASS]" if ok else "[FAIL]"
                    act = payload.get("action", self._current_action)
                    tgt = payload.get("target", self._current_target)
                    os_arch = f"{payload.get('os', '')}/{payload.get('arch', '')}".strip("/")
                    self._append_line(f"═══ {tag} action='{act}' target='{tgt}' ({os_arch}) ═══\n")
                    self.lbl_run_state.setText(f"{tag} {act} ({tgt})")
                    color = COLORS["accent_success"] if ok else COLORS["accent_danger"]
                    self.lbl_run_state.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
                    self._pending_json_payload = payload
                    return
            except json.JSONDecodeError:
                pass
        self._append_line(stripped)

    def _on_process_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._on_stdout_ready()
        if self._stdout_buffer.strip():
            for rem_line in self._stdout_buffer.splitlines():
                self._process_output_line(rem_line)
            self._stdout_buffer = ""

        completed_payload = self._pending_json_payload
        self._pending_json_payload = None

        if self._current_action == "build-binaries":
            tag = "[PASS]" if exit_code == 0 else "[FAIL]"
            self._append_line(f"═══ {tag} Build finished (exit {exit_code}) ═══\n")
            color = COLORS["accent_success"] if exit_code == 0 else COLORS["accent_danger"]
            self.lbl_run_state.setText(f"{tag} Build")
            self.lbl_run_state.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            self._set_running_ui_state(False)
        elif completed_payload is not None:
            self._set_running_ui_state(False)
        else:
            self._set_running_ui_state(False, f"Finished (exit {exit_code})")

        self.lbl_engine_status.setText(self._detect_engine_badge())
        if completed_payload is not None:
            self.diagnostic_completed.emit(completed_payload)

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        self._append_line(f"[ERROR] QProcess error occurred ({error}).")
        self._set_running_ui_state(False, "Process error")

    def _set_running_ui_state(self, running: bool, state_text: Optional[str] = None) -> None:
        if running:
            self.progress_bar.setRange(0, 0)  # Indeterminate animation
        else:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
        self.btn_stop.setEnabled(running)
        self.btn_build_bins.setEnabled(not running)
        for btn in self._action_buttons:
            btn.setEnabled(not running)
        if state_text is not None:
            self.lbl_run_state.setText(state_text)
            if running:
                self.lbl_run_state.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: bold;")

    def _append_line(self, text: str) -> None:
        self.console.appendPlainText(text)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())


# ── Standalone Child-Process CLI & Interactive REPL Fallback ────────────────

def _is_fallback_admin() -> bool:
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return getattr(os, "geteuid", lambda: 1)() == 0


def _extract_host(target: str) -> str:
    cleaned = target.strip()
    for prefix in ("https://", "http://"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]
    if ":" in cleaned and not cleaned.startswith("["):
        host_part, _ = cleaned.rsplit(":", 1)
        if host_part:
            return host_part
    return cleaned


def _fallback_ping(target: str) -> Tuple[str, bool]:
    host = _extract_host(target)
    lines: List[str] = []
    try:
        infos = socket.getaddrinfo(host, None)
        addrs = sorted({info[4][0] for info in infos if info[4]})
        lines.append(f"Resolved {host} -> {', '.join(addrs[:4])}")
    except Exception as exc:
        return f"DNS resolution failed for {host}: {exc}", False

    reachable = 0
    for port in (443, 80, 53):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=2.0):
                ms = int((time.perf_counter() - t0) * 1000)
                reachable += 1
                lines.append(f"TCP {host}:{port} -> OPEN (RTT: {ms}ms)")
        except Exception as exc:
            lines.append(f"TCP {host}:{port} -> UNREACHABLE ({exc})")
    return "\n".join(lines), reachable > 0


def _fallback_port_scan(target: str) -> Tuple[str, bool]:
    host = _extract_host(target)
    ports = [22, 53, 80, 443, 3389, 8080]

    def probe(p: int) -> Tuple[int, bool, int]:
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, p), timeout=2.0):
                return p, True, int((time.perf_counter() - t0) * 1000)
        except Exception:
            return p, False, int((time.perf_counter() - t0) * 1000)

    results: List[Tuple[int, bool, int]] = []
    with ThreadPoolExecutor(max_workers=len(ports)) as pool:
        futures = [pool.submit(probe, p) for p in ports]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda item: item[0])

    lines: List[str] = []
    open_count = 0
    for p, is_open, ms in results:
        if is_open:
            open_count += 1
            lines.append(f"Port {p:<5d} : OPEN ({ms}ms)")
        else:
            lines.append(f"Port {p:<5d} : CLOSED/FILTERED")
    lines.append(f"Summary: {open_count}/{len(ports)} scanned ports open on {host}")
    return "\n".join(lines), True


def _fallback_tls_check(target: str) -> Tuple[str, bool]:
    host = _extract_host(target)
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=4.0) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                not_before = cert.get("notBefore", "Unknown")
                not_after = cert.get("notAfter", "Unknown")
                subj_tuples = cert.get("subject", ())
                issuer_tuples = cert.get("issuer", ())
                subj = ", ".join(f"{k}={v}" for rdn in subj_tuples for k, v in rdn) or host
                issuer = ", ".join(f"{k}={v}" for rdn in issuer_tuples for k, v in rdn) or "Unknown"
                lines = [
                    f"Target      : {host}:443 ({ssock.version()} / {cipher[0] if cipher else ''})",
                    f"Subject     : {subj}",
                    f"Issuer      : {issuer}",
                    f"Valid From  : {not_before}",
                    f"Valid Until : {not_after}",
                ]
                return "\n".join(lines), True
    except Exception as exc:
        return f"TLS handshake failed for {host}:443: {exc}", False


def _fallback_http_check(target: str) -> Tuple[str, bool]:
    raw = target.strip()
    if raw.lower().startswith(("http://", "https://")):
        urls = [raw]
    else:
        urls = [f"https://{raw}", f"http://{raw}"]

    last_err: Optional[Exception] = None
    for url in urls:
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": "TimeSpace-Diag/3.5"})
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                ms = int((time.perf_counter() - t0) * 1000)
                status_code = getattr(resp, "status", 200)
                reason = getattr(resp, "reason", "OK")
                server_hdr = resp.headers.get("Server") or "(not disclosed)"
                final_url = resp.geturl()
                lines = [
                    f"Request URL : {url}",
                    f"Final URL   : {final_url}",
                    f"HTTP Status : {status_code} {reason}",
                    f"Latency     : {ms}ms",
                    f"Server      : {server_hdr}",
                ]
                return "\n".join(lines), status_code < 400
        except urllib.error.HTTPError as http_err:
            ms = int((time.perf_counter() - t0) * 1000)
            server_hdr = http_err.headers.get("Server") if http_err.headers else "(not disclosed)"
            lines = [
                f"Request URL : {url}",
                f"HTTP Status : {http_err.code} {http_err.reason}",
                f"Latency     : {ms}ms",
                f"Server      : {server_hdr or '(not disclosed)'}",
            ]
            return "\n".join(lines), False
        except Exception as exc:
            last_err = exc
    return f"HTTP/HTTPS probe failed for {target}: {last_err}", False


def _fallback_dns_lookup(target: str) -> Tuple[str, bool]:
    host = _extract_host(target)
    lines: List[str] = []
    try:
        infos = socket.getaddrinfo(host, None)
        v4 = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET and info[4]})
        v6 = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET6 and info[4]})
        if v4:
            lines.append(f"A (IPv4)    : {', '.join(v4)}")
        if v6:
            lines.append(f"AAAA (IPv6) : {', '.join(v6)}")
    except Exception as exc:
        return f"DNS lookup failed for {host}: {exc}", False

    try:
        fqdn = socket.getfqdn(host)
        if fqdn and fqdn.lower() != host.lower():
            lines.append(f"FQDN/PTR    : {fqdn}")
    except Exception:
        pass

    if shutil.which("nslookup"):
        for qtype in ("MX", "NS", "TXT"):
            try:
                proc = subprocess.run(
                    ["nslookup", f"-type={qtype}", host],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                matched = [
                    ln.strip()
                    for ln in (proc.stdout or "").splitlines()
                    if any(k in ln.lower() for k in ("mail exchanger", "nameserver", "text ="))
                ]
                if matched:
                    lines.append(f"{qtype:<11s} : {'; '.join(matched[:3])}")
            except Exception:
                pass

    return "\n".join(lines), bool(lines)


def _fallback_os_action(action: str) -> Tuple[str, bool]:
    if sys.platform == "win32":
        cmd_map = {
            "flush-dns": ["ipconfig", "/flushdns"],
            "net-status": ["netsh", "interface", "ip", "show", "config"],
            "net-reset": ["netsh", "interface", "ip", "show", "config"],
            "sys-info": ["netstat", "-ep"],
            "sys-health": ["netstat", "-ep"],
        }
    elif sys.platform == "darwin":
        cmd_map = {
            "flush-dns": ["dscacheutil", "-flushcache"],
            "net-status": ["ifconfig"],
            "net-reset": ["ifconfig"],
            "sys-info": ["uptime"],
            "sys-health": ["uptime"],
        }
    else:
        cmd_map = {
            "flush-dns": ["resolvectl", "flush-caches"],
            "net-status": ["ip", "-brief", "addr"],
            "net-reset": ["ip", "-brief", "addr"],
            "sys-info": ["uptime"],
            "sys-health": ["uptime"],
        }
    cmd = cmd_map.get(action)
    if not cmd:
        return f"Unsupported action: {action}", False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip(), proc.returncode == 0
    except Exception as exc:
        return f"OS command failed: {exc}", False


def _execute_fallback_action(action: str, target: str) -> Tuple[str, bool]:
    if action == "ping":
        return _fallback_ping(target)
    if action == "port-scan":
        return _fallback_port_scan(target)
    if action == "tls-check":
        return _fallback_tls_check(target)
    if action == "http-check":
        return _fallback_http_check(target)
    if action == "dns-lookup":
        return _fallback_dns_lookup(target)
    if action in ("flush-dns", "net-status", "net-reset", "sys-info", "sys-health"):
        return _fallback_os_action(action)
    return f"Unknown action '{action}'", False


def _hex_to_ansi_fg(hex_color: str, bold: bool = False) -> str:
    cleaned = hex_color.lstrip("#")
    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)
    prefix = "1;" if bold else ""
    return f"\x1b[{prefix}38;2;{r};{g};{b}m"


def _supports_repl_ansi() -> bool:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.environ.get("NO_COLOR"):
        return False
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
        except Exception:
            pass
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _clear_repl_screen(use_color: bool) -> None:
    if use_color:
        print("\x1b[2J\x1b[3J\x1b[H", end="", flush=True)
        return
    if getattr(sys.stdout, "isatty", lambda: False)():
        os.system("cls" if sys.platform == "win32" else "clear")


_REPL_OPTION_MAP: Dict[str, List[str]] = {
    "1": ["ping"],
    "ping": ["ping"],
    "2": ["port-scan"],
    "port-scan": ["port-scan"],
    "3": ["tls-check"],
    "tls-check": ["tls-check"],
    "4": ["flush-dns"],
    "flush-dns": ["flush-dns"],
    "5": ["http-check"],
    "http-check": ["http-check"],
    "6": ["dns-lookup"],
    "dns-lookup": ["dns-lookup"],
    "7": ["ping", "port-scan", "tls-check", "http-check", "dns-lookup", "net-status"],
    "playbook": ["ping", "port-scan", "tls-check", "http-check", "dns-lookup", "net-status"],
}


def _parse_repl_selection(raw: str) -> Tuple[List[str], Optional[str]]:
    normalized = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", raw.strip().lower())
    tokens = [t for t in re.split(r"[\s,]+", normalized) if t]

    actions: List[str] = []
    seen = set()

    def _append_unique(items: List[str]) -> None:
        for act in items:
            if act not in seen:
                seen.add(act)
                actions.append(act)

    for tok in tokens:
        if tok in _REPL_OPTION_MAP:
            _append_unique(_REPL_OPTION_MAP[tok])
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m:
            start_num, end_num = int(m.group(1)), int(m.group(2))
            if start_num < 1 or end_num > 7 or start_num > end_num:
                return [], f"Invalid range '{tok}' (enter ranges within 1-7, e.g., 1-4)"
            for num in range(start_num, end_num + 1):
                _append_unique(_REPL_OPTION_MAP[str(num)])
            continue
        if tok.isdigit():
            return [], f"Option '{tok}' is out of range (choose 1-7)"
        return [], f"Unrecognized command '{tok}'"

    if not actions:
        return [], "No diagnostic options selected"
    return actions, None


def _run_fallback_repl(initial_target: str) -> int:
    target = initial_target.strip() or "1.1.1.1"
    goos = "windows" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    arch = platform.machine().lower() or "amd64"
    priv_badge = "[ADMIN / ROOT]" if _is_fallback_admin() else "[STANDARD USER]"

    use_color = _supports_repl_ansi()
    p_bold = _hex_to_ansi_fg(COLORS["accent"], bold=True) if use_color else ""
    p_norm = _hex_to_ansi_fg(COLORS["accent"], bold=False) if use_color else ""
    ok_col = _hex_to_ansi_fg(COLORS["accent_success"], bold=True) if use_color else ""
    fail_col = _hex_to_ansi_fg(COLORS["accent_danger"], bold=True) if use_color else ""
    rst = "\x1b[0m" if use_color else ""

    while True:
        print(f"{p_bold}═══════════════════════════════════════════════════════════════════{rst}", flush=True)
        print(f"{p_bold}  🪻 TimeSpace Go Diagnostic REPL | {goos}/{arch} | {priv_badge}{rst}", flush=True)
        print(f"{p_bold}  Active Target: {target}{rst}", flush=True)
        print(f"{p_bold}═══════════════════════════════════════════════════════════════════{rst}", flush=True)
        print(f"{p_norm}  [1] Ping & TCP Reachability{rst}", flush=True)
        print(f"{p_norm}  [2] Concurrent Port Scan (22, 53, 80, 443, 3389, 8080){rst}", flush=True)
        print(f"{p_norm}  [3] TLS Certificate Inspector{rst}", flush=True)
        print(f"{p_norm}  [4] Flush DNS Cache (OS Fix){rst}", flush=True)
        print(f"{p_norm}  [5] HTTP/HTTPS Status & Latency Probe{rst}", flush=True)
        print(f"{p_norm}  [6] DNS Records Inspector (A / AAAA / MX / NS / TXT){rst}", flush=True)
        print(f"{p_norm}  [7] Automated Network Triage Playbook (All Checks){rst}", flush=True)
        print(f"{p_norm}  ─────────────────────────────────────────────────────────────────{rst}", flush=True)
        print(f"{p_norm}  Multi-Select   — Enter multiple or ranges (e.g., 1,3,4 or 1-4, 6){rst}", flush=True)
        print(f"{p_norm}  target <host>  — Change active target host/IP{rst}", flush=True)
        print(f"{p_norm}  clr            — Clear terminal screen{rst}", flush=True)
        print(f"{p_norm}  exit           — Close interactive session{rst}", flush=True)
        try:
            print(f"\n{p_bold}TimeSpace-Go> {rst}", end="", flush=True)
            raw = input()
        except EOFError:
            print(flush=True)
            return 0

        cmd = raw.strip()
        if not cmd:
            continue
        lower = cmd.lower()
        if lower in ("exit", "quit", "q"):
            print("Exiting TimeSpace Diagnostic REPL.", flush=True)
            return 0
        if lower in ("clr", "clear", "cls"):
            _clear_repl_screen(use_color)
            continue
        if lower.startswith("target "):
            new_tgt = cmd[7:].strip()
            if new_tgt:
                target = new_tgt
                print(f"{ok_col}✔ Active target updated to: {target}{rst}\n", flush=True)
            continue

        actions, parse_err = _parse_repl_selection(cmd)
        if parse_err is not None:
            print(
                f"{fail_col}✖ {parse_err}. Enter 1-7 (e.g., 1,3,4 or 1-4, 6), 'target <host>', 'clr', or 'exit'.{rst}\n",
                flush=True,
            )
            continue

        total = len(actions)
        for idx, act in enumerate(actions, start=1):
            step_prefix = f"[{idx}/{total}] " if total > 1 else ""
            print(f"\n{p_bold}▶ {step_prefix}Running '{act}' on '{target}'...{rst}", flush=True)
            out, ok = _execute_fallback_action(act, target)
            if out:
                print(out, flush=True)
            if ok:
                print(f"{ok_col}✔ [PASS] {act} completed.{rst}", flush=True)
            else:
                print(f"{fail_col}✖ [FAIL] {act} completed.{rst}", flush=True)
        print(flush=True)


def _run_fallback_cli() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fallback-cli", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--action", default="ping")
    parser.add_argument("--target", default="1.1.1.1")
    known, _ = parser.parse_known_args()

    action = known.action.strip().lower()
    target = known.target.strip() or "1.1.1.1"

    if known.interactive:
        return _run_fallback_repl(target)

    goos = "windows" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    arch = platform.machine().lower() or "amd64"
    priv = "ADMIN/ROOT" if _is_fallback_admin() else "STANDARD"

    print(f"[Diagnostic Worker {goos}/{arch} | {priv}] Starting action='{action}' target='{target}'...", flush=True)

    output, ok = _execute_fallback_action(action, target)
    if output:
        for line in output.splitlines():
            print(line, flush=True)

    payload: Dict[str, Any] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "os": goos,
        "arch": arch,
        "action": action,
        "target": target,
        "success": ok,
        "output": output,
    }
    print(json.dumps(payload), flush=True)
    return 0 if ok else 1


if __name__ == "__main__" and "--fallback-cli" in sys.argv:
    sys.exit(_run_fallback_cli())
