# Timer & Rendez-vous ⏰

A sleek, dark-mode **PySide6** desktop application and pluggable **F7Hub** module for daily task timers, calendar appointments (Rendez-vous), and time-stamped scratchpad notes on Windows 10/11.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-informational?style=flat-square)
![UI](https://img.shields.io/badge/UI-PySide6%20Dark%20QSS-6366f1?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Highlights

- **Dual-Mode Architecture**: Runs standalone (`MainApp`) with System Tray & Win32 `Ctrl+F7` global hotkey, or embeds directly into the **F7Hub** modular monolith via `TimerRendezVousWidget(QWidget)`.
- **Hero Deck**: Anti-aliased `QPainter` Radial Countdown Ring (`124px`) paired with a plain-English Natural Language Scheduler (`"Ring in 15m"`, `"Call Sam in 2 days at 3pm"`, `"RDV tomorrow at 14:00"`).
- **6 Focused Modules + Persistent Multi-Row Queue**:
  1. **`1. Timers ⏳`** — Everyday presets (`15m`, `30m`, `1h`, `2h`) and custom task reminders with optional `Client / Ticket #` tagging and `Link / Note` attachments.
  2. **`2. RDV 📅`** — Interactive dark calendar grid, ergonomic time picker, optional `Link / Note` attachments, lead-time alerts, anchored calendar recurrence (`Daily`, `Weekly`, `Monthly`), and `.ics` import/export.
  3. **`3. Activity 📋`** — Full-height side-by-side live view of all active timers and scheduled appointments with 1-click **`🔗 Open Link`**.
  4. **`4. Scratchpad 📝`** — Auto-saved time notes with `Ctrl+T` timestamp insertion and 1-click clipboard copy.
  5. **`5. History 📜`** — Dedicated audit log of triggered, dismissed, link-opened, and snoozed reminders with **`🔗 Open Link`** and **`📋 Copy Selected`**.
  6. **`6. Settings ⚙️`** — Built-in chime synthesizers, custom `.mp3`/`.wav` playback via Windows MCI hardware volume (`0–100%`), live-preview **Popup & HUD Opacity (`60–100%`, default `90%`)**, gradual escalation, and Windows boot auto-start.
- **Actionable Non-Intrusive Alerts**: Compact frameless bottom-right notification cards (with dynamic vertical stacking, note preview, 1-click **`🔗 Open Link`**, and snooze), Windows Action Center toasts, sleep-drift wake detection, and a draggable always-on-top **Floating Mini HUD**.

---

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. Launch
```powershell
python run.py
```
*(Note: `run.py` automatically delegates to `.venv\Scripts\python.exe` if invoked from a global Python environment missing `PySide6`. Pass `--minimized` to start hidden in the System Tray.)*

---

## 📚 Canonical Documentation

To avoid duplication, documentation is organized by strict single-owner scope:

- **[AGENTS.md](AGENTS.md)** — **Start here for AI Coding Agents**: mandatory pre-implementation rules, thread-safety constraints, verification commands, and doc routing.
- **[Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md)** — Dual-mode F7Hub/Standalone runtime, `SchedulerBridge` Qt signal concurrency, and Win32 subsystems (MCI audio, `RegisterHotKey`, sleep drift, bottom-right popups).
- **[Docs/STATE_AND_CONFIG.md](Docs/STATE_AND_CONFIG.md)** — Typed `@dataclass` schemas (`AppConfig`, `ScheduledItem`, `HistoryEntry`, `ScratchpadState`), `UI_DIMENSIONS`, `COLORS`, `DARK_QSS`, and `data/*.json` contracts.
- **[Docs/COMPONENT_MAP.md](Docs/COMPONENT_MAP.md)** — Repository tree, module signatures/signals, and the PySide6 widget hierarchy.
- **[Docs/USER_GUIDE.md](Docs/USER_GUIDE.md)** — Complete user manual, 6-tab walkthrough, Natural Language cheatsheet, and keyboard shortcuts.
- **[Docs/CHANGELOG.md](Docs/CHANGELOG.md)** — Chronological record of refactors, Tkinter-to-PySide6 migration, UI enhancements, and deprecated features.

---

## 📄 License
Released under the [MIT License](LICENSE).
