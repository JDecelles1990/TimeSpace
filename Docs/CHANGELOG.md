# Engineering & Migration Changelog (`Docs/CHANGELOG.md`)

> **Canonical Scope**: Chronological record of all architectural refactors, UI migrations, layout adjustments, bug fixes, and intentionally removed features across **TimeSpace** (formerly *Timer & Rendez-vous*).
> *(For current system design, see [ARCHITECTURE.md](ARCHITECTURE.md). For state schemas, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## [v3.9] — Neon Gradient Button Glow & Countdown SpinBox Sizing (2026-11-09)
- **Countdown Number Display Fix (`1. Timers ⏳`, `src/gui.py`)**: Enlarged `spin_h`, `spin_m`, and `spin_s` width bounds (`setMinimumWidth(75)`, `setMaximumWidth(110)`, up from the restrictive `maxWidth=62px` cap). This expands the internal `QLineEdit` from 13px to 48–54px (and 35–42px at minimum 480px window width), ensuring countdown numbers and suffixes (`0 h`, `15 m`, `0 s`) are fully visible and never clipped behind native spin stepper arrows.
- **Violet ➔ Cyan Hover & Cyan ➔ Green Pressed Gradients (src/config.py, src/gui.py)**: Added glow_violet, glow_violet_light, glow_cyan, glow_green COLORS tokens and rewrote the QPushButton hover/pressed DARK_QSS rules (including #primaryBtn, #successBtn, #dangerBtn) with qlineargradient fills. Added ButtonGlowFilter(QObject) (src/gui.py) installed by TimerRendezVousWidget, applying a QGraphicsDropShadowEffect neon glow (violet on hover, cyan on press) to every QPushButton and removing it on leave.
- **Gradient Tab Buttons (src/config.py)**: The 7 QTabBar::tab buttons now use a violet ➔ cyan gradient on hover and a cyan ➔ green gradient on the selected (clicked) tab. *(QTabBar tabs are not widgets, so they get the gradients but not the drop-shadow glow.)*

---

## [v3.8] — Scratchpad Power Tools (`Ctrl+F`, Schedule Selection, `C:\Temp` Export) & Custom Go Target Bookmarks (2026-11-08)
- **Scratchpad Power Tools Across All 3 Rich-Text Scratchpads (`src/gui.py`, `src/storage.py`)**:
  - **Inline `Ctrl+F` Search Bar (`🔍`)**: Added a toggleable compact find bar (`find_bar`, `entry_find`, `▲` previous, `▼` next, `✖` close, `Ctrl+F` open, `Escape` close) inside `RichScratchpadPane` with wrap-around case-insensitive search and emerald/crimson match feedback.
  - **Schedule Highlighted Text as Timer / RDV (`⏰`)**: Added `btn_schedule` (`⏰`) and right-click context menu integration (`ScratchpadEditor.scheduleContextRequested`) that extracts the highlighted text (or current cursor line), automatically pulls any embedded URL into the reminder's `url` attachment field, and offers 1-click scheduling via `NaturalParser.parse()`, quick timers (`15m`, `30m`, `1h`, `2h`), or pre-filling Tab 1 (`1. Timers ⏳`) / Tab 2 (`2. RDV 📅`).
  - **1-Click Scratchpad Markdown Export to `C:\Temp` (`💾` / `Ctrl+S`)**: Added `Storage.export_scratchpad_note()` (`src/storage.py`) and `btn_export` (`💾` + `Ctrl+S` shortcut) to export any of the 3 Scratchpads directly to `C:\Temp\TimeSpace_Scratchpad_<slug>_<timestamp>.md`.
- **Custom Saved Target Bookmarks in `5. Go ⏱️` & Interactive Go CLI (`src/config.py`, `src/go_tab.py`, `src/gui.py`, `go_engine/main.go`)**:
  - Added `AppConfig.custom_go_targets: List[Dict[str, str]]` persisted in `data/settings.json` with automatic sanitization in `AppConfig.from_dict()`.
  - Added **`⭐`** (`save_current_target_bookmark()`, supporting optional `Label | host` syntax) and **`✕`** (`remove_current_target_bookmark()`) next to `combo_presets` in `GoTroubleshootingTab`, displaying user bookmarks at the top of the presets dropdown (`⭐ Label (host)`).
  - Added the `bm [n|add|del]` (alias `bookmarks`) command to both the pure-Go Interactive CLI (`go_engine/main.go`) and the Python fallback REPL (`src/go_tab.py`) to list, select, add, and delete custom target bookmarks directly from the terminal.

---

## [v3.7] — Compact Emoji UI, Inline Timer/RDV Editing, 3 Rich Scratchpads, Opacity Sliders & Tab Hotkeys (2026-11-08)
- **Section 1 (`1. Timers ⏳`) — Compact Presets, Non-Overlapping Countdown Row & Inline Active Editing (`src/config.py`, `src/scheduler.py`, `src/gui.py`)**:
  - Shortened `QUICK_TIMER_PRESETS` labels to `15m`, `30m`, `1h`, `2h` with responsive sizing (`setMinimumWidth(0)`).
  - Replaced `"Start Timer ▶"` with compact `▶️` (`40px` width) and constrained `spin_h`, `spin_m`, `spin_s` widths (`maxWidth=62px`) with compact `🔁` repeat checkbox so controls never overlap when resized small.
  - Added `ReminderScheduler.get_item()` and `ReminderScheduler.update_item()` (`src/scheduler.py`) plus inline editing (`_begin_edit_timer`, `_begin_edit_rdv`, `✏️` button, and double-click on Queue/Activity items) that populates form fields and switches `▶️` to `💾` (with `✖` cancel) to update running timers and RDVs in-place.
- **Section 2 (`2. RDV 📅`) — Responsive 'Appointment Details' & Compact Emoji Buttons (`src/time_picker.py`, `src/gui.py`)**:
  - Rebuilt `BigButtonsTimePicker` (`src/time_picker.py`) with a responsive `QGridLayout`, `setMinimumWidth(0)`, and `set_time(h, m)` so controls never clip at narrow widths.
  - Updated RDV action buttons to `📤 .ics`, `📥 .ics`, `✏️`, and `➕ RDV` (switching to `💾 RDV` when editing an active RDV).
- **Section 3 (`3. Activity 📋`) & Section 6 (`6. History 📜`) — Full-Height Lists & `Delete` Key Binding (`src/storage.py`, `src/gui.py`)**:
  - Automatically hid the bottom `Active Reminders Queue` on Tab 3 (`3. Activity 📋`) and Tab 6 (`6. History 📜`) so lists expand to 100% of vertical space.
  - Added `HistoryListWidget(QListWidget)` (`deleteKeyPressed` on `Qt.Key.Key_Delete`) and `Storage.delete_history_indices()` (`src/storage.py`) to delete individual selected history items via the `Delete` key or `🗑️` button.
- **Section 4 (`4. Scratchpad 📝`) & Section 5 (`5. Go ⏱️`) — Hero Deck Cleanup, 3 Rich-Text Scratchpads & Dual CLI Buttons (`src/config.py`, `src/go_tab.py`, `src/gui.py`)**:
  - Automatically hid the top Hero Deck (circular timer + Quick Natural Schedule bar) on Tab 4 (`4. Scratchpad 📝`), Tab 5 (`5. Go ⏱️`), and Tab 7 (`7. Settings ⚙️`).
  - Added `RichScratchpadPane(QWidget)` (`src/gui.py`) and extended `ScratchpadState` (`upper_content`, `upper_html`, `go_content`, `go_html`) to provide **Dual Upper & Lower Rich-Text Scratchpads** inside a `QSplitter(Qt.Orientation.Vertical)` on Tab 4 and a **3rd Rich-Text Scratchpad** inside a vertical `QSplitter` below the live console on Tab 5 (all with `𝐁` Bold, `🎨` Color, `🕒` Timestamp, `📋` Copy, `🧹` Clear, and detectable clickable URLs).
  - Replaced the single CLI launch bar in `5. Go ⏱️` (`src/go_tab.py`) with two dedicated side-by-side buttons: **`🛡️ Admin Go CLI`** (`elevate_override=True`) and **`🚀 Standard Go CLI`** (`elevate_override=False`).
- **Section 7 (`7. Settings ⚙️`) & Global Window Improvements (`src/config.py`, `src/gui.py`)**:
  - Added `AppConfig.app_opacity` (`45–100%`, default `90%`) with a live **`🔆` Opacity Slider** in the top header bar (immediately to the left of the `📌 HUD` button) synchronized with an **App Transparency** slider in `7. Settings ⚙️`.
  - Added keyboard shortcuts **`1`–`7`** (and `Alt+1`–`Alt+7`) to navigate directly across all 7 tabs (`eventFilter` guarded so typing numbers in inputs works normally).
  - Updated `MainApp.toggle_visibility()` (`Ctrl+F7`) to minimize (`showMinimized()`) when visible or restore (`showNormal()`, `activateWindow()`) when minimized/hidden, and set the balanced minimum window size to `480×540`.

---

## [v3.6] — `5. Go ⏱️` Enhancements: Color Console, Scratchpad Bridge, HTTP/DNS Probes, Presets & Binary Builder (2026-11-01)
- **Color-Coded Live Output Console (`src/go_tab.py`)**:
  - Added `GoConsoleHighlighter(QSyntaxHighlighter)` highlighting `[PASS]`/`OPEN`/`✔`/`200 OK` in emerald green, `[FAIL]`/`[ERROR]`/`[STDERR]`/`UNREACHABLE`/`✖` in crimson red, `CLOSED/FILTERED`/`[WARN]`/`[STOPPED]`/`ELEVATED` in amber, and `═══` action headers in sky cyan using `COLORS` tokens.
- **1-Click Clipboard Copy, `+Scratchpad` Integration & Diagnostic Report Exporter (`src/go_tab.py`, `src/storage.py`, `src/gui.py`, `go_engine/main.go`)**:
  - Added **`📋 Copy`** (`copy_console_output()`), **`📝 +Scratchpad`** (`send_console_to_scratchpad()`, emitting `sendToScratchpad = Signal(str)` wired to `TimerRendezVousWidget._append_to_scratchpad()`), and **`💾 Export`** (`export_console_report()`, delegating to `Storage.export_diagnostic_report()` to save `.md`, `.txt`, or `.json` incident reports).
  - Automatically hidden the bottom **Active Reminders Queue** on **`4. Scratchpad 📝`** (as well as **`5. Go ⏱️`**), giving the Scratchpad editor full vertical window height for writing notes.
- **Expanded Diagnostic Suite to 8 Actions (`src/config.py`, `src/go_tab.py`, `go_engine/main.go`, `go_engine/diag_common.go`)**:
  - Added **`🌍 HTTP/S Probe`** (`--action=http-check`: HTTP/HTTPS status code, protocol, latency, redirect URL, and `Server` header) and **`🧭 DNS Lookup`** (`--action=dns-lookup`: `A`, `AAAA`, `CNAME`, `MX`, `NS`, and `TXT` records) in a `2×4` action grid across both pure Go (`go_engine/`) and the built-in Python fallback engine.
  - Upgraded the `--interactive` external REPL (`go_engine/main.go`, `go_engine/fixes_*.go`, and `src/go_tab.py`) into **two dedicated privilege-specific Interactive Go CLIs**:
    - **Standard User Diagnostic CLI (`--cli-mode=user`, `TimeSpace-User> `)**: 8 non-elevated diagnostic options (`[1] Ping`, `[2] Port Scan`, `[3] TLS Cert`, `[4] HTTP/S Probe`, `[5] DNS Lookup`, `[6] IP Config Summary`, `[7] Socket & Uptime Summary`, `[8] Standard User Playbook`).
    - **Elevated Admin Remediation & Deep Audit CLI (`--cli-mode=admin`, `TimeSpace-Admin⚡> `)**: 9 Administrator / `sudo` OS remediation & deep audit commands (`[1] Flush DNS`, `[2] Clear ARP & NetBIOS Cache`, `[3] Restart DNS Client Service`, `[4] Reset Winsock Catalog`, `[5] Reset TCP/IP Stack`, `[6] Elevated Port & Process Owner Audit`, `[7] OS Firewall Profiles Audit`, `[8] Kernel IPv4 Routing Table Audit`, `[9] Automated Admin Repair & Audit Playbook`).
    - **Multi-number & range selection** (`1,3,4`, `1-4, 6`) with deduplicated sequential execution and `[i/total]` step progress.
    - **`copy` command** (plus `cp` alias) to copy the last diagnostic batch output to the system clipboard (`clip.exe` UTF-16LE on Windows, `pbcopy` on macOS, `wl-copy`/`xclip`/`xsel` on Linux).
    - **`save [fmt]` command** (plus `export` alias) to export the last diagnostic output directly to `C:\Temp\TimeSpace_Diag_<target>_<timestamp>.<md|txt|json>` (auto-creating `C:\Temp` if missing).
    - **`clr` command** (plus `clear`/`cls` aliases) to clear the terminal viewport and scrollback buffer.
    - **TimeSpace Purple (`#6366f1`)** TrueColor ANSI main menu styling with native Windows Virtual Terminal Processing (`ENABLE_VIRTUAL_TERMINAL_PROCESSING`) and UTF-8 console codepage setup.
- **Quick Target Presets & 1-Click Binary Builder (`src/config.py`, `src/__init__.py`, `src/go_tab.py`)**:
  - Added `GO_TARGET_PRESETS` (`Cloudflare 1.1.1.1`, `Google 8.8.8.8`, `github.com`, `google.com`, `microsoft.com`, `127.0.0.1`) next to the Target input and **`🔨 Build Binaries`** (`build_go_binaries()`) to cross-compile `go_engine/build_all.ps1` non-blockingly via `QProcess` and refresh the engine readiness badge.

---

## [v3.5] — `5. Go ⏱️` Cross-Platform Diagnostic & Troubleshooting Module (2026-11-01)
- **Inserted `5. Go ⏱️` Tab Between `Scratchpad` and `History` (`src/go_tab.py`, `src/gui.py`, `src/config.py`, `src/__init__.py`)**:
  - Added `GoTroubleshootingTab(QWidget)` (`src/go_tab.py`) as Tab 5 (`5. Go ⏱️`), renumbering `History` to `6. History 📜` and `Settings` to `7. Settings ⚙️`, and tightened `QTabBar::tab` padding in `DARK_QSS` (`5px 7px`) so all 7 tabs fit on one row.
  - Implemented non-blocking process execution via `PySide6.QtCore.QProcess` and `pathlib.Path` with an Engine Mode selector (`Compiled Binary Mode` vs `Go Script Mode`), Target Host/IP + CLI Args inputs, a 2×3 grid of 6 diagnostic actions (`GO_DIAG_ACTIONS`), an external interactive CLI launcher bar (**`⚡ Run as Admin / sudo (Elevated Fixes)`** + **`🚀 Launch Interactive Go CLI (External Terminal)`** via Win32 `ShellExecuteW` + UTF-16LE `-EncodedCommand` on Windows and `QProcess.startDetached` on Linux/macOS), indeterminate `QProgressBar`, `⏹ Stop Process`, `🧹 Clear Console`, and a read-only monospace live console.
  - Added automatic JSON result parsing (`[PASS]` / `[FAIL]` banners), full-height console expansion on Tab 5 (auto-hiding `Active Reminders Queue` only while `5. Go ⏱️` is active), and connected `diagnostic_completed = Signal(dict)` to log completed diagnostic runs into `6. History 📜` via `Storage.add_history_entry(HistoryEntry(...))`.
  - Included a built-in asynchronous `QProcess` fallback worker and interactive REPL (`--interactive`) in `src/go_tab.py` so all 6 diagnostic actions and external terminal sessions run out of the box even when `bin/diag_*` has not been compiled yet and `go` is not on `PATH`.
- **Created Cross-Platform Go Engine (`go_engine/` & `bin/`)**:
  - Created `go_engine/go.mod`, `main.go` (supporting `--action`, `--target`, and `--interactive` REPL with `[ADMIN / ROOT]` vs `[STANDARD USER]` banner), `diag_common.go` (goroutine + `sync.WaitGroup` concurrent TCP port scan, `crypto/tls` certificate inspection, and TCP reachability probe), OS-specific build-tagged files (`fixes_windows.go`, `fixes_linux.go`, `fixes_darwin.go` implementing `isAdmin() bool` and `runOSAction()`), and `go_engine/build_all.ps1` (`CGO_ENABLED=0` cross-compiler for Windows, Linux, and macOS).

---

## [v3.4] — Rich-Text Scratchpad: Highlighted Bold, Text Color & Clickable Web Links (2026-11-01)
- **Rich-Text Scratchpad Formatting (`src/gui.py`, `src/config.py`, `src/__init__.py`)**:
  - Upgraded Tab 4 (`4. Scratchpad 📝`) from `QPlainTextEdit` to `ScratchpadEditor(QTextEdit)` with rich-text formatting and clean plain-text external clipboard paste (`insertFromMimeData`).
  - Added **`𝐁 Bold`** button (`Ctrl+B` shortcut) to toggle bold weight on highlighted text (or current typing cursor).
  - Added **`🎨 Color`** button opening a dark-themed `QMenu` with 8 color swatches (`SCRATCHPAD_TEXT_COLORS` in `src/config.py`) plus **`🎨 Custom Color...`** (`QColorDialog`) to recolor highlighted text.
  - Extended `ScratchpadState` (`src/config.py`) with an `html: str = ""` field so bold and custom text colors persist across restarts in `data/scratchpad.json` while remaining backward-compatible with plain-text `content`.
- **Detectable & Clickable Web Links in Scratchpad (`src/gui.py`)**:
  - Added `ScratchpadUrlHighlighter(QSyntaxHighlighter)` to automatically detect and underline web links (`https://`, `http://`, `www.`, and bare domains) in real time using `COLORS["accent_link"]` (`#38bdf8`) while preserving user-applied bold and custom foreground colors.
  - Added pixel-accurate hover/click detection (`ScratchpadEditor._url_at_pos()`) that changes the cursor to a pointing hand (`👆`) with a target tooltip on hover and opens the link in the default browser via `open_attachment_link()` on a single left-click (without interfering with click-and-drag text selection).

---

## [v3.3] — TimeSpace Rebrand, Actionable Links/Notes, Monthly Recurrence & Overlay Opacity (2026-10-31)
- **Rebranded Application & Repository to `TimeSpace`**:
  - Updated `APP_TITLE` and `APP_REGISTRY_NAME` to `"TimeSpace"` (`src/config.py`), added `TimeSpaceWidget` alias (`src/gui.py`, `src/__init__.py`), and published to the standalone GitHub repository `JDecelles1990/TimeSpace` while preserving the legacy Tkinter repository separately.
- **Actionable Links & Short Notes (`Timers`, `RDV`, `AlarmDialog`, `Activity`, `History`, `.ics`)**:
  - Added compact side-by-side `Link / URL / Path` and `Short Note` inputs to both Tab 1 (`1. Timers ⏳`) and Tab 2 (`2. RDV 📅`), pairing `Alert` and `Repeat` horizontally in Tab 2 so the bottom `Active Reminders Queue` retains full multi-row height.
  - Added `normalize_link_target()` and `open_attachment_link()` in `src/notifications.py` supporting web URLs, bare domains (`teams.microsoft.com/...`), custom protocol URIs, and local Windows files/folders.
  - Upgraded bottom-right `AlarmDialog` (`src/alarm_dialog.py`) with dynamic height stacking (`132px` standard / `162px` rich), inline note preview, and a 1-click **`🔗 Open Link`** button that opens the target, stops alarm audio, logs `"Opened Link"`, and dismisses the card (while preserving `url`/`note` across snoozes).
  - Surfaced `🔗` / `📝` indicators and tooltips in `Active Reminders Queue`, contextual **`🔗 Open Link`** buttons in `3. Activity 📋` and `5. History 📜`, and RFC 5545 `URL` / `DESCRIPTION` round-tripping (including line unfolding, `newline=""` CRLF output, and embedded meeting URL extraction) in `src/calendar_export.py`.
- **Anchored Monthly Recurrence & Missed-Repeat Catch-Up (`src/scheduler.py`)**:
  - Replaced fixed `+ 30 days` drift in `ReminderScheduler._advance_repeat()` with `calendar.monthrange` day-of-month anchoring (`ScheduledItem.anchor_day`: `Jan 31 -> Feb 28/29 -> Mar 31`) and DST-safe wall-clock stepping across `lead_time_min` offsets.
  - Updated startup recovery in `ReminderScheduler.__init__()` so repeating reminders missed while the app was closed still alert once via `missed_items` while automatically advancing to their next future occurrence.
- **Popup & Mini HUD Opacity Slider (`src/config.py`, `src/mini_hud.py`, `src/alarm_dialog.py`, `src/gui.py`)**:
  - Added `AppConfig.overlay_opacity` (`60%–100%`, default `90%`) and a live-preview `Popup & HUD Opacity` slider in `6. Settings ⚙️` controlling `FloatingMiniHUD` and `AlarmDialog` transparency while keeping `MainApp` `100%` opaque.

---

## [v3.2] — Canonical Documentation Redesign & DRY Architecture (2026-10-31)
- **Redesigned `AGENTS.md`**: Rebuilt the root `AGENTS.md` into a strict AI Coding Agent governance specification with mandatory pre-implementation reading order, PySide6/F7Hub boundary rules, thread-safety constraints, verification commands, and a single-owner documentation routing table.
- **Added `Docs/STATE_AND_CONFIG.md` & `Docs/CHANGELOG.md`**: Extracted all `@dataclass` field contracts, `UI_DIMENSIONS`, `COLORS`, `DARK_QSS` selectors, and `data/*.json` schemas into `STATE_AND_CONFIG.md`, and consolidated project history into `CHANGELOG.md` to eliminate cross-document repetition.
- **Synchronized `Docs/` & `README.md`**: Updated `ARCHITECTURE.md`, `COMPONENT_MAP.md`, `USER_GUIDE.md`, and `README.md` to reflect the 6-tab PySide6 UI, Win32 `RegisterHotKey` subsystem, and `.venv` auto-relaunch, removing legacy Tkinter and Pomodoro references.
- **Package Facade (`src/__init__.py`)**: Added `GlobalHotkeyListener` to `__all__` exports.

---

## [v3.1] — 6-Tab Layout, Intuitive Daily Timer & Startup/Hotkey Fixes (2026-10-31)
- **Simplified Tab 1 (`1. Timers ⏳`)**:
  - Removed IT Support SLA preset button clutter (`15m SLA`, `30m SLA`, `45m Callback`, `2h Follow-up`, `4h Maint`) from Tab 1 and removed the duplicate `+Instant` preset strip from the Hero Deck.
  - Designed a clean **Daily Task & Reminder Timer** with 4 everyday presets (`15 Minutes`, `30 Minutes`, `1 Hour`, `2 Hours`), a `What to do` description field, and an optional `Client / Ticket #` reference field that automatically prefixes timer titles as `[Client/Ticket] Description`.
- **Expanded Multi-Row List Visibility**:
  - Increased default window dimensions to `650x800` (min `600x720`) and tightened `QListWidget` item density (`11px` font, `2px 6px` padding) in `DARK_QSS`.
  - Increased the bottom **Active Reminders Queue** minimum height (`155px`) and layout stretch (`stretch=3`) so 7–9+ reminders remain visible simultaneously across all tabs.
- **Extracted Dedicated Tab 5 (`5. History 📜`) & Full-Height Activity Tab**:
  - Moved Completed/Triggered History out of Tab 3 into its own 6th module tab (`5. History 📜`, positioned between `4. Scratchpad` and `6. Settings`) and added **`📋 Copy Selected`**.
  - Expanded `⏳ All Timers` and `📅 All Rendez-vous` in Tab 3 (`3. Activity 📋`) to fill the full vertical tab height (~15+ visible rows per column).
- **Fixed `run.py` Interpreter Launch & Global `Ctrl+F7` Hotkey**:
  - Installed `PySide6` in `.venv` and added `_ensure_pyside6_interpreter()` in `run.py` to auto-relaunch via `.venv\Scripts\python.exe` whenever invoked from a global Python interpreter lacking `PySide6`.
  - Created `src/hotkey_manager.py` (`GlobalHotkeyListener`) using native Win32 `user32.RegisterHotKey` / `WM_HOTKEY` so `Ctrl+F7` toggles window visibility reliably across Windows without requiring Administrator privileges.

---

## [v3.0] — Tkinter to PySide6 UI Migration for F7Hub (2026-10-31)
- **Complete Framework Migration**: Replaced all `tkinter` / `ttk` views with **PySide6** widgets styled via centralized `DARK_QSS`.
- **F7Hub Modular Split (`src/gui.py`)**:
  - Created self-contained `TimerRendezVousWidget(QWidget)` for direct embedding into the F7Hub modular monolith shell.
  - Created `MainApp(QMainWindow)` as the standalone desktop wrapper managing `TrayManager` and global hotkeys.
- **Thread-Safe Qt Signal Bridge**: Added `SchedulerBridge(QObject)` and `QTimer` loops (`1000ms` live refresh + `500ms` single-shot scratchpad debounce), eliminating Tkinter `root.after()` calls.
- **Custom PySide6 Components**: Rebuilt `CircularProgressRing` (anti-aliased `QPainter`), `MiniCalendar` (`dateSelected` signal), `BigButtonsTimePicker` (`timeChanged` signal), `AlarmDialog` (`QDialog` using `availableGeometry()`), and `FloatingMiniHUD` (`QWidget`).

---

## [v2.5] — Unified Dataclass State Refactor, Scratchpad & Bottom-Right Toasts (2026-10-31)
- **Sweeping Cross-File State & Config Unification**:
  - Centralized all colors, pixel geometry (`UI_DIMENSIONS`), presets, and typed `@dataclass` state models (`AppConfig`, `HistoryEntry`, `ScratchpadState`, `ScheduledItem`) in `src/config.py` and `src/scheduler.py`.
  - Updated `Storage`, `SoundPlayer`, and `AlarmDialog` signatures to consume typed dataclasses directly.
- **Added Time Notes Scratchpad (`Scratchpad 📝`)**: Persistent monospace scratchpad (`data/scratchpad.json`) with `Ctrl+T` timestamp insertion, 500ms debounced auto-save, `Copy All`, and `Clear`.
- **Compact Bottom-Right `AlarmDialog`**: Replaced modal center-screen alarm windows and intrusive confirmation messageboxes with non-intrusive `350x132` frameless bottom-right notification cards that stack vertically and do not force-open the main window.
- **Side-by-Side Hero Deck**: Combined the compact `CircularProgressRing` and Quick Natural Language Scheduler side-by-side at the top of the UI.

---

## [v1.0 – v2.4] — Foundational Capabilities & Deprecated Features
- **Core Capabilities**: Multi-threaded `ReminderScheduler` with pause/resume, sleep/hibernation clock-drift detection (`gap > 6.0s`), cold-start missed-alarm catch-up, `NaturalParser` English grammar, RFC 5545 `.ics` import/export, Windows MCI hardware volume (`0–1000`) & 15s fade-in escalation, Action Center native toasts, `winreg` boot startup, and `FloatingMiniHUD`.
- **Intentionally Removed Features**:
  - **Pomodoro Focus Mode & Tray Pomodoro Shortcuts**: Removed permanently by user request; do not re-implement.
