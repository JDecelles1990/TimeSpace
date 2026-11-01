# Engineering & Migration Changelog (`Docs/CHANGELOG.md`)

> **Canonical Scope**: Chronological record of all architectural refactors, UI migrations, layout adjustments, bug fixes, and intentionally removed features across **Timer & Rendez-vous**.
> *(For current system design, see [ARCHITECTURE.md](ARCHITECTURE.md). For state schemas, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## [v3.3] — Actionable Links/Notes, Exact Monthly Recurrence & Overlay Opacity (2026-10-31)
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

