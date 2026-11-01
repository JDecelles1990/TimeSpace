# Component Map & Module Signatures (`Docs/COMPONENT_MAP.md`)

> **Canonical Scope**: This document maps the repository file layout, per-module public classes/methods/Qt `Signal` signatures, dependency boundaries, and the PySide6 widget composition tree.
> *(For runtime threading and Win32 behavior, see [ARCHITECTURE.md](ARCHITECTURE.md). For dataclasses and constants, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## 1. Repository Directory Structure

```
TimeSpace/
├── AGENTS.md                  # Canonical AI Coding Agent governance & routing contract
├── README.md                  # Concise project overview & quick-start guide
├── LICENSE                    # MIT License
├── requirements.txt           # Dependencies (PySide6, keyboard, pystray, pillow)
├── run.py                     # CLI entry point with .venv PySide6 auto-relaunch
├── bin/                       # Output directory for compiled standalone Go CLIs (diag_windows.exe, diag_linux, diag_mac_arm64)
├── go_engine/                 # Cross-platform Go 1.22+ diagnostic & remediation engine
│   ├── go.mod                 # Go module definition (module timespace/diag)
│   ├── main.go                # Universal CLI entrypoint (--action, --target, --interactive REPL, JSON stdout)
│   ├── diag_common.go         # Pure-Go TCP reachability, concurrent port scan, TLS cert, HTTP/S probe & DNS lookup
│   ├── fixes_windows.go       # //go:build windows (ipconfig /flushdns, netsh, netstat)
│   ├── fixes_linux.go         # //go:build linux (resolvectl, ip addr, uptime)
│   ├── fixes_darwin.go        # //go:build darwin (dscacheutil, ifconfig, uptime)
│   └── build_all.ps1          # PowerShell 7 script to cross-compile Windows, Linux, and macOS binaries into /bin
├── data/                      # Auto-created JSON state directory (see STATE_AND_CONFIG.md)
│   ├── settings.example.json  # Reference template for AppConfig
│   ├── settings.json          # Active AppConfig preferences
│   ├── reminders.json         # Active ScheduledItem records
│   ├── history.json           # Completed/triggered HistoryEntry log (max 100)
│   └── scratchpad.json        # Auto-saved ScratchpadState time notes (plain text + rich HTML)
├── Docs/
│   ├── ARCHITECTURE.md        # Dual-mode F7Hub runtime, concurrency & Win32 subsystems
│   ├── STATE_AND_CONFIG.md    # Dataclasses, UI_DIMENSIONS, COLORS, DARK_QSS & JSON schemas
│   ├── COMPONENT_MAP.md       # File tree, module APIs & widget hierarchy (this file)
│   ├── USER_GUIDE.md          # End-user manual, 7-tab workflows & NLP grammar
│   └── CHANGELOG.md           # Chronological engineering & migration changelog
└── src/
    ├── __init__.py            # Public package exports (__all__)
    ├── config.py              # Constants, presets, DARK_QSS, AppConfig, HistoryEntry, ScratchpadState
    ├── storage.py             # Storage class for JSON persistence
    ├── scheduler.py           # ScheduledItem dataclass & thread-safe ReminderScheduler
    ├── sound.py               # SoundPlayer (winsound presets + Windows MCI MP3/WAV)
    ├── hotkey_manager.py      # GlobalHotkeyListener (Win32 RegisterHotKey / WM_HOTKEY)
    ├── tray.py                # TrayManager (pystray icon, dynamic tooltip, context menu)
    ├── notifications.py       # show_toast() Windows Action Center dispatcher
    ├── startup.py             # Windows HKCU Run registry helper (is_startup_enabled, set_startup_enabled)
    ├── natural_parser.py      # NaturalParser.parse() English timer/RDV expression parser
    ├── calendar_export.py     # CalendarManager RFC 5545 .ics export & import
    ├── circular_ring.py       # CircularProgressRing(QWidget) QPainter countdown visualizer
    ├── calendar_widget.py     # MiniCalendar(QWidget) monthly grid & relative date chips
    ├── time_picker.py         # BigButtonsTimePicker(QWidget) steppers, chips & presets
    ├── alarm_dialog.py        # AlarmDialog(QDialog) frameless bottom-right stacked toast card
    ├── mini_hud.py            # FloatingMiniHUD(QWidget) frameless draggable desktop pill
    ├── go_tab.py              # GoConsoleHighlighter & GoTroubleshootingTab(QWidget) non-blocking QProcess diagnostic launcher
    └── gui.py                 # ScratchpadUrlHighlighter, ScratchpadEditor, SchedulerBridge, TimerRendezVousWidget & MainApp
```

---

## 2. Module Signatures & Dependency Matrix

| File | Public Classes / Functions / Signals | Imports From `src.*` | Responsibility |
|---|---|---|---|
| `run.py` | `_ensure_pyside6_interpreter() -> None` | `src.gui.MainApp` | Verifies `PySide6` availability (re-executes via `.venv` if missing) and starts `MainApp`. |
| `src/__init__.py` | Re-exports config tokens, dataclasses, `Storage`, `ReminderScheduler`, `ScheduledItem`, `GlobalHotkeyListener`, `GoTroubleshootingTab`, `TimerRendezVousWidget`, `MainApp` | `config`, `storage`, `scheduler`, `hotkey_manager`, `go_tab`, `gui` | Clean package facade for F7Hub or external callers. |
| `src/config.py` | `COLORS`, `DARK_QSS`, `UI_DIMENSIONS`, `SOUND_PRESETS`, `CATEGORIES`, `QUICK_TIMER_PRESETS`, `SNOOZE_OPTIONS`, `SCRATCHPAD_TEXT_COLORS`, `GO_DIAG_ACTIONS`, `GO_TARGET_PRESETS`, `AppConfig`, `HistoryEntry`, `ScratchpadState` | *(None — leaf module)* | Single source of truth for styling, geometry, presets, and typed config/state dataclasses. |
| `src/storage.py` | `Storage.load_config()`, `save_config()`, `load_reminders()`, `save_reminders()`, `load_history()`, `add_history_entry()`, `clear_history()`, `load_scratchpad()`, `save_scratchpad()` | `src.config` | Thread-tolerant JSON file I/O with automatic directory creation and schema fallback. |
| `src/scheduler.py` | `ScheduledItem`, `ReminderScheduler(on_trigger_callback, on_wake_missed_callback)` (`add_item`, `remove_item`, `toggle_pause`, `get_nearest_item`, `get_active_timer`, `get_events_for_date`, `get_all_event_dates`) | `src.storage` | Background countdown & calendar scheduler with pause/resume, recurrence, and sleep-drift detection. |
| `src/sound.py` | `SoundPlayer(config)` (`update_config`, `start_alarm`, `stop_alarm`, `start_preview`, `stop_preview`) | `src.config`, `src.storage` | Synthesized chime patterns and hardware-volume MCI playback. |
| `src/hotkey_manager.py` | `GlobalHotkeyListener(hotkey_str, callback)` (`start()`, `stop()`) | *(None — Win32 leaf)* | Native Win32 `RegisterHotKey` listener thread with `keyboard` fallback. |
| `src/tray.py` | `TrayManager(on_toggle, on_exit, on_toggle_pause, on_toggle_hud)` (`start()`, `update_tooltip(text)`, `stop()`) | `src.config` | System tray icon and quick-action menu (`pystray` + `Pillow`). |
| `src/notifications.py` | `show_toast(title, message)`, `normalize_link_target(raw_link) -> str`, `open_attachment_link(raw_link) -> bool` | `src.config` | Non-blocking Windows 10/11 Action Center toast sender and OS URL/path launcher (`os.startfile` / `webbrowser`). |
| `src/startup.py` | `get_executable_command() -> str`, `is_startup_enabled() -> bool`, `set_startup_enabled(enable: bool) -> bool` | `src.config` | Manages Windows boot auto-launch registry entry. |
| `src/natural_parser.py` | `NaturalParser.parse(text: str) -> Optional[Dict[str, Any]]` | *(None — pure stdlib)* | Parses freeform English timer durations, relative days/weeks, weekdays, and appointment times. |
| `src/calendar_export.py` | `CalendarManager.export_to_ics(items, filepath) -> bool`, `import_from_ics(filepath) -> List[Dict]` | *(None — pure stdlib)* | Exports and imports Rendez-vous items (including `URL`, `DESCRIPTION`, and unfolded RFC 5545 lines) via `.ics`. |
| `src/circular_ring.py` | `CircularProgressRing(parent, size, ring_width)` (`update_countdown(...)`, `set_idle()`) | `src.config` | Custom `QPainter` anti-aliased radial countdown ring with pause & repeat badges. |
| `src/calendar_widget.py` | `MiniCalendar(parent, on_date_selected)` — Signal: `dateSelected(datetime.date)` (`set_event_dates`, `render_calendar`) | `src.config` | Monthly calendar grid with relative date chips (`Today`, `Tmrw`, `Fri`, `Mon`) and event dots (`•`). |
| `src/time_picker.py` | `BigButtonsTimePicker(parent, initial_hour, initial_minute, on_change)` — Signal: `timeChanged(int, int)` (`set_minute`, `set_time`, `get_time`) | `src.config` | Ergonomic hour/minute `+`/`−` steppers, `:00`/`:15`/`:30`/`:45` chips, and time presets. |
| `src/alarm_dialog.py` | `AlarmDialog(master, title_text, reminder_name, on_dismiss, on_snooze, on_open_link, category, url, note, config)` (`set_active_popups_opacity`) | `src.config`, `src.notifications` | Frameless `350x132` / `350x162` bottom-right stacked popup card with Dismiss, optional `🔗 Open Link`, Note preview, and Snooze. |
| `src/mini_hud.py` | `FloatingMiniHUD(master, on_toggle_pause, on_bring_main_to_front, on_close, initial_x, initial_y, opacity)` (`update_status`, `set_idle`, `set_hud_opacity`, `close_hud`) | `src.config` | Frameless `276x40` draggable always-on-top status pill with configurable opacity. |
| `src/go_tab.py` | `GoConsoleHighlighter(QSyntaxHighlighter)`, `GoTroubleshootingTab(parent)` — Signals: `diagnostic_completed(dict)`, `sendToScratchpad(str)` (`run_diagnostic(action)`, `build_go_binaries()`, `launch_interactive_go_cli()`, `copy_console_output()`, `send_console_to_scratchpad()`, `stop_process()`, `clear_console()`) | `src.config` | Non-blocking `QProcess` launcher for cross-platform Go diagnostic binaries (`bin/`), `go run .` (`go_engine/`), 1-click `build_all.ps1` compilation, elevated external interactive REPL (Win32 `ShellExecuteW` + UTF-16LE `-EncodedCommand` / `sudo` / `osascript`), color-highlighted output, and async fallback worker. |
| `src/gui.py` | `ScratchpadUrlHighlighter(QSyntaxHighlighter)`, `ScratchpadEditor(QTextEdit)` — Signal: `linkActivated(str)`, `SchedulerBridge(QObject)`, `TimerRendezVousWidget(QWidget)`, `MainApp(QMainWindow)` | All `src.*` modules | Main UI composition, 7-tab workflow wiring, rich-text & clickable-URL Scratchpad, 1s `QTimer` refresh loop, and standalone shell. |

---

## 3. PySide6 UI Widget Composition Tree (`src/gui.py`)

```
MainApp (QMainWindow — standalone shell only, 100% opaque)
 └── TimerRendezVousWidget (QWidget — pluggable F7Hub root)
      ├── Header Bar (QFrame): App Title, btn_hud_toggle ("📌 HUD: ON/OFF"), Hotkey Badge
      ├── Hero Deck (QFrame, side-by-side):
      │    ├── Left: CircularProgressRing (124px) + [⏯ Pause] / [⏹ Stop]
      │    └── Right: smart_entry (QLineEdit) + [Create ⚡] + smart_feedback (QLabel)
      ├── Module Tabs (QTabWidget, stretch=2):
      │    ├── Tab 1 ("1. Timers ⏳"): Quick Start Presets (15m/30m/1h/2h) + Daily Task Form (What to do, Client / Ticket #, Link + Short Note, h/min/sec, Repeat)
      │    ├── Tab 2 ("2. RDV 📅"): MiniCalendar + Day Agenda (left) | Event/Client, BigButtonsTimePicker, Link + Short Note, Category, Alert + Repeat, .ics I/O (right)
      │    ├── Tab 3 ("3. Activity 📋"): Full-height side-by-side QListWidgets (All Timers | All Rendez-vous) + inline detail bars + contextual [🔗 Open Link]
      │    ├── Tab 4 ("4. Scratchpad 📝"): Toolbar (𝐁 Bold Ctrl+B, 🎨 Color menu + custom picker, 🕒 +Timestamp Ctrl+T, 📋 Copy All, 🧹 Clear, save status) + ScratchpadEditor (QTextEdit + ScratchpadUrlHighlighter)
      │    ├── Tab 5 ("5. Go ⏱️"): GoTroubleshootingTab (Engine Mode QComboBox + [🔨 Build Binaries], Target + GO_TARGET_PRESETS QComboBox + CLI Args QLineEdit, 2x4 Action Grid, [⚡ Run as Admin / sudo] QCheckBox + [🚀 Launch Interactive Go CLI] QPushButton, Indeterminate QProgressBar + [📋 Copy] + [📝 +Scratchpad] + [⏹ Stop] + [🧹 Clear], Color-Highlighted Live Monospace QPlainTextEdit Console)
      │    ├── Tab 6 ("6. History 📜"): Full-height Completed/Triggered QListWidget + contextual [🔗 Open Link] + [📋 Copy Selected] + [🧹 Clear History] + detail bar
      │    └── Tab 7 ("7. Settings ⚙️"): Alarm Tone, [🔊 Preview], Master Volume QSlider, Popup & HUD Opacity QSlider (60–100%), Custom Audio, Escalation, Boot Startup, Default Snooze, [Save Settings ✓]
      ├── Active Reminders Queue (QGroupBox, stretch=3, visible across Tabs 1–4 & 6–7; auto-hidden on Tab 5 "5. Go ⏱️" for full-height console):
      │    └── Queue status + [⏯ Pause / Resume] + [🗑️ Delete] + multi-row QListWidget (minHeight=155px, 🔗/📝 indicators & tooltips)
      └── Top-Level Overlays (spawned on demand, controlled by AppConfig.overlay_opacity):
           ├── FloatingMiniHUD (QWidget, frameless always-on-top)
           └── AlarmDialog (QDialog, frameless bottom-right dynamic-height vertical stack)
```
