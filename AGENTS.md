# AGENTS.md — Canonical AI Coding Agent Specification

> **MANDATORY PRE- & POST-IMPLEMENTATION DIRECTIVES**
> 1. **Before coding**: Every AI coding agent MUST read this file in full before planning, modifying, or adding any code in this repository. This file is the authoritative governance contract and routing index for **Timer & Rendez-vous**.
> 2. **After every implementation**: Every AI coding agent MUST document all code, schema, UI, or architectural changes in the corresponding `Docs/*.md` owner files and append an entry to [Docs/CHANGELOG.md](Docs/CHANGELOG.md) before concluding any task. A task is **not complete** until `Docs/*.md` are updated and verified.

---

## 1. System Identity & Dual-Mode Scope

**Timer & Rendez-vous** is a dark-mode Windows 10/11 desktop module built with **Python 3.10+** and **PySide6**. It operates in two interchangeable modes:
1. **Embedded F7Hub Module**: `TimerRendezVousWidget(QWidget)` plugs directly into the parent **F7Hub** modular monolith shell without creating competing windows, tray icons, or event loops.
2. **Standalone Desktop Application**: `run.py` launches `MainApp(QMainWindow)`, wrapping `TimerRendezVousWidget` with Windows System Tray residency (`pystray`), native Win32 global hotkey toggling (`Ctrl+F7`), and auto-relaunch into `.venv`.

*(For integration code and execution flow, see [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md#1-dual-mode-execution--f7hub-embedding).)*

---

## 2. Canonical Documentation Map (DRY Single-Owner Policy)

To prevent drift and contradiction, **every topic has exactly one canonical owner document**. Agents MUST NOT duplicate schemas, tables, or instructions across files—always cross-reference the owning document below:

| Document | Exclusive Ownership Scope | When Agents Must Read / Update |
|---|---|---|
| **[AGENTS.md](AGENTS.md)** *(this file)* | Agent workflow, hard architectural constraints, verification commands, and documentation routing. | Read **before every task**. Update only when global engineering rules or doc topology change. |
| **[Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md)** | Dual-mode F7Hub/Standalone runtime, concurrency & `SchedulerBridge` Qt signal model, `QTimer` loops, and native Win32 subsystems (MCI audio, `RegisterHotKey`, sleep drift, bottom-right popups, Action Center toasts, `winreg`). | Read before touching threading, signals, audio, hotkeys, tray, or window lifecycle. |
| **[Docs/STATE_AND_CONFIG.md](Docs/STATE_AND_CONFIG.md)** | All `@dataclass` schemas (`AppConfig`, `ScheduledItem`, `HistoryEntry`, `ScratchpadState`), `src/config.py` constants (`COLORS`, `UI_DIMENSIONS`, presets), `DARK_QSS` selectors, and `data/*.json` persistence contracts. | Read/update whenever adding settings, UI tokens, QSS rules, presets, or persisted fields. |
| **[Docs/COMPONENT_MAP.md](Docs/COMPONENT_MAP.md)** | Repository file tree, per-module public classes/methods/Qt `Signal` signatures, dependency boundaries, and the 6-tab UI widget hierarchy. | Read to locate symbols/imports; update whenever files, classes, tabs, or public signatures change. |
| **[Docs/USER_GUIDE.md](Docs/USER_GUIDE.md)** | End-user operational manual: Hero Deck, Natural Language syntax, 6-tab workflows (`Timers`, `RDV`, `Activity`, `Scratchpad`, `History`, `Settings`), shortcuts, HUD, and notifications. | Update whenever user-facing controls, labels, tabs, or keyboard shortcuts change. |
| **[Docs/CHANGELOG.md](Docs/CHANGELOG.md)** | Chronological record of all architectural refactors, UI migrations, bug fixes, and intentionally removed features (e.g., Tkinter, Pomodoro, SLA preset bar). | Append an entry after completing any meaningful feature, refactor, or fix. |
| **[README.md](README.md)** | Concise repository landing page, environment setup, launch commands, and links into `Docs/`. | Update only if setup steps, Python/OS requirements, or top-level navigation links change. |

---

## 3. Non-Negotiable Engineering Rules

### Rule 1 — PySide6 UI Only (Zero Tkinter)
- The UI stack is strictly **PySide6** (`QtWidgets`, `QtCore`, `QtGui`). Do **not** import `tkinter` anywhere in the codebase.
- Keep `TimerRendezVousWidget(QWidget)` completely self-contained so it embeds cleanly inside any parent `QMainWindow` or `QStackedWidget` in F7Hub. Host-level concerns (System Tray, OS global hotkey, `closeEvent` hide-to-tray) belong exclusively in `MainApp` (`src/gui.py`).

### Rule 2 — Strict Separation of Concerns
- UI widgets (`src/gui.py`, `src/circular_ring.py`, `src/calendar_widget.py`, `src/time_picker.py`, `src/alarm_dialog.py`, `src/mini_hud.py`) must contain **zero** raw persistence I/O, audio MCI calls, or scheduling math.
- Delegate all business operations to backend services: `ReminderScheduler`, `Storage`, `SoundPlayer`, `NaturalParser`, `CalendarManager`, and `startup`.

### Rule 3 — Thread Safety & Qt Signal Marshaling
- Background daemon threads (`ReminderScheduler._worker`, `TrayManager`, `GlobalHotkeyListener`, `SoundPlayer`, `notifications`) **MUST NEVER** read or mutate `QWidget` instances directly.
- All cross-thread UI triggers must emit through `SchedulerBridge(QObject)` signals onto the main Qt event loop, and periodic/debounced UI tasks must use `QTimer` (see [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md#2-concurrency--pyside6-signal-slot-model)).

### Rule 4 — Unified Typed State & Theme Tokens
- Never pass ad-hoc settings dictionaries or hardcode hex colors, window sizes, or preset lists inside widget code.
- Always use the typed dataclasses (`AppConfig`, `ScheduledItem`, `HistoryEntry`, `ScratchpadState`) and constants (`COLORS`, `UI_DIMENSIONS`, `DARK_QSS`, `CATEGORIES`, `QUICK_TIMER_PRESETS`, `SNOOZE_OPTIONS`, `SOUND_PRESETS`) defined in `src/config.py` and `src/scheduler.py` (see [Docs/STATE_AND_CONFIG.md](Docs/STATE_AND_CONFIG.md)).

### Rule 5 — Respect Removed & Refined UX Decisions
- **Do NOT re-introduce Pomodoro mode** or tray Pomodoro shortcuts (explicitly removed by user preference).
- **Do NOT re-introduce IT SLA preset button clutter** in Tab 1 (`1. Timers ⏳`) or duplicate instant-preset strips in the Hero Deck. Keep Tab 1 focused on everyday professional task reminders (`What to do` + optional `Client / Ticket #` reference + optional `Link / Note` + 4 clean presets).
- **Do NOT force-open the main window** when an alarm triggers; alarms must surface via the compact bottom-right `AlarmDialog` card and Windows Action Center toast.

### Rule 6 — Mandatory Post-Implementation Documentation in `Docs/*.md`
- **Every implementation MUST be documented in `Docs/` before concluding the turn.** Never leave code changes undocumented.
- Follow the **DRY Single-Owner Policy** in Section 2:
  - Update [Docs/STATE_AND_CONFIG.md](Docs/STATE_AND_CONFIG.md) whenever dataclasses, `UI_DIMENSIONS`, `COLORS`, `DARK_QSS`, presets, or `data/*.json` schemas change.
  - Update [Docs/COMPONENT_MAP.md](Docs/COMPONENT_MAP.md) whenever files, classes, public method/signal signatures, or the 6-tab widget tree change.
  - Update [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md) whenever threading, Qt signals, recurrence algorithms, popup stacking, or Win32 OS integrations change.
  - Update [Docs/USER_GUIDE.md](Docs/USER_GUIDE.md) whenever user-visible controls, inputs, tabs, popups, settings, or shortcuts change.
  - **Always** append a dated version entry summarizing the implementation to [Docs/CHANGELOG.md](Docs/CHANGELOG.md).

---

## 4. Mandatory Agent Workflow & Verification Checklist

Before starting implementation:
1. Read `AGENTS.md` -> check the relevant owner docs in `Docs/` (`COMPONENT_MAP.md`, `STATE_AND_CONFIG.md`, `ARCHITECTURE.md`).
2. Inspect target files in `src/` before editing.

Before concluding **every** implementation task, execute **all three** mandatory completion steps:

1. **Bytecode & Syntax Compilation Check**:
   ```powershell
   & ".venv\Scripts\python.exe" -m py_compile run.py src/__init__.py src/config.py src/storage.py src/scheduler.py src/sound.py src/hotkey_manager.py src/tray.py src/notifications.py src/startup.py src/natural_parser.py src/calendar_export.py src/circular_ring.py src/calendar_widget.py src/time_picker.py src/alarm_dialog.py src/mini_hud.py src/gui.py
   ```
2. **Headless Lifecycle Smoke Test** (verifies `QMainWindow`, `TimerRendezVousWidget`, `SchedulerBridge`, `GlobalHotkeyListener`, and clean shutdown):
   ```powershell
   & ".venv\Scripts\python.exe" -c "from PySide6.QtCore import QTimer; from src.gui import MainApp; app = MainApp(start_minimized=True); QTimer.singleShot(500, app.quit_app); app._qt_app.exec()"
   ```
3. **Mandatory `Docs/*.md` Documentation Sync**: Update every affected owner document in `Docs/` (`ARCHITECTURE.md`, `STATE_AND_CONFIG.md`, `COMPONENT_MAP.md`, `USER_GUIDE.md`) and append an entry to [Docs/CHANGELOG.md](Docs/CHANGELOG.md) without duplicating details across multiple files.
