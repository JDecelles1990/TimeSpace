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
│   ├── scratchpad.json        # Auto-saved ScratchpadState time notes (plain text + rich HTML)
│   ├── hotstrings.json        # Saved AHKHotstringItem records for visual table editor
│   └── hotstrings.ahk         # Compiled strict AutoHotkey v2 executable script
├── Docs/
│   ├── ARCHITECTURE.md        # Dual-mode F7Hub runtime, concurrency & Win32 subsystems
│   ├── STATE_AND_CONFIG.md    # Dataclasses, UI_DIMENSIONS, COLORS, DARK_QSS & JSON schemas
│   ├── COMPONENT_MAP.md       # File tree, module APIs & widget hierarchy (this file)
│   ├── USER_GUIDE.md          # End-user manual, 7-tab workflows & NLP grammar
│   └── CHANGELOG.md           # Chronological engineering & migration changelog
└── src/
    ├── __init__.py            # Public package exports (__all__)
    ├── config.py              # Constants, presets, DARK_QSS, AppConfig, HistoryEntry, ScratchpadState, AHKHotstringItem
    ├── storage.py             # Storage class for JSON persistence & AHK script text
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
    ├── ahk_manager.py         # AHKProcessManager(QObject), find_ahk_v2_exe, generate_ahk_v2_script
    ├── ahk_dialog.py          # AHKHotstringsDialog(QDialog) & AHKItemEditDialog(QDialog)
    └── gui.py                 # ScratchpadUrlHighlighter, ScratchpadEditor, SchedulerBridge, TimerRendezVousWidget & MainApp
```

---

## 2. Module Signatures & Dependency Matrix

| File | Public Classes / Functions / Signals | Imports From `src.*` | Responsibility |
|---|---|---|---|
| `run.py` | `_ensure_pyside6_interpreter() -> None` | `src.gui.MainApp` | Verifies `PySide6` availability (re-executes via `.venv` if missing) and starts `MainApp`. |
| `src/__init__.py` | Re-exports config tokens, dataclasses, `Storage`, `ReminderScheduler`, `ScheduledItem`, `GlobalHotkeyListener`, `GoTroubleshootingTab`, `TimerRendezVousWidget`, `MainApp` | `config`, `storage`, `scheduler`, `hotkey_manager`, `go_tab`, `gui` | Clean package facade for F7Hub or external callers. |
| `src/config.py` | `COLORS`, `DARK_QSS`, `UI_DIMENSIONS`, `SOUND_PRESETS`, `CATEGORIES`, `QUICK_TIMER_PRESETS`, `SNOOZE_OPTIONS`, `SCRATCHPAD_TEXT_COLORS`, `GO_DIAG_ACTIONS`, `GO_TARGET_PRESETS`, `AppConfig`, `HistoryEntry`, `ScratchpadState` | *(None — leaf module)* | Single source of truth for styling, geometry, presets, and typed config/state dataclasses. |
| `src/storage.py` | `Storage.load_config()`, `save_config()`, `load_reminders()`, `save_reminders()`, `load_history()`, `add_history_entry()`, `delete_history_indices()`, `clear_history()`, `load_scratchpad()`, `save_scratchpad()`, `load_hotstrings()`, `save_hotstrings()`, `load_ahk_script_text()`, `save_ahk_script_text()`, `default_report_path()`, `export_diagnostic_report()`, `export_scratchpad_note()` | `src.config` | Thread-tolerant JSON file I/O, diagnostic incident report export (`.md`, `.txt`, `.json`), 1-click Scratchpad Markdown export (`C:\Temp`), and AutoHotkey v2 state persistence with automatic directory creation. |
| `src/scheduler.py` | `ScheduledItem`, `ReminderScheduler(on_trigger_callback, on_wake_missed_callback)` (`add_item`, `get_item`, `update_item`, `remove_item`, `toggle_pause`, `get_nearest_item`, `get_active_timer`, `get_events_for_date`, `get_all_event_dates`) | `src.storage` | Background countdown & calendar scheduler with inline item updates, pause/resume, recurrence, and sleep-drift detection. |
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
| `src/go_tab.py` | `GoConsoleHighlighter(QSyntaxHighlighter)`, `GoTroubleshootingTab(parent)` — Signals: `diagnostic_completed(dict)`, `sendToScratchpad(str)`, `customTargetsChanged(list)` (`run_diagnostic(action)`, `build_go_binaries()`, `launch_interactive_go_cli()`, `attach_scratchpad_widget()`, `set_custom_targets()`, `save_current_target_bookmark()`, `remove_current_target_bookmark()`, `copy_console_output()`, `send_console_to_scratchpad()`, `export_console_report()`, `stop_process()`, `clear_console()`) | `src.config`, `src.storage` | Non-blocking `QProcess` launcher for cross-platform Go diagnostic binaries (`bin/`), `go run .` (`go_engine/`), 1-click `build_all.ps1` compilation, custom target bookmarking (`[⭐]` / `[✕]` + `bm` REPL command), dedicated `[🛡️ Admin Go CLI]` and `[🚀 Standard Go CLI]` launchers, vertical `QSplitter` hosting the 3rd Rich-Text Scratchpad, report export, color-highlighted output, and async fallback worker. |
| `src/ahk_manager.py` | `find_ahk_v2_exe(custom_path) -> Optional[str]`, `clean_hotstring_trigger(trig) -> str`, `normalize_hotstring_options(opts, is_expr) -> str`, `generate_ahk_v2_script(items) -> str`, `AHKProcessManager(QObject)` — Signals: `statusChanged(bool, int)`, `errorOccurred(str)`, `outputReceived(str)` (`start_script()`, `reload_script()`, `stop_script()`, `is_running()`, `get_pid()`) | `src.config` | Strict AutoHotkey v2 executable discovery, 100% compliant v2 code generation (`#Requires AutoHotkey v2.0+`), and background child process lifecycle management via `QProcess`. |
| `src/ahk_dialog.py` | `AHKItemEditDialog(QDialog)`, `AHKHotstringsDialog(QDialog)` | `src.config`, `src.storage`, `src.ahk_manager` | Dual-mode AutoHotkey v2 text expanders manager: visual `QTableWidget` editor (search, add/edit/delete/dup, move, templates) and monospace `.ahk` script editor (`data/hotstrings.ahk`). |
| `src/meeting_detector.py` | `is_microphone_in_use() -> bool`, `get_active_microphone_apps() -> List[str]` | *(None — winreg / stdlib)* | Zero-dependency native Windows 10/11 microphone capture activity detector querying `CapabilityAccessManager\ConsentStore\microphone` (`NonPackaged` & `Packaged`). |
| `src/gui.py` | `ButtonGlowFilter(QObject)`, `ScratchpadUrlHighlighter(QSyntaxHighlighter)`, `ScratchpadEditor(QTextEdit)` — Signals: `linkActivated(str)`, `scheduleContextRequested()`, `RichScratchpadPane(QWidget)` — Signals: `contentModified()`, `scheduleRequested(str, str, int)`, `HistoryListWidget(QListWidget)` — Signal: `deleteKeyPressed()`, `SchedulerBridge(QObject)`, `TimerRendezVousWidget(QWidget)`, `MainApp(QMainWindow)` | All `src.*` modules | Main UI composition, 7-tab workflow wiring, keys `1`–`7` tab shortcuts, header/settings window opacity sliders, Meeting Mode controller & right-click timed presets (`30m`, `1h`, `2h`, `17:00`), `Ctrl+Shift+M` shortcut, inline active timer/RDV editing, 3 rich-text clickable-URL Scratchpads, Settings AHK v2 text expanders group, 1s `QTimer` refresh loop, and standalone shell (`480x540` min size). |

---

## 3. PySide6 UI Widget Composition Tree (`src/gui.py`)

```
MainApp (QMainWindow — standalone shell, minSize=480x540, opacity=AppConfig.app_opacity)
 └── TimerRendezVousWidget (QWidget — pluggable F7Hub root)
      ├── Header Bar (QHBoxLayout): App Title, Shortcut Hint ("Ctrl+F8 | Keys 1-7"), btn_meeting_mode ("🔔 Normal" / "🤫 Meeting"), slider_header_opacity (45–100%, default 90%) + lbl_header_opacity, btn_hud_toggle ("📌 HUD")
      ├── Hero Deck (QFrame, visible on Tabs 1, 2, 3, 6; hidden on Tabs 4, 5, 7):
      │    ├── Left: CircularProgressRing (124px) + [⏸️] / [⏹️]
      │    └── Right: smart_entry (QLineEdit) + [⚡] + smart_feedback (QLabel)
      ├── Module Tabs (QTabWidget, keys 1–7 / Alt+1–7 navigation):
      │    ├── Tab 1 ("1. Timers ⏳"): Compact Presets (15m, 30m, 1h, 2h) + [✏️] Edit Active + Task Form (Task, Ref, 🔗 Link, 📝 Note, h/m/s, 🔁 Repeat, [▶️] Start / [💾] Update + [✖] Cancel)
      │    ├── Tab 2 ("2. RDV 📅"): MiniCalendar + Day Agenda (left) | Responsive Appointment Details (Event, BigButtonsTimePicker, 🔗 Link, 📝 Note, Cat, Alert, Repeat, [📤 .ics], [📥 .ics], [✏️], [➕ RDV] / [💾 RDV] + [✖])
      │    ├── Tab 3 ("3. Activity 📋"): Full-height side-by-side QListWidgets (All Timers | All Rendez-vous, double-click or [✏️] to edit, [⏸️], [🗑️], [🔗])
      │    ├── Tab 4 ("4. Scratchpad 📝"): Vertical QSplitter with Dual RichScratchpadPanes (Upper Scratchpad 1 + Lower Scratchpad 2; each with [𝐁], [🎨], [🕒], [🔍] Ctrl+F Find Bar, [⏰] Schedule Selection, [💾] Export to C:\Temp, [📋], [🧹] and clickable URLs)
      │    ├── Tab 5 ("5. Go ⏱️"): GoTroubleshootingTab (Engine Mode + [🔨], Target + Presets + [⭐] / [✕] Bookmarks + Args, 2x4 Action Grid, [🛡️ Admin Go CLI] + [🚀 Standard Go CLI], Progress + [📋] [📝] [💾] [⏹️] [🧹], Vertical QSplitter: Live Console + 3rd RichScratchpadPane)
      │    ├── Tab 6 ("6. History 📜"): Full-height HistoryListWidget (Delete key or [🗑️] removes selected items, [🔗], [📋], [🧹])
      │    └── Tab 7 ("7. Settings ⚙️"): Alarm Tone + [🔊], Master Volume, App Transparency QSlider (45–100%, synced with Header), Popup & HUD Opacity QSlider (60–100%), Audio File [📂], Escalation, Boot Startup, Snooze, [💾], ⌨️ AutoHotkey v2 Text Expanders Group ([⚡ Set Up & Edit AHK v2 Hotstrings...], [▶️ Run], [⏹️ Stop], Auto-start Checkbox)
      ├── Active Reminders Queue (QGroupBox, visible on Tabs 1, 2, 7; hidden on Tabs 3, 4, 5, 6):
      │    └── Queue status + [⏸️] + [✏️] + [🗑️] + multi-row QListWidget (double-click any item to edit inline)
      └── Top-Level Overlays (spawned on demand, controlled by AppConfig.overlay_opacity):
           ├── FloatingMiniHUD (QWidget, frameless always-on-top)
           ├── AlarmDialog (QDialog, frameless bottom-right dynamic-height vertical stack)
           └── AHKHotstringsDialog (QDialog, dual-mode visual table & v2 code editor)
```
